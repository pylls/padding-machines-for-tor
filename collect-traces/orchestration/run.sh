#!/bin/bash

# the number of docker instances to create
WORKERS=2

# the absolute path to the experiment folder where you put collect.py and
# visit.py, as well as your list of URLs
FOLDER=/home/pulls/test/

# filename of your list of URLs to collect from
LIST=top10.csv

# number of samples to collect per URL
SAMPLES=2

# subfolder of FOLDER to store data in. Needs write permissions (chmod 777)
DATA=data

# the IP-address to the guard set in torrc
GUARD=171.25.193.77

# the number of seconds to collect data for per instance visit
TIMEOUT=30

# There are some more possible settings in collect.py, see there and set them
# below if you want, typically the defaults should be OK. 

for ((n=0;n<$WORKERS;n++)) do
    echo docker run -d --rm --cap-add=NET_RAW --cap-add=NET_ADMIN \
    -v $FOLDER:/home/user/exp wf-collect \
    python3 exp/collect.py -v exp/visit.sh \
    -b /home/user/exp/tor-browser_en-US/ \
    -l exp/$LIST \
    -n $SAMPLES \
    -d /home/user/exp/$DATA \
    -g $GUARD \
    -t $TIMEOUT
done

