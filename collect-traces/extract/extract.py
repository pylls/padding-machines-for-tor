#!/usr/bin/env python3
import argparse
import os
import sys
import shutil
import circpadsim

''' Given an input and output folders, extract results.

Monitored: dimension, use backups, give error, check for already done

Unmonitored: num, check if done, pick random
'''
ap = argparse.ArgumentParser()
ap.add_argument("-i", required=True,
    help="input folder of logs")
ap.add_argument("-o", required=True,
    help="output folder for logs")
ap.add_argument("-t", required=True,
    help="output folder for traces")
ap.add_argument("-l", required=True,
    help="file with list of sites to visit, one site per line")

ap.add_argument("--monitored", required=False, default=False,
    action="store_true", help="extract monitored")
ap.add_argument("--unmonitored", required=False, default=False,
    action="store_true", help="extract unmonitored")

ap.add_argument("-c", required=False, type=int, default=500,
    help="the number of monitored classes")
ap.add_argument("-s", required=False, type=int, default=20,
    help="the number of samples")
ap.add_argument("-m", required=False, default=100, type=int,
    help="minimum number of lines in a trace")
args = vars(ap.parse_args())

def main():
    if (
        (args["monitored"] and args["unmonitored"]) or
        (not args["monitored"] and not args["unmonitored"])
    ):
        sys.exit("needs exactly one of --monitored or --unmonitored")

    if not os.path.isdir(args["i"]):
        sys.exit(f"{args['i']} is not a directory")
    if not os.path.isdir(args["o"]):
        sys.exit(f"{args['o']} is not a directory")
    if not os.path.isdir(args["t"]):
        sys.exit(f"{args['t']} is not a directory")

    inlist = os.listdir(args["i"])
    if len(inlist) < args["c"]*args["s"]:
        sys.exit(
            f'tasked to extract {args["c"]*args["s"]} samples, '
            f'but {args["i"]} contains at most '
            f'{len(inlist)} samples'
        )

    outlist = os.listdir(args["o"])
    if len(outlist) > 0:
        sys.exit(f'{args["o"]} is not empty')

    tracelist = os.listdir(args["t"])
    if len(tracelist) > 0:
        sys.exit(f'{args["t"]} is not empty')
    
    print(f"reading sites list {args['l']}")
    sites = get_sites_list()
    print(f"ok, list has {len(sites)} starting sites")

    if args["monitored"]:
        print("monitored")
        for c in range(args["c"]):
            print(f"{c}-{0}")
            # every class has backup traces, that is, extract logs we collected,
            # starting from the intended sample counter until there is no more
            # such file
            backup = args["s"]
            site = sites[c]
            for i in range(args["s"]):
                infname = f"{c}-{i}.log"
                trace, readfname, backup = find_good_trace(c, i, backup, site)
                write_trace(trace, results_trace_file(infname))
                write_log(readfname, infname)
    else:
        print("unmonitored")
        n = 0
        for index, site in enumerate(sites):
            if n >= args["c"]*args["s"]:
                break

            infname = f"{index}-0.log"
            if not os.path.exists(os.path.join(args["i"], infname)):
                continue
            
            trace, good = extract_trace(infname, site)
            if not good:
                print(f"not good {infname}")
                continue
            
            write_trace(trace, results_trace_file(infname))
            write_log(infname, infname)        

            n += 1
            if n % 100 == 0:
                print(n)

def write_log(src, dst):
    shutil.copy(
        os.path.join(args["i"], src), 
        os.path.join(args["o"], dst)
    )

def write_trace(output, fname):
    # make time relative before writing
    base = -1
    with open(fname, "w") as f:
        for l in output:
            t = int(l[0])
            if base == -1:
                base = t
            t = t - base
            f.write(f"{t:016d} {l[1].strip()}\n")

def find_good_trace(c, i, backup, site):
    inst = i
    while True:
        infname = f"{c}-{inst}.log"
        if not os.path.exists(os.path.join(args["i"], infname)):
            sys.exit(f"not enough logs for class {c}, instance {i}")

        trace, good = extract_trace(infname, site)
        if good:
            return trace, infname, backup
        # no good, try a backup
        print(f"need backup for {c}-{i}")
        inst = backup
        backup += 1

def extract_trace(infname, site):
    circuits = {}
    with open(os.path.join(args["i"], infname), 'r') as f:
        circuits = circpadsim.circpad_extract_log_traces(f.readlines(),
            True, True, False, False, False, 10*1000)

    if len(circuits) == 0:
        return "", False

    # try to find the first circuit with our site that is of acceptable length
    for cid in circuits:
        for l in circuits[cid]:
            s = l[1].split(" ")
            if s[len(s)-1].rstrip() in site:
                if len(circuits[cid]) >= args["m"]:
                    return circuits[cid], True

    return "", False

def results_trace_file(fname):
    if os.path.splitext(fname)[1] == ".log":
          return os.path.join(args["t"], os.path.splitext(fname)[0]+'.trace')
    return os.path.join(args["t"], fname+'.trace')

def get_sites_list():
    l = []
    with open(args["l"]) as f:
        for line in f:
            site = line.rstrip()
            if site in l:
                print(f"warning, list of sites has duplicate: {site}")
            l.append(site)
    return l

if __name__ == "__main__":
    main()
