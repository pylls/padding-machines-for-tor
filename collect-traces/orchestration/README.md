# Orchestrating trace collection

Clone this repo, download a fresh Linux Tor Browser install from torproject.org,
and then follow the below steps.

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
2. Build the Dockerfile by `cd collect-traces/orchestration/docker` and `docker
   build -t wf-collect .` (note the dot).

## Run an experiment

1. Create a folder for the collection. In this example, we'll use `mkdir /home/pulls/exp/`.
2. Copy `tor-browser_en-US` that you modified earlier to `exp`. 
3. From this repository, copy `run.sh`, `collect.py`, your csv file with
   websites (`top10.csv` here), and `visit.sh` to `exp`.
4. Run `chmod a+r -R tor-browser_en-US/` and `find tor-browser_en-US/ -type d
   -print0 | xargs -0 chmod 755` to enable the containers to get necessary
   access to Tor Browser. 
5. Create a sub-folder in `exp` for the results data, in our case, `mkdir data`, and
   give complete access: `chmod 777 data` (lazy, but works).

Edit `run.sh` before running it.