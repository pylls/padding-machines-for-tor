#!/bin/bash

# the number of docker instances to create
WORKERS=2

# the absolute path to the experiment folder where you put collect.py and
# visit.py, as well as your list of URLs
FOLDER=/home/pylls/collect-traces/exp/

# filename of your list of URLs to collect from
LIST=top-50-selected-multi.list

# number of samples to collect per URL
SAMPLES=2

# subfolder of FOLDER to store data in. Needs write permissions (chmod 777)
DATA=data

# the number of seconds to collect data for per instance visit
TIMEOUT=60

# There are some more possible settings in collect.py, see there and set them
# below if you want, typically the defaults should be OK. 

for ((n=0;n<$WORKERS;n++)) do
    echo docker run -d \
    -v $FOLDER:/home/user/exp wf-collect \
    python3 -u exp/collect.py \
    -b /home/user/exp/tor-browser_en-US/ \
    -l exp/lists/$LIST \
    -n $SAMPLES \
    -d /home/user/exp/$DATA \
    -t $TIMEOUT
done
