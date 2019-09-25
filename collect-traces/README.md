# Orchestrating trace collection

Here we describe how we collect traces using python, shell-scripts, and several
machines with docker. First download this folder and a fresh Linux Tor Browser
install from torproject.org.

## Modify Tor Browser
Edit `Browser/start-tor-browser`, line 12, change it to:

```bash
if [ "x$DISPLAY" = "x" ] && [[ "$*" != *--headless* ]]; then
```

This makes it possible to run Tor Browser in headless mode without a full X
install (no more `xvfb`, yay). 

Start Tor Browser, in `about:config`, set:

- `browser.aboutHomeSnippets.updateUrl` to `""`
- `browser.startup.homepage_override.mstone` to `ignore`
- `extensions.blocklist.enabled` to `false`

Above are minimal changes according to Mozilla's guide to [stop Firefox from
making automatic
connections](https://support.mozilla.org/en-US/kb/how-stop-firefox-making-automatic-connections).

Edit `Browser/TorBrowser/Data/Tor/torrc` and set any necessary restrictions on
`EntryNodes` and/or `MiddleNodes`, depending on experiment to run. 

## Docker
1. On the machine(s) you want to use for collection, install docker. 
2. Build the Dockerfile by `cd collect-traces/docker` and `docker build -t
   wf-collect .` (note the dot).

## Run an experiment
1. Copy `tor-browser_en-US` that you modified earlier into `exp`. 
2. From `exp`, run `./set_tb_permissions.sh`. 
3. Create a sub-folder in `exp` for the results data, in our case, `mkdir data`, and
   give complete access: `chmod 777 data` (lazy, but works).

Edit `run.sh` and then run it from this folder: `./run.sh`. This runs the number
of docker containers specified.

The docker containers will use the results folder to coordinate trace
collection. If you're using several machines to run many containers, you have at
least two options:

1. Split by samples, that is, have each machine download a subset of the total
   number of samples then manually merge (and rename) afterwards. We'll provide
   a script for this (TODO).
2. On all machines, mount a remote filesystem and use it to coordinate across
   containers and machines.