#!/usr/bin/env python3
''' Tweak a pair of machines. 

The goal is to be able to rapidly tweak a single pair of machines as fast as
possible against DF. '''
import argparse
import sys
import os
import subprocess
import tempfile
import signal
import numpy as np
import pickle
from multiprocessing import Pool
import logging
import shared

logging.basicConfig(level = logging.INFO, format = "%(asctime)s %(message)s")

ap = argparse.ArgumentParser()
# dataset and its dimensions, assuming same count unmon as mon
ap.add_argument("--client", required=True, 
    help="input folder of client circpadtrace files")
ap.add_argument("--relay", required=True, 
    help="input folder of relay circpadtrace files")
ap.add_argument("-c", required=False, type=int, default=50,
    help="the number of monitored classes")
ap.add_argument("-p", required=False, type=int, default=10,
    help="the number of partitions")
ap.add_argument("-s", required=False, type=int, default=20,
    help="the number of samples")

# exp
ap.add_argument("-t", required=True, 
    help="path to tor folder (bob/tor, not bob/tor/src)")
ap.add_argument("-w", required=False, type=int, default=10,
    help="number of workers for simulating machines")
ap.add_argument("-l", required=False, type=int, default=5000,
    help="max length of extracted cells")

# machines to tweak
ap.add_argument("--mc", required=True, 
    help="path to file of client machine (c-code) to tweak")
ap.add_argument("--mr", required=True, 
    help="path to file of relay machine (c-code) to tweak")

# pickle dump results
ap.add_argument("--save", required=True, help="file to save results to")
args = vars(ap.parse_args())

TOR_CIRCPADSIM_SRC_LOC = "src/test/test_circuitpadding_sim.c"
CLIENT_MACHINE_TOKEN = "//REPLACE-client-padding-machine-REPLACE"
RELAY_MACHINE_TOKEN = "//REPLACE-relay-padding-machine-REPLACE"
TOR_CIRCPADSIM_CMD = os.path.join(args["t"], "src/test/test circuitpadding_sim/..")
TOR_CIRCPADSIM_CMD_FORMAT = f"{TOR_CIRCPADSIM_CMD} --info --circpadsim {{}} {{}} 1"

tmpdir = tempfile.mkdtemp()
original_src = "" 
src_path = os.path.join(args["t"], TOR_CIRCPADSIM_SRC_LOC)

def main():
    # properly restore tor source when closed
    signal.signal(signal.SIGINT, sigint_handler)

    # list of input traces, sorted assuming the matching client and relay traces
    # have the same name in respective folders
    c_mon_dir = os.path.join(args["client"], "monitored")
    if not os.path.isdir(c_mon_dir):
        sys.exit(f"{c_mon_dir} is not a directory")
    c_unm_dir = os.path.join(args["client"], "unmonitored")
    if not os.path.isdir(c_unm_dir):
        sys.exit(f"{c_unm_dir} is not a directory")
    r_mon_dir = os.path.join(args["relay"], "monitored")
    if not os.path.isdir(r_mon_dir):
        sys.exit(f"{r_mon_dir} is not a directory")
    r_unm_dir = os.path.join(args["relay"], "unmonitored")
    if not os.path.isdir(r_unm_dir):
        sys.exit(f"{r_unm_dir} is not a directory")

    logging.info(f"loading original traces")
    labels, fnames_client, fnames_relay = load_dataset(
        c_mon_dir, c_unm_dir,
        r_mon_dir, r_unm_dir,
        args["c"], args["p"], args["s"]
    )
    logging.info(f"loaded {len(labels)} traces")

    # load machines to tweak
    with open(args["mc"], "r") as f:
        mc = f.read()
    with open(args["mr"], "r") as f:
        mr = f.read()

    logging.info(f"adding machines")
    add_machines(mc, mr)

    logging.info("simulating machines")
    client_traces, _ = simulate_machines(labels, fnames_client, fnames_relay, extract_cells_detailed)

    logging.info(f"pickle dump to {args['save']}")
    pickle.dump((client_traces, labels), open(args["save"], "wb"))

    logging.info(f"done")

def add_machines(client, relay):
    # read source
    global original_src, src_path
    if original_src == "":
        with open(src_path, "r") as myfile:
            original_src = myfile.read()
    assert(original_src != "")
    assert(CLIENT_MACHINE_TOKEN in original_src)
    assert(RELAY_MACHINE_TOKEN in original_src)

    # replace with machines and save the modified source
    modified_src = original_src.replace(CLIENT_MACHINE_TOKEN, client)
    modified_src = modified_src.replace(RELAY_MACHINE_TOKEN, relay)
    with open(src_path, "w") as f:
        f.write(modified_src)

    # make new machines, then restore original source
    make_tor()
    restore_source()

def restore_source():
    global original_src, src_path
    with open(src_path, "w") as f:
        f.write(original_src)

def sigint_handler(foo=1, bar=2):
    restore_source()
    sys.exit(0)

def make_tor():
    cmd = f"cd {args['t']} && make"
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, shell=True)
    if result.returncode != 0:
            logging.info(cmd)
    assert(result.returncode == 0)

def simulate_machines(
    labels, fnames_client, fnames_relay,
    extract_func,
    extract_client=True,
    extract_relay=False,
    ):

    todo = []
    logging.info(f"\t\tlisting {len(labels)} traces to simulate")
    for ID in labels:
        todo.append(
            (fnames_client[ID], fnames_relay[ID], ID,
            extract_func, extract_client, extract_relay)
        )

    logging.info(f"\t\trunning with {args['w']} workers")
    p = Pool(args["w"])
    results = p.starmap(do_simulate_machines, todo)

    logging.info(f"\t\textracting results")
    # ID -> extracted
    out_client = {}
    out_relay = {}
    for result in results:
        if extract_client:
            out_client[result[0]] = result[1]
        if extract_relay:
            out_relay[result[0]] = result[2]

    p.close()

    return out_client, out_relay

def do_simulate_machines(
    client, relay, ID,
    extract_func, extract_client=True, extract_relay=False
    ):
    cmd = TOR_CIRCPADSIM_CMD_FORMAT.format(client, relay)
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        logging.error(f"got returncode {result.returncode} for cmd {cmd}")
    assert(result.returncode == 0)

    # parse out the simulated logs, get client and relay traces
    client_out = []
    relay_out = []
    log = result.stdout.split("\n")
    if extract_client:
        client_out = extract_func(log, client=True)
    if extract_relay:
        relay_out = extract_func(log, client=False)

    return (ID, client_out, relay_out)

def extract_cells_detailed(log, client=True):
    i = 0
    length = args["l"]
    data = np.zeros((1, length), dtype=np.float32)
    for line in log:
        if i >= length:
            break

        if client and not "source=client" in line:
            continue
        elif not client and not "source=relay" in line:
            continue

        if shared.CIRCPAD_EVENT_NONPADDING_SENT in line:
            data[0][i] = 1.0 # outgoing is positive
            i += 1
        elif shared.CIRCPAD_EVENT_PADDING_SENT in line:
            data[0][i] = 2.0
            i += 1
        elif shared.CIRCPAD_EVENT_NONPADDING_RECV in line:
            data[0][i] = -1.0
            i += 1
        elif shared.CIRCPAD_EVENT_PADDING_RECV in line:
            data[0][i] = -2.0
            i += 1

    return data

def load_dataset(
    c_mon_dir, c_unm_dir, 
    r_mon_dir, r_unm_dir, 
    classes, partitions, samples
    ):

    # ID -> class
    labels = {}
    # ID -> fname
    fnames_client = {}
    fnames_relay = {}

    # monitored
    for c in range(0,classes):
        for p in range(0,partitions):
            site = c*10 + p
            for s in range(0,samples):
                ID = f"m-{c}-{p}-{s}"
                fname = f"{site}-{s}.trace"

                labels[ID] = c
                fnames_client[ID] = os.path.join(c_mon_dir, fname)
                fnames_relay[ID] = os.path.join(r_mon_dir, fname)
                if not os.path.exists(fnames_client[ID]):
                    sys.exit(f"{fnames_client[ID]} does not exist")
                if not os.path.exists(fnames_relay[ID]):
                    sys.exit(f"{fnames_relay[ID]} does not exist")

    # unmonitored
    dirlist = os.listdir(c_unm_dir)[:len(labels)]
    for fname in dirlist:
        ID = f"u-{fname}"

        labels[ID] = classes # start from 0 for monitored
        fnames_client[ID] = os.path.join(c_unm_dir, fname)
        fnames_relay[ID] = os.path.join(r_unm_dir, fname)
        if not os.path.exists(fnames_relay[ID]):
            sys.exit(f"{fnames_relay[ID]} does not exist")

    # we need to provide:
    # - for simulate_machines, the full fname with path for each pair
    # - for df, labels as above and a way to get the data from simulate_machines that maps from ID
    # have simulate_machines produce ID -> data for client and relay
    return labels, fnames_client, fnames_relay

if __name__ == "__main__":
    main()
