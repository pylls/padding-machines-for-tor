#!/usr/bin/env python3
import argparse
import sys
import os
import shutil
import subprocess
import tempfile
import signal
import numpy as np
import pickle
from multiprocessing import Pool
import logging
import torch
from torch.utils import data
import torch.nn.functional as F

import circpadsim
import machine
import evolve
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

ap.add_argument("-t", required=True, 
    help="path to tor folder (bob/tor, not bob/tor/src)")

ap.add_argument("-w", required=False, type=int, default=10,
    help="number of workers for simulating machines")

# fitness options
ap.add_argument("--df", required=False, default=False,
    action="store_true", help="determine fitness using DF")
ap.add_argument("--collision", required=False, default=False,
    action="store_true", help="determine fitness using collision matrix")

# for generated machines
ap.add_argument("--save", required=False, default="",
    help="file for saving latest machines")
ap.add_argument("--load", required=False, default="",
    help="file to load latest machines from for initial population")

# exp
ap.add_argument("-n", required=False, type=int, default=10,
    help="number of machines per generation")
ap.add_argument("-l", required=False, type=int, default=5000,
    help="max length of extracted cells")

# df fitness
ap.add_argument("--epochs", required=False, type=int, default=20,
    help="the number of epochs for training")
ap.add_argument("--batchsize", required=False, type=int, default=250,
    help="batch size")

# tweaker helper
ap.add_argument("--print", required=False, default=False,
    action="store_true", help="print the code of the best machines and quit")
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
    ''' loop
    '''

    if not args["df"] and not args["collision"]:
        sys.exit("need at least one of --df and --collision for fitness")

    # properly restore tor source when closed
    signal.signal(signal.SIGINT, sigint_handler)

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

    # construct our fitness function with a global cache
    fitness_cache = {}
    def fitness(mp):
        f = -1.1234
        pid = to_pid(mp)

        if pid in fitness_cache:
            logging.info(f"\tcache hit for machines {pid}")
            f = fitness_cache[pid]
        else:
            logging.info(f"\tadding machines {pid}")
            add_machines(mp)

            logging.info("\tsimulating machines")
            client_traces, _ = simulate_machines(labels, fnames_client, fnames_relay,
                        extract_cells if args["df"] else extract_cell_events)
            
            logging.info("\tdetermining fitness")
            
            if args["df"]:
                f = fitness_df(client_traces, labels)
            elif args["collision"]:
                f = fitness_collision(client_traces)

            if f == -1.1234:
                sys.exit("no fitness computed")

            fitness_cache[pid] = f

        logging.info(f"\t\tfitness is {f:.2}")
        return f

    # parameters for our experiment in a dict, easier to save
    exp = {}
    exp["num_states"] = 4
    exp["iat_d_low"] = 0
    exp["iat_d_high"] = 10
    exp["iat_a_low"] = 0
    exp["iat_a_high"] = 10
    exp["iat_m_low"] = 100
    exp["iat_m_high"] = 100*1000
    exp["length_d_low"] = 0
    exp["length_d_high"] = 10
    exp["length_a_low"] = 0
    exp["length_a_high"] = 10
    exp["length_m_low"] = 10
    exp["length_m_high"] = 1*1000
    exp["target_hopnum"] = 2 # NOTE: circpadsim only works for middle relay ...
    exp["name"] = "evolved"
    exp["allowed_padding_count_client"] = 1000
    exp["max_padding_percent_client"] = 50
    exp["allowed_padding_count_relay"] = 1000
    exp["max_padding_percent_relay"] = 50
    
    exp["population_size"] = args["n"]
    exp["mutation_prob"] = 0.5
    exp["crossover_prob"] = 0.5
    exp["elitist_frac"] = 0.1
    exp["diversity_frac"] = 0.0

    # template client and relay machines with our parameters
    machine_client = machine.Machine(
        is_origin_side=True, name=exp["name"], target_hopnum=exp["target_hopnum"],
        allowed_padding_count=exp["allowed_padding_count_client"], 
        max_padding_percent=exp["max_padding_percent_client"],
        )
    machine_relay = machine_client.clone()
    machine_relay.is_origin_side = False
    machine_relay.name = machine_relay.name + "_relay"
    machine_relay.allowed_padding_count = exp["allowed_padding_count_relay"]
    machine_relay.max_padding_percent = exp["max_padding_percent_relay"]

    # generate initial population
    ml = evolve.initial_population(machine_client, machine_relay, exp)
    if args["load"] != "":
        logging.info(f"loading initial population of machines from {args['load']}")
        loaded = pickle.load(open(args["load"], "rb"))[1]
        # copy in, three cases
        if len(loaded) == len(ml):
            ml = loaded
        elif len(loaded) > len(ml):
            ml = loaded[:len(ml)]
        else:
            loaded.extend(ml[:len(ml)-len(loaded)])
            ml = loaded
        
    logging.info(f"initial population has {len(ml)} pairs of machines")

    if args["print"]:
        print(f"\n\nprinting machines then quitting\n")
        print(ml[0][0].to_c("client"))
        print(f"\n\n")
        print(ml[0][1].to_c("relay"))
        print(f"\n")
        sys.exit("quitting, told to only print")

    n = 1
    while True:
        # selection
        logging.info(f"selection, round {n}")
        ml, fl = evolve.selection(ml, fitness)

        logging.info(f"best pair of machines {to_pid(ml[0])} has fitness {fl[0]:.2}, did {n} rounds")
        logging.info(f"{ml[0][0]}")
        logging.info(f"{ml[0][1]}")
        if args["save"] != "":
            pickle.dump([exp, ml], open(args["save"], "wb"))
            logging.info(f"saved generation to file {args['save']}")
        
        # next generation
        logging.info("next generation")
        ml = evolve.next_generation(ml, fl, exp)
        n += 1

def to_pid(mp):
    return f"[{mp[0].id()}, {mp[1].id()}]"

def fitness_df(traces, labels):
    split = shared.split_dataset(args["c"], args["p"], args["s"], 0, labels)
    
    model = shared.DFNet(args["c"]+1) # one class for unmonitored
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        logging.info(f"\t\tusing {torch.cuda.get_device_name(0)}")
        model.cuda()
    
    # Note below that shuffle=True is *essential*, 
    # see https://stackoverflow.com/questions/54354465/
    train_gen = data.DataLoader(
        shared.Dataset(split["train"], traces, labels),
        batch_size=args["batchsize"], shuffle=True,
    )
    validation_gen = data.DataLoader(
        shared.Dataset(split["validation"], traces, labels),
        batch_size=args["batchsize"], shuffle=True,
    )
    optimizer = torch.optim.Adamax(params=model.parameters())
    criterion = torch.nn.CrossEntropyLoss()
    for epoch in range(args["epochs"]):
        # training
        model.train()
        torch.set_grad_enabled(True)
        running_loss = 0.0
        n = 0
        for x, Y in train_gen:
            x, Y = x.to(device), Y.to(device)
            optimizer.zero_grad()
            outputs = model(x)
            loss = criterion(outputs, Y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            n+=1
        training_loss = running_loss/n

        # validation
        model.eval()
        torch.set_grad_enabled(False)
        running_corrects = 0
        n = 0
        for x, Y in validation_gen:
            x, Y = x.to(device), Y.to(device)

            outputs = model(x)
            _, preds = torch.max(outputs, 1)
            running_corrects += torch.sum(preds == Y)
            n += len(Y)
        if epoch+1 == args["epochs"]:
            logging.info(f"\t\t{epoch+1} epochs, last training loss {training_loss:.2} and validation accuracy {float(running_corrects)/float(n):.2}")
    
    # testing
    testing_gen = data.DataLoader(
        shared.Dataset(split["test"], traces, labels), 
        batch_size=args["batchsize"]
    )
    model.eval()
    torch.set_grad_enabled(False)
    predictions = []
    p_labels = []
    for x, Y in testing_gen:
        x = x.to(device)
        outputs = model(x)
        index = F.softmax(outputs, dim=1).data.cpu().numpy()
        predictions.extend(index.tolist())
        p_labels.extend(Y.data.numpy().tolist())
    
    # fitness is 1 - recall, with threshold 0.0. We use recall because it is
    # focused on when the client visits a monitored page, and it tells us how
    # many out of all visits by the client the classifier accurately detects.
    # Techniques like Website Oracles can be used to increase precision.
    # Assuming an attacker that uses such a technique, we should consider the
    # maximum recall of the classifier, i.e., when the threshold is 0.0.
    # However, as a fitness function, this is too unstable for our loop to
    # reliably progress towards increasingly better machines, so we use a larger
    # threshold.
    _, _, _, _, _, _, recall, _, _ = shared.metrics(0.0,
                                            predictions, p_labels, args["c"])
    fitness = 1.0 - recall
    return fitness

def fitness_collision(traces):
    # how many padding cells hit the same location in a trace as a non-padding cell?
    # FIXME: could consider time as well as a distance for cells, but tricky?
    length = args["l"]
    nonpadding_sent = np.zeros((length, 2*length+1), dtype=int)
    nonpadding_recv = np.zeros((length, 2*length+1), dtype=int)
    padding_sent = np.zeros((length, 2*length+1), dtype=int)
    padding_recv = np.zeros((length, 2*length+1), dtype=int)

    for _, t in traces.items():
        y = length # middle
        for x, e in enumerate(t):
            if circpadsim.CIRCPAD_EVENT_NONPADDING_SENT in e:
                y += 1
                nonpadding_sent[x][y] = nonpadding_sent[x][y] + 1
            elif circpadsim.CIRCPAD_EVENT_PADDING_SENT in e:
                y += 1
                padding_sent[x][y] = padding_sent[x][y] + 1
            elif circpadsim.CIRCPAD_EVENT_NONPADDING_RECV in e:
                y += -1
                nonpadding_recv[x][y] = nonpadding_recv[x][y] + 1
            elif circpadsim.CIRCPAD_EVENT_PADDING_RECV in e:
                y += -1
                padding_recv[x][y] = padding_recv[x][y] + 1

    fitness_sent = padding_sent * nonpadding_sent
    fitness_recv = padding_recv * nonpadding_recv
    fitness = fitness_sent.sum() + fitness_recv.sum()
    return fitness

def add_machines(mp):
    # read source
    global original_src, src_path
    if original_src == "":
        with open(src_path, "r") as myfile:
            original_src = myfile.read()
    assert(original_src != "")
    assert(CLIENT_MACHINE_TOKEN in original_src)
    assert(RELAY_MACHINE_TOKEN in original_src)

    # create machine variables
    c_var = "gen_client"
    r_var = "gen_relay"
    client = f"circpad_machine_spec_t *{c_var} = tor_malloc_zero(sizeof(circpad_machine_spec_t));\n"
    relay = f"circpad_machine_spec_t *{r_var} = tor_malloc_zero(sizeof(circpad_machine_spec_t));\n"

    # hardcoded conditions for the client FIXME: check these
    client += f"{c_var}->conditions.state_mask = CIRCPAD_CIRC_STREAMS;\n"
    client += f"{c_var}->conditions.purpose_mask = CIRCPAD_PURPOSE_ALL;\n"
    client += f"{c_var}->conditions.reduced_padding_ok = 1;\n"

    # generate the full machines
    client += mp[0].to_c(c_var)
    relay += mp[1].to_c(r_var)

    # add boilerplate to register machines as in test_circuitpadding_sim.c
    client += f"\n{c_var}->machine_num = smartlist_len(origin_padding_machines);\ncircpad_register_padding_machine({c_var}, origin_padding_machines);"
    relay += f"\n{r_var}->machine_num = smartlist_len(relay_padding_machines);\ncircpad_register_padding_machine({r_var}, relay_padding_machines);"

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
        logging.error(cmd)
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

def extract_cells(log, client=True):
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

        if "padding_sent" in line: # also includes nonpadding_sent
            data[0][i] = 1.0 # outgoing is positive
            i += 1
        elif "padding_received" in line: # also includes nonpadding_received
            data[0][i] = -1.0 # incoming is negative
            i += 1

    return data

def extract_cell_events(trace):
    return circpadsim.circpad_to_wf(trace, cellevents=True)[:args["l"]]

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

    return labels, fnames_client, fnames_relay

def load_dataset_fnames(
    mon_dir, unm_dir, 
    classes, partitions, samples
    ):
    fnames = []

    # load monitored data
    for c in range(0,classes):
        for p in range(0,partitions):
            site = c*10 + p
            for s in range(0,samples):
                ID = f"m-{c}-{p}-{s}"

                # file format is {site}-{sample}.trace
                fname = os.path.join(mon_dir, f"{site}-{s}.trace")
                if not os.path.exists(fname):
                    sys.exit(f"{fname} does not exist")
                fnames.append(fname)

    # load unmonitored data
    dirlist = os.listdir(unm_dir)[:len(fnames)]
    for f in dirlist:
        fnames.append(os.path.join(unm_dir, f))

    return fnames

if __name__ == "__main__":
    main()
