#!/usr/bin/env python3
import argparse
import os
import random
import sys
from flask import Flask, request

app = Flask(__name__)

ap = argparse.ArgumentParser()
ap.add_argument("-l", required=True,
    help="file with list of sites to visit, one site per line")
ap.add_argument("-n", required=True, type=int,
    help="number of samples")
ap.add_argument("-d", required=True,
    help="data folder for storing results")

ap.add_argument("-m", required=False, default=500, type=int,
    help="minimum number of lines in torlog to accept")
ap.add_argument("-s", required=False, default=-1, type=int,
    help="stop collecting at this many logs collected, regardless of remaining sites or samples (useful for unmonitored sites)")
args = vars(ap.parse_args())

RESULTSFMT = "{}-{}.log"

sites = []
remaining_sites = []
collected_samples = {}
total_collected = 0

def main():
    global total_collected

    if not os.path.exists(args["d"]):
        sys.exit(f"data directory {args['d']} does not exist")

    print(f"reading sites list {args['l']}")
    starting_sites = get_sites_list()
    print(f"ok, list has {len(starting_sites)} starting sites")

    for site in starting_sites:
        sites.append(site)
        remaining_sites.append(site)
        collected_samples[site] = 0

        for _ in range(args["n"]):
            if os.path.isfile(results_file(site)):
                total_collected = total_collected + 1
                # record the collected sample
                collected_samples[site] = collected_samples[site] + 1
                # if we got enough samples, all done
                if collected_samples[site] >= args["n"]:
                    remaining_sites.remove(site)
    
    if args["s"] > 0 and total_collected >= args["s"]:
        sys.exit(f"already done, collected {total_collected} logs")

    if args["s"] > 0:
        remaining = args['s'] - total_collected
        print(f"set to collect {args['s']} logs, need {remaining} more")
    
    print(f"list has {len(remaining_sites)} remaining sites")

    app.run(host="0.0.0.0", threaded=False)

@app.route('/', methods=['GET', 'POST'])
def handler():
    if request.method == 'POST':
        add_log(request.form['log'], request.form['site']) 
    return get_next_item()

def add_log(log, site):
    log = log.split("\n")
    
    # already done?
    if not site in remaining_sites:
        print(f"\t got already done site")
        return
    # log too small to accept?
    if len(log) < args["m"]:
        print(f"\t got too small log")
        return

    print(f"\tgot log of {len(log)} events for site {site}")

    # store the log
    with open(results_file(site), 'w') as f:
        for l in log:
            f.write(f"{l}\n")

    # update count of samples
    collected_samples[site] = collected_samples[site] + 1
    if collected_samples[site] >= args["n"]:
        remaining_sites.remove(site)

def get_next_item():
    next = ""
    if len(remaining_sites) > 0:
        random.shuffle(remaining_sites)
        next = remaining_sites[0]
    print(f"\tnext item is {next}")
    return next

def get_sites_list():
    l = []
    with open(args["l"]) as f:
        for line in f:
            site = line.rstrip()
            if site in l:
                print(f"warning, list of sites has duplicate: {site}")
            l.append(site)
    return l

def results_file(site):
    index = sites.index(site)
    sample = collected_samples[site]
    return os.path.join(args["d"], RESULTSFMT.format(index, sample))

if __name__ == '__main__':
    main()