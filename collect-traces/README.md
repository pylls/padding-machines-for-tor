# Howto collect a lot of traces
Here we describe how we collect traces from Tor Browser in a large scale with
relative ease. We make basic use of python, shell-scripts, and containers. The
idea is to run many headless Tor Browser clients in containers that repeatedly
get work from a collection server. The work consists of a URL to visit. While
visiting a URL the client records its tor log and uploads it the server.

Note that everything in this folder is of *research quality*, we share this with
the hope of making it easier for other researchers.

## Modify Tor Browser
First download this folder and a fresh Linux Tor Browser install from
torproject.org. Edit `Browser/start-tor-browser`, line 12, change it to:

```bash
if [ "x$DISPLAY" = "x" ] && [[ "$*" != *--headless* ]]; then
```

This makes it possible to run Tor Browser in headless mode without a full X
install (no more `xvfb`, yay).

Edit `Browser/TorBrowser/Data/Tor/torrc` and set any necessary restrictions,
e.g., `EntryNodes`, `MiddleNodes` or`UseEntryGuards`, depending on experiment to
run. If you're using the [circuitpadding
simulator](https://github.com/pylls/circpad-sim), build the custom `tor` binary,
add it to TB at `Browser/TorBrowser/Tor/`, and add ``Log [circ]info notice
stdout'' to `torrc`.

When we collected our traces for the goodenough dataset we used the following torrc:

```
Log [circ]info notice stdout
UseEntryGuards 0
```

## Build the docker container
1. On the machine(s) you want to use for collection, install docker. 
2. Build the Dockerfile in either `docker-debian` or `docker-ubuntu`, depending
   on what fits the environment where you built the custom `tor`binary. You
   build the container by running: `docker build -t wf-collect .` (note the
   dot).

## Starting containers
On each machine:
1. Copy `tor-browser_en-US` that you modified earlier into `exp`. 
2. Run `./set_tb_permissions.sh`. 

Edit `run.sh` and then run it.

For our experiments we created three zip-files of Tor Browser with different
security levels/settings set and put them all in the `exp` folder. We then used
the following command to rotate on each machine:

```
rm -rf collect/exp/tor-browser_en-US && cd collect/exp/ && unzip tor-browser_en-US-safest.zip && cd ../ && ./set_tb_permissions.sh && ./run.sh
```

## Setup a collection server
Run `circpad-server.py` on a server that can be reached from the docker
containers. The parameters to the script are largely self-explanatory:

```
usage: circpad-server.py [-h] -l L -n N -d D [-m M] [-s S]

optional arguments:
  -h, --help  show this help message and exit
  -l L        file with list of sites to visit, one site per line
  -n N        number of samples
  -d D        data folder for storing results
  -m M        minimum number of lines in torlog to accept
  -s S        stop collecting at this many logs collected, regardless of
              remaining sites or samples (useful for unmonitored sites)
```

All clients will attempt to get work from the server, and on failure, sleeps for
the specified timeout (default: 60s) before trying again. For our experiments we
used 7 machines with 20 containers each talking to a server with a single modest
core without much trouble. All machines, including the server, were located in
the same cluster. Running the server on separate physical machines may mean the
server becomes a too-big bottleneck during collection due to being single
threaded.

## Extract traces from the dataset
Once you've collected your raw dataset the next step is to extract the useful
logs and get some circpad traces. The `extract` folder contains all you need:
the `extract.py` script will verify that the logs contain traces from visiting
the intended websites and structure the dataset as in our goodenough dataset.

```
usage: extract.py [-h] -i I -o O -t T -l L [--monitored] [--unmonitored]
                  [-c C] [-s S] [-m M]

optional arguments:
  -h, --help     show this help message and exit
  -i I           input folder of logs
  -o O           output folder for logs
  -t T           output folder for traces
  -l L           file with list of sites to visit, one site per line
  --monitored    extract monitored
  --unmonitored  extract unmonitored
  -c C           the number of monitored classes
  -s S           the number of samples
  -m M           minimum number of lines in a trace
```

See the helper `all.sh` script for examples on how to use `extract.py`.