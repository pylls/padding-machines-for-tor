#!/usr/bin/env python3
"""Collect Network Traces from Tor Browser

We assume that this script will execute from multiple containers that share the
exact same script arguments. Hence, the shared results folder (specified as an
argument) is used to coordinate the multiple instances. The results folder will
contain in total sites * instances number of pcaps.
"""
import argparse
import csv
import os
import sys
import time
import random
import shutil
import string
import subprocess
import tempfile
import threading
import datetime

ap = argparse.ArgumentParser()
ap.add_argument("-l", required=True,
    help="file with list of sites to visit, one site per line")
ap.add_argument("-n", required=True, type=int,
    help="number of samples")

# all data is stored in the below dir and checks are made against the folder if
# data has already been collected before collecting again, multiple instances of
# this script are assumed to possibly be using the same shared directory
ap.add_argument("-d", required=True,
    help="(shared) data folder for storing results")
ap.add_argument("-b", required=True, 
    help="folder with Tor Browser")

ap.add_argument("-a", required=False, default=5, type=int,
    help="number of attempts to collect each trace")
ap.add_argument("-t", required=False, default=60, type=int,
    help="timeout (s) for each TB visit")
ap.add_argument("-m", required=False, default=100, type=int,
    help="minimum number of liens in torlog to accept")
args = vars(ap.parse_args())

RESULTSFMT = "{}-{}.log"
TBFILE = "start-tor-browser.desktop"
CIRCPAD_EVENT = "circpad_trace_event"

tmpdir  = tmpdir = tempfile.mkdtemp()

def now():
    return datetime.datetime.now()

def main():
    if not os.path.exists(args["d"]):
        sys.exit(f"data directory {args['d']} does not exist")
    if not os.path.exists(args["b"]):
        sys.exit(f"Tor Browser directory {args['b']} does not exist")
    if not os.path.isfile(os.path.join(args["b"], TBFILE)):
        sys.exit(f"Tor Browser directory {args['b']} missing {TBFILE}")

    print("reading sites list {}".format(args["l"]))
    sites = get_sites_list()
    print("ok, list has {} sites".format(len(sites)))

    tb = make_tb_copy(args["b"])
    print("two warmup visits for fresh consensus and whatnot update checks")
    print(f"\t got {len(visit('kau.se/en', tb, args['t']))} log-lines")
    print(f"\t got {len(visit('kau.se/en/cs', tb, args['t']))} log-lines")

    # random order of samples and sites, making it unlikely that several
    # instances of this script are be working on the same sites-sample pair
    samples = [i for i in range(args["n"])]
    random.shuffle(samples)
    for n in samples:
        random.shuffle(sites)
        for index, site in sites:
            # only attempt to collect if not already collected
            if not os.path.isfile(results_file(index, n)):
                collect(index, site, n, tb)

    # cleanup
    shutil.rmtree(tmpdir)
    print("all done, exiting")

def collect(index, site, sample, tb_orig):
    print(f"attempting to collect site {site}, saving to {index}-{sample}")
    for _ in range(args["a"]):
        # create fresh TB copy for this visit
        tb = make_tb_copy(tb_orig)

        # visit with TB, blocking, and get stdout (the log)
        log = visit(site, tb, args["t"])
        print(f"\t {now()} got {len(log)} circpad events in log")

        # cleanup our TB copy
        shutil.rmtree(tb)

        # seems someone already saved the file while we visited, exit
        if os.path.isfile(results_file(index, sample)):
            break

        # save and break if long enough
        if len(log) >= args["m"]:
            with open(results_file(index, sample), 'w') as f:
                for l in log:
                    f.write(f"{l}\n")
            break

def make_tb_copy(src):
    dst = os.path.join(tmpdir, 
    ''.join(random.choices(string.ascii_uppercase + string.digits, k=24)))

    # ibus breaks on multiple copies that move location, need to ignore
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('ibus'))
    return dst

def visit(url, tb, timeout):
    tb = os.path.join(tb, "Browser", "start-tor-browser")
    cmd = f"timeout -k 5 {str(timeout)} {tb} --verbose --headless {url}"
    print(f"\t {now()} {cmd}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True
    )
    
    return filter_circpad_lines(result.stdout)

def filter_circpad_lines(stdout):
    out = []
    lines = stdout.split("\n")
    for l in lines:
        if CIRCPAD_EVENT in l:
            out.append(l)
    
    return out

def results_file(index, sample):
    return os.path.join(args["d"], RESULTSFMT.format(index, sample))

def get_sites_list():
    # list of tuple (index,site)
    l = []
    with open(args["l"]) as f:
        for line in f:
            # index each site by its line in the file
            l.append((len(l), line.rstrip())) 
    return l

if __name__ == "__main__":
    main()
