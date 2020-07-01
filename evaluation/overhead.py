#!/usr/bin/env python3
import argparse
import shared
import pickle
import sys
import os
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--ld", required=True,
    help="load dataset from pickle, provide path to pickled file")
args = vars(ap.parse_args())

def main():
    '''Bandwidth overhead is based on number of padding and non-padding cells in
    all traces.
    '''
    print(f"attempting to load dataset from pickle file {args['ld']}")
    dataset, labels = pickle.load(open(args["ld"], "rb"))

    t_sent_padding = []
    t_sent_nonpadding = []
    t_sent_overhead = []
    t_recv_padding = []
    t_recv_nonpadding = []
    t_recv_overhead = []

    for trace in dataset:
        unique, counts = np.unique(dataset[trace][0], return_counts=True)
        d = dict(zip(unique, counts))
        sent_nonpadding = d[1]
        recv_nonpadding = d[-1]
        
        sent_padding = 0
        if 2 in d:
            sent_padding = d[2]

        recv_padding = 0
        if -2 in d:
            recv_padding = d[-2]
            
        if sent_nonpadding == 0:
            sys.exit(f"sent 0 nonpadding cells, broken trace?")
        if recv_nonpadding == 0:
            sys.exit(f"recv 0 nonpadding cells, broken trace?")

        t_sent_padding.append(sent_padding)
        t_sent_nonpadding.append(sent_nonpadding)
        t_sent_overhead.append(float(sent_padding+sent_nonpadding) / float(sent_nonpadding))

        t_recv_padding.append(recv_padding)
        t_recv_nonpadding.append(recv_nonpadding)
        t_recv_overhead.append(float(recv_padding+recv_nonpadding) / float(recv_nonpadding))

    sent_padding = sum(t_sent_padding)
    sent_nonpadding = sum(t_sent_nonpadding)
    sent_cells = sent_padding + sent_nonpadding
    
    recv_padding = sum(t_recv_padding)
    recv_nonpadding = sum(t_recv_nonpadding)
    recv_cells = recv_padding + recv_nonpadding

    total_cells = sent_cells + recv_cells

    avg_sent = float(sent_cells)/float(sent_nonpadding)
    avg_recv = float(recv_cells)/float(recv_nonpadding)
    avg_total = float(total_cells)/float(recv_nonpadding+sent_nonpadding)

    print(f"in total for {len(t_sent_padding)} traces:")
    print(f"\t- {total_cells} cells")
    print(f"\t- {avg_total:.0%} average total bandwidth")
    
    print(f"\t- {sent_cells} sent cells ({float(sent_cells)/float(total_cells):.0%})")
    print(f"\t\t- {sent_nonpadding} nonpadding")
    print(f"\t\t- {sent_padding} padding")
    print(f"\t\t- {avg_sent:.0%} average sent bandwidth")

    print(f"\t- {recv_cells} recv cells ({float(recv_cells)/float(total_cells):.0%})")
    print(f"\t\t- {recv_nonpadding} nonpadding")
    print(f"\t\t- {recv_padding} padding")
    print(f"\t\t- {avg_recv:.0%} average recv bandwidth")

if __name__ == "__main__":
    main()