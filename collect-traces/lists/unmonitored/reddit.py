#!/usr/bin/env python3
import argparse
import sys
import os
import praw
from urllib.parse import urlsplit

ap = argparse.ArgumentParser()
ap.add_argument("-m", required=True, default="",
    help="location of monitored list to load")
ap.add_argument("-u", required=True, default="",
    help="location of unmonitored list to save")
ap.add_argument("-n", required=True, type=int,
    help="the total number of unique sites to get")
args = vars(ap.parse_args())

blacklist = [
    # remove direct image links
    ".gif",
    ".jpg",
    ".jpeg",
    ".png",
    # remove image hosting sites
    "redd.it",
    "reddit.com",
    "reddituploads.com",
    "imgur.com",
    "gfycat.com",
    # youtube and twitter both treat Tor bad
    "youtube.com",
    "youtu.be",
    "twitter.com",
]

def main():
    if not os.path.exists(args["m"]):
        sys.exit(f"{args['m']}, no such file (argument -m)")
    if os.path.exists(args["u"]):
        sys.exit(f"{args['u']} already exists")

    # load monitored list, clean the urls, filter on base
    monitored = get_sites_list()

    # loop over submissions until done
    reddit = praw.Reddit(client_id='REPLACE',
                    client_secret='REPLACE',
                    password='REPLACE',
                    user_agent='a research python script by /u/REPLACE, collecting URLs for website fingerprinting attacks',
                    username='REPLACE')    
    unmonitored = []
    count = 0
    with open(args["u"], 'w') as f:
        for submission in reddit.subreddit("all").top(time_filter="year", limit=args["n"]):
            count += 1
            # https://praw.readthedocs.io/en/latest/code_overview/models/submission.html
            base = base_url(submission.url)
            if not any(b in submission.url for b in blacklist):
                if not any(m in base for m in monitored):
                    print(f"base {base}\t full {submission.url}")
                    if not submission.url in unmonitored:
                        unmonitored.append(submission.url)
                        f.write(f"{submission.url}\n")

    print(f"\ngot {len(unmonitored)} sites, {count} submissions")

def get_sites_list():
    l = []
    with open(args["m"]) as f:
        for line in f:
            site = base_url(line.rstrip())
            # only add unique base URLs, faster lookup
            if not site in l:
                l.append(site)
    return l

def base_url(u):
    return urlsplit(u).netloc

if __name__ == "__main__":
    main()