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
import time
import random
import subprocess
import os
import threading

ap = argparse.ArgumentParser()
ap.add_argument("-l", required=True,
    help="Alexa file with list of sites to visit")
ap.add_argument("-n", required=True, type=int,
    help="number of samples")
ap.add_argument("-r", required=True,
    help="shared folder for storing results")
ap.add_argument("-g", required=True, 
    help="IP address of guard")

ap.add_argument("-a", required=False, default=5, type=int,
    help="number of attempts to collect each trace")
ap.add_argument("-t", required=False, default=60, type=int,
    help="timeout (s) for each TB visit")
ap.add_argument("-i", required=False, default="eth0",
    help="network interface to capture from")
ap.add_argument("-s", required=False, default=68, type=int,
    help="snaplen to capture")
args = vars(ap.parse_args())

RESULTSFMT = "{}-{}.pcap"
TSHARKFMT = "tshark -i {} -f \"host {}\" -s {} -a duration:{} -w {} -F libpcap"

def main():
    print("reading Alexa site list {}".format(args["l"]))
    alexa = get_alexa_list()
    print("ok, list has {} sites".format(len(alexa)))

    # FIXME warmup visits? 

    # random order of samples and alexa, ensuring that each instance of this
    # script won't be working on the same alexa-sample pair
    samples = [i for i in range(args["n"])]
    random.shuffle(samples)
    for n in samples:
        random.shuffle(alexa)
        for index, site in alexa:
            # only attempt to collect if not already collected
            if not os.path.isfile(RESULTSFMT.format(index, n)):
                collect(index, site, n)

def collect(index, site, sample):
    print("collect index {}, site {}, sample {}".format(index, site, sample))
    #subprocess.call("./visit.sh {} {}".format(site, sample), shell=True)
    fname = RESULTSFMT.format(index, sample)

    for a in range(args["a"]):
        if a % 2 == 0:
            site = togglewww(site)
        
        # start network capture in new thread
        t = threading.Thread(target=capture, args=(fname,))
        t.start()

        # fixme: sleep briefly, giving the thread time to start

        # visit with TB, blocking

        # wait for network capture to finish
        t.join()

        # if capture was successful, break
        # FIXME: check based on filesize (?), set constant

def capture(fname):
    print(TSHARKFMT.format(args["i"], args["g"], args["s"], args["t"], fname))

def togglewww(site):
    if site.startswith("www."):
        return site[4:]
    else:
        return "www."+site

def get_alexa_list():
    l = []
    with open(args["l"]) as f:
        for r in csv.reader(f, delimiter=','):
            l.append((r[0], r[1]))
    return l

if __name__ == "__main__":
    main()
