# Orchestrating trace collection

Here we describe how we collect traces using python, shell-scripts, and several
machines with docker. Collection is orchestrated by a collection server.

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

## Docker
1. On the machine(s) you want to use for collection, install docker. 
2. Build the Dockerfile in either `docker-debian` or `docker-ubuntu`, depending
   on what bets fits the enviornment where you built the custom `tor`binary. You
   build the container by running: `docker build -t wf-collect .` (note the
   dot).

## Run an experiment
1. Copy `tor-browser_en-US` that you modified earlier into `exp`. 
2. Run `./set_tb_permissions.sh`. 

Edit `run.sh` and then run it once you've setup a server.

## Setup a collection server
Run `server.py` on a server that can be reached from the docker containers. The
parameters to the script are largely self-explanatory:

```
usage: server.py [-h] -l L -n N -d D [-m M]

optional arguments:
  -h, --help  show this help message and exit
  -l L        file with list of sites to visit, one site per line
  -n N        number of samples
  -d D        data folder for storing results
  -m M        minimum number of lines in torlog to accept
```

All clients will attempt to get work from the server, and on failure, sleeps for
the specified timeout (default: 60s) before trying again.