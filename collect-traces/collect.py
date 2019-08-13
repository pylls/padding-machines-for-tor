#!/usr/bin/env python3
"""Collect Network Traces from Tor Browser

We assume that this script will execute from multiple containers that share the
exact same script arguments. Hence, the shared results folder (specified as an
argument) is used to coordinate the multiple instances. The result folder will
contain pcaps for |sites in list|xsamples site visits using the Tor Browser run
by calling the provided shellscript.
"""
import argparse
import csv
import os
import time
import random
import shutil
import string
import subprocess
import tempfile
import threading

ap = argparse.ArgumentParser()
ap.add_argument("-l", required=True,
    help="Alexa file with list of sites to visit")
ap.add_argument("-n", required=True, type=int,
    help="number of samples")

# all data is stored in the below dir and checks are made against the folder if
# data has already been collected before collecting again, multiple instances of
# this script are assumed to possibly be using the same shared directory
ap.add_argument("-d", required=True,
    help="(shared) data folder for storing results")

# make sure that the IP address of the guard is that which is hardcoded as the
# guard in Browser/TorBrowser/Data/Tor/torrc (using EntryNodes fingerprint) of
# the instance of Tor Browser
ap.add_argument("-g", required=True, 
    help="IP address of guard")
ap.add_argument("-b", required=True, 
    help="folder with Tor Browser")

ap.add_argument("-a", required=False, default=5, type=int,
    help="number of attempts to collect each trace")
ap.add_argument("-t", required=False, default=60, type=int,
    help="timeout (s) for each TB visit")
ap.add_argument("-i", required=False, default="eth0",
    help="network interface to capture from")
ap.add_argument("-v", required=False, default="./visit.sh",
    help="location of the visit.sh script")

# SnapLen of 68 bytes for IPv4 packets and 96 bytes for IPv6 packets
ap.add_argument("-s", required=False, default=68, type=int,
    help="snaplen to capture")

# with default snaplen 68, expect at least 100 packets, and account for pcap
# header of 24 bytes: 68x100+24 = 6824
ap.add_argument("-m", required=False, default=6824, type=int,
    help="minimum pcap size to accept (bytes)")
args = vars(ap.parse_args())

RESULTSFMT = "{}-{}.pcap"
TSHARKFMT = "tshark -i {} -f \"host {} and length > 511\" -s {} -a duration:{} -w {} -F libpcap"
TBFILE = "start-tor-browser.desktop"

tmpdir = tempfile.mkdtemp()

def main():
    if not os.path.exists(args["d"]):
        print("data directory {} does not exist".format(args["d"]))
        return -1
    if not os.path.exists(args["b"]):
        print("Tor Browser directory {} does not exist".format(args["b"]))
        return -1
    if not os.path.isfile(os.path.join(args["b"], TBFILE)):
        print("Tor Browser directory {} missing {}".format(args["b"], TBFILE))
        return -1

    print("reading Alexa site list {}".format(args["l"]))
    alexa = get_alexa_list()
    print("ok, list has {} sites".format(len(alexa)))

    # FIXME: make a copy of TB, warmup visits, make a copy again and go
    tb = make_tb_copy(args["b"])
    visit("kau.se/en", tb, args["t"])
    visit("kau.se/en/cs", tb, args["t"])

    # random order of samples and alexa, ensuring that each instance of this
    # script won't be working on the same alexa-sample pair
    samples = [i for i in range(args["n"])]
    random.shuffle(samples)
    for n in samples:
        random.shuffle(alexa)
        for index, site in alexa:
            # only attempt to collect if not already collected
            if not os.path.isfile(results_file(index, n)):
                collect(index, site, n, tb)

    # remove tmpdir
    shutil.rmtree(tmpdir)

def collect(index, site, sample, tb_orig):
    print("collect index {}, site {}, sample {}".format(index, site, sample))
    fname = results_file(index, sample)

    for a in range(args["a"]):
        # after two attempts, try to toggle www. prefix on url
        if a >= 2:
            site = toggle_www(site)

        # create fresh TB copy
        tb = make_tb_copy(tb_orig)

        # start network capture in new thread
        t = threading.Thread(target=capture, args=(fname,))
        t.start()

        # sleep briefly, giving the thread time to start
        time.sleep(1)

        # visit with TB, blocking
        visit(site, tb, args["t"]-1)

        # cleanup before/while waiting
        cleanup_tb_copy(tb)

        # wait for network capture to finish
        t.join()

        # if capture was successful and at least of minimum size, done
        if os.path.isfile(fname) and os.path.getsize(fname) >= args["m"]:
            break
        
        # otherwise remove the file, too little data, so other instances can try
        os.remove(fname)

def make_tb_copy(src):
    dst = os.path.join(tmpdir, 
    ''.join(random.choices(string.ascii_uppercase + string.digits, k=24)))
    shutil.copytree(src, dst)
    return dst

def cleanup_tb_copy(c):
    return shutil.rmtree(c)

def visit(url, tb, timeout):
    tb = os.path.join(tb, "Browser", "start-tor-browser")
    subprocess.call("{} {} {} {}".format(args["v"], url, tb, timeout), shell=True)

def capture(fname):
    cmd = TSHARKFMT.format(args["i"], args["g"], args["s"], args["t"], fname)
    print(cmd)
    subprocess.call(cmd, shell=True)

def toggle_www(site):
    if site.startswith("www."):
        return site[4:]
    else:
        return "www."+site

def results_file(index, sample):
    return os.path.join(args["d"], RESULTSFMT.format(index, sample))

def get_alexa_list():
    l = []
    with open(args["l"]) as f:
        for r in csv.reader(f, delimiter=','):
            l.append((r[0], r[1]))
    return l

if __name__ == "__main__":
    main()
