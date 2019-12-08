#!/usr/bin/env python3

import argparse
import os
import sys

RESULTSFMT = "{}-{}.log"

ap = argparse.ArgumentParser()
ap.add_argument("-d", required=True,
    help="data folder for storing results")
args = vars(ap.parse_args())

def main():
    for site in range(0,500):
        for sample in range(0,20):
            if not os.path.exists(results_file(site, sample)):
                print(f"didnt find {results_file(site, sample)}")


def results_file(index, sample):
    return os.path.join(args["d"], RESULTSFMT.format(index, sample))

if __name__ == '__main__':
    main()