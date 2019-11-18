#!/bin/bash

# the number of docker instances to create
WORKERS=2

# the absolute path to the experiment folder where you put collect.py and
# visit.py, as well as your list of URLs
FOLDER=/home/pylls/collect-traces/exp/

# the number of seconds to collect data for per instance visit
TIMEOUT=60

# the minimum number of circpad trace events to accept
MIN=100

# the URL of the server
SERVER=http://example.com:5000

for ((n=0;n<$WORKERS;n++)) do
    echo docker run -d wf-collect \
    python3 -u exp/collect.py \
    -b /home/user/exp/tor-browser_en-US/ \
    -u SERVER \
    -m MIN \
    -t $TIMEOUT
done
