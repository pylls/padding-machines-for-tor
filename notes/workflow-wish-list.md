# Workflow Wish List
Here we briefly note the expected high-level workflow for creating padding
machines for tor's circuit padding framework. The goals are to document and in
the process identify key tools (read: typically shell or Python scripts) we can
create to ease our work.

To iteratively design-implement-evaluate padding machines:

1. Modify `src/core/or/circuitpadding_machines.{h,c}` and/or
   `src/core/or/circuitpadding.{h,c}`, resulting in a modified `tor` binary. 
2. Deploy modified `tor` to:
   1.  dedicated relay(s) acting as guard or middle, and
   2.  Tor Browser clients.
3. Visit a couple of websites and manually inspect the log outputs of `tor` from
   the client and the relay.
4. Collect a WF dataset in the open world with and without the implemented
   machine of different sizes.
5. Split the dataset intro train-validate-testing (8:1:1). 
6. Train selected WF attacks on dataset:
   1. [Deep Fingerprinting](https://github.com/deep-fingerprinting/df) is the go-to due to relative fast training times.
   2. [Var-CNN](https://people.csail.mit.edu/devadas/pubs/varcnn.pdf) when defenses show promise, especially on small datasets. 
7. Test on the dataset, producing metrics and graphs.
8. Evaluate results and go back to 1.

Ideally, we can create tooling to automate the above steps into:

- Run `test-machine.py`, performs steps 1-3, producing client+relay
  logs.
- Run `quick-eval.py`, performs steps 4-7, collecting a small dataset and only
  using DF, producing metrics and graphs.

### Refining Tooling

For `test-machine.py`:

1. Building tor is as easy as `make` once dependencies and configuration are done
once. 
2. Deploying to:
   1. a relay is just a matter of `scp`/`ssh` and restarting the tor process. 
   2. Tor Browser depends on how we orchestrate clients, but likely a simple
       `scp` to a server that clients pull from on visit. 
3. Getting logs from:
   1. a relay is as simple as `scp` to the preconfigured log file (by editing
      `torrc`). We need to take care not to run out of disk space though if
      logging at `debug` level. Does `tor` support some sort of log rotation?
   2. a client depends on how we orchestrate clients, but likely just log to
      file and `scp` back after a fixed delay. For Tor Browser to log,  
      first edit `torrc` to set verbosity level (`Log debug stdout`) and then
      run Tor Browser with `./start-tor-browser.desktop --log output.log`.

For `quick-eval.py`: step 4, it depends on how we orchestrate clients. Steps
5-7 we will reuse tooling from another project (not yet released). 

### Logs and Packets from Tor Browser
 `start-tor-browser.desktop --log here.log --headless --screenshot /home/user/Downloads/tor-browser_en-US/kau.se kau.se`

[Consider future UC.]

### Client Orchestration
https://github.com/webfp/tor-browser-selenium would be the go-to option. Brings
many dependencies though. Worthwhile to tackle now?