#!/usr/bin/env python3
import argparse
import os
import random
import socket
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
    next = get_next_item()
    print(f"\tnext item is {next}")
    return next

def add_log(log, site):
    global total_collected
    
    # already done?
    if not site in remaining_sites:
        print(f"\t got already done site")
        return

    log = log.split("\n")

    if not is_complete_circpad_log(log):
        print(f"\t got incomplete log for {site}")
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
        total_collected += 1

def is_complete_circpad_log(log):
    circuits = circpad_extract_log_traces(log)
    n = 0
    for cid in circuits:
        if len(circuits[cid]) >= args["m"]:
            n += 1
    
    # A "complete" circpad log has exactly one sizeable trace, but at times we
    # get extra traces, e.g., due to TB extensions phoning home. I found that
    # the best approach was to collect potentially some less useful logs and
    # then discard at the end (see extraction tools).
    # return n == 1

    # at least we got one log that looks good
    return n >= 1

def get_next_item():
    global total_collected

    # already done?
    if args["s"] > 0 and total_collected >= args["s"]:
        return ""

    # got more work?
    if len(remaining_sites) > 0:
        random.shuffle(remaining_sites)
        return remaining_sites[0]

    return ""

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


CIRCPAD_ERROR_WRONG_FORMAT = "invalid trace format"
CIRCPAD_ADDRESS_EVENT = "connection_ap_handshake_send_begin"
CIRCPAD_EVENT_NONPADDING_SENT = "circpad_cell_event_nonpadding_sent"

CIRCPAD_LOG = "circpad_trace_event"
CIRCPAD_LOG_TIMESTAMP = "timestamp="
CIRCPAD_LOG_CIRC_ID = "client_circ_id="
CIRCPAD_LOG_EVENT = "event="

CIRCPAD_BLACKLISTED_ADDRESSES = ["aus1.torproject.org"]
CIRCPAD_BLACKLISTED_EVENTS = [
    "circpad_negotiate_logging"
]

def circpad_get_all_addresses(trace):
    addresses = []
    for l in trace:
        if len(l) < 2:
            sys.exit(CIRCPAD_ERROR_WRONG_FORMAT)
        if CIRCPAD_ADDRESS_EVENT in l[1]:
            if len(l[1]) < 2:
                sys.exit(CIRCPAD_ERROR_WRONG_FORMAT)
            addresses.append(l[1].split()[1])
    return addresses

def circpad_parse_line(line):
    split = line.split()
    assert(len(split) >= 2)
    event = split[1]
    timestamp = int(split[0])

    return event, timestamp

def circpad_lines_to_trace(lines):
    trace = []
    for l in lines:
        event, timestamp = circpad_parse_line(l)
        trace.append((timestamp, event))
    return trace

def circpad_extract_log_traces(
    log_lines,
    source_client=True,
    source_relay=True,
    allow_ips=False,
    filter_client_negotiate=False,
    filter_relay_negotiate=False
    ):
    # helper function
    def blacklist_hit(d):
        for a in circpad_get_all_addresses(d):
            if a in CIRCPAD_BLACKLISTED_ADDRESSES:
                return True
        return False

    # helper to extract one line
    def extract_from_line(line):
        n = line.index(CIRCPAD_LOG_TIMESTAMP)+len(CIRCPAD_LOG_TIMESTAMP)
        timestamp = line[n:].split(" ", maxsplit=1)[0]
        n = line.index(CIRCPAD_LOG_CIRC_ID)+len(CIRCPAD_LOG_CIRC_ID)
        cid = line[n:].split(" ", maxsplit=1)[0]

        # an event is the last part, no need to split on space like we did earlier
        n = line.index(CIRCPAD_LOG_EVENT)+len(CIRCPAD_LOG_EVENT)
        event = line[n:]
        
        return int(cid), int(timestamp), event

    circuits = {}
    base = -1
    for line in log_lines:
        if CIRCPAD_LOG in line:
            # skip client/relay if they shouldn't be part of the trace
            if not source_client and "source=client" in line:
                continue
            if not source_relay and "source=relay" in line:
                continue

            # extract trace and make timestamps relative
            cid, timestamp, event = extract_from_line(line)
            if base == -1:
                base = timestamp
            timestamp = timestamp - base

            # store trace
            if cid in circuits.keys():
                circuits[cid] = circuits.get(cid) + [(timestamp, event)]
            else:
                circuits[cid] = [(timestamp, event)]

    # filter out circuits with blacklisted addresses
    for cid in list(circuits.keys()):
        if blacklist_hit(circuits[cid]):
            del circuits[cid]
    # filter out circuits with only IPs (unless arg says otherwise)
    for cid in list(circuits.keys()):
        if not allow_ips and circpad_only_ips_in_trace(circuits[cid]):
            del circuits[cid]

    # remove blacklisted events (and associated events)
    for cid in list(circuits.keys()):
        circuits[cid] = circpad_remove_blacklisted_events(circuits[cid],
                        filter_client_negotiate, filter_relay_negotiate)
    
    return circuits
    

def circpad_remove_blacklisted_events(
    trace, 
    filter_client_negotiate, 
    filter_relay_negotiate
    ):
    
    result = []
    ignore_next_send_cell = True

    for line in trace:
        # If we hit a blacklisted event, this means we should ignore the next
        # sent nonpadding cell. Since the blacklisted event should only be
        # triggered client-side, there shouldn't be any impact on relay traces.
        if any(b in line for b in CIRCPAD_BLACKLISTED_EVENTS):
            ignore_next_send_cell = True
        else:
            if ignore_next_send_cell and CIRCPAD_EVENT_NONPADDING_SENT in line:
                ignore_next_send_cell = False
            else:
                result.append(line)
                
    return result

def circpad_only_ips_in_trace(trace):
    def is_ipv4(addr):
        try:
            socket.inet_aton(addr)
        except (socket.error, TypeError):
            return False
        return True
    def is_ipv6(addr):
        try:
            socket.inet_pton(addr,socket.AF_INET6)
        except (socket.error, TypeError):
            return False
        return True

    for a in circpad_get_all_addresses(trace):
        if not is_ipv4(a) and not is_ipv6(a):
            return False
    return True

if __name__ == '__main__':
    main()
