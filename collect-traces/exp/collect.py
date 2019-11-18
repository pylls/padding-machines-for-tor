#!/usr/bin/env python3
"""Collect Network Traces from Tor Browser

We assume that this script will execute from multiple containers that share the
exact same script arguments. The script gets its work and uploads the traces it
collects to the sever at the specific url.
"""
import argparse
import os
import sys
import random
import shutil
import string
import tempfile
import time
import datetime
import subprocess
import signal

import requests
from requests.exceptions import Timeout

ap = argparse.ArgumentParser()
ap.add_argument("-b", required=True, 
    help="folder with Tor Browser")
ap.add_argument("-u", required=True, 
    help="the complete URL to the server")

ap.add_argument("-a", required=False, default=5, type=int,
    help="number of attempts to collect each trace")
ap.add_argument("-t", required=False, default=60, type=int,
    help="timeout (s) for each TB visit")
ap.add_argument("-m", required=False, default=100, type=int,
    help="minimum number of liens in torlog to accept")
args = vars(ap.parse_args())

TBFILE = "start-tor-browser.desktop"
CIRCPAD_EVENT = "circpad_trace_event"

tmpdir  = tmpdir = tempfile.mkdtemp()

def main():
    if not os.path.exists(args["b"]):
        sys.exit(f"Tor Browser directory {args['b']} does not exist")
    if not os.path.isfile(os.path.join(args["b"], TBFILE)):
        sys.exit(f"Tor Browser directory {args['b']} missing {TBFILE}")

    # on SIGINT remove the temporary folder
    def signal_handler(sig, frame):
        shutil.rmtree(tmpdir)
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    tb = make_tb_copy(args["b"])
    print("two warmup visits for fresh consensus and whatnot update checks")
    print(f"\t got {len(visit('kau.se/en', tb, args['t']))} log-lines")
    print(f"\t got {len(visit('kau.se/en/cs', tb, args['t']))} log-lines")

    work = ""
    last_site = ""
    while True:
        # either work will be empty or contain the log from collecting below
        if work == "":
            # get new work
            work = get_work()
        else:
            # upload work and get new work
            work = upload_work(work, last_site)

        # do any work if we got any, or sleep a bit
        if work != "":
            last_site = work
            work = collect(last_site, tb)
        else:
            time.sleep(args["t"])

    # cleanup, if we ever get here somehow
    shutil.rmtree(tmpdir)

def get_work():
    try:
        response = requests.get(args["u"], timeout=args["t"])
        if response:
            return response.content.decode('UTF-8')
    except Timeout:
        return ""
    return ""

def upload_work(log, site):
    print(f"\t {now()} uploading log of len {len(log)}...")

    try:
        response = requests.post(
            args["u"],
            timeout=args["t"],
            data=[('log', '\n'.join(log)), ('site', site)]
        )
        if response:
            return response.content.decode('UTF-8')
    except Timeout:
        return ""
    return ""

def collect(site, tb_orig):
    print(f"attempting to collect site {site}")
    for _ in range(args["a"]):
        # create fresh TB copy for this visit
        tb = make_tb_copy(tb_orig)

        # visit with TB, blocking, and get stdout (the log)
        log = visit(site, tb, args["t"])
        print(f"\t {now()} got {len(log)} circpad events in log")

        # cleanup our TB copy
        shutil.rmtree(tb)

        # done if long enough trace
        if len(log) >= args["m"]:
            return log
    
    return ""

def make_tb_copy(src):
    dst = os.path.join(tmpdir, 
    ''.join(random.choices(string.ascii_uppercase + string.digits, k=24)))

    # ibus breaks on multiple copies that move location, need to ignore
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('ibus'))
    return dst

def visit(url, tb, timeout):
    tb = os.path.join(tb, "Browser", "start-tor-browser")
    url = url.replace("'", "\\'")
    url = url.replace(";", "\;")
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
    ''' Filters the log for trace events from the circuitpadding 
    framework, saving space.
    '''
    out = []
    lines = stdout.split("\n")
    for l in lines:
        if CIRCPAD_EVENT in l:
            out.append(l)
    
    return out

def now():
    return datetime.datetime.now()

if __name__ == "__main__":
    main()
