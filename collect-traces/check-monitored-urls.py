#!/usr/bin/env python3

import argparse
import os
import sys

RESULTSFMT = "{}-{}.log"

ap = argparse.ArgumentParser()
ap.add_argument("-d", required=True,
    help="data folder for storing results")
ap.add_argument("-l", required=True,
    help="file with list of sites to visit, one site per line")
args = vars(ap.parse_args())

def main():
    print(f"reading sites list {args['l']}")
    starting_sites = get_sites_list()
    print(f"ok, list has {len(starting_sites)} starting sites")

    for index, site in enumerate(starting_sites):
        for sample in range(0,20):
            if not os.path.exists(results_file(index, sample)):
                print(f"didnt find {results_file(index, sample)}")
                continue
            found = 0
            with open(results_file(index, sample), 'r') as f:
                for l in f:
                    s = l.split(" ")
                    if s[len(s)-1].rstrip() in site:
                        found = 1
                        break
            if found == 0:
                print(f"didn't find {site} in {results_file(index, sample)}")

def results_file(index, sample):
    return os.path.join(args["d"], RESULTSFMT.format(index, sample))

def get_sites_list():
    l = []
    with open(args["l"]) as f:
        for line in f:
            site = line.rstrip()
            if site in l:
                print(f"warning, list of sites has duplicate: {site}")
            l.append(site)
    return l

if __name__ == '__main__':
    main()