# A Padding Machine from Scratch

This document describes the process of building a "padding machine" in tor's new
circuit padding framework from scratch. Notes were taken as part of porting APE
from basket2 to the circuit padding framework. The goal is just to document the
process and provide useful pointers along the way, not create a useful machine. 

The quick and dirty plan is to:
1. clone and compile tor
2. use newly built tor in TB and at small (non-exit) relay we run
3. add an empty APE machine in the framework, make it run locally in TB without
   crashing
4. add a log message during padding machine negotiation and observe it in TB and
   at the relay
5. port APE without thinking much about parameters

## Clone and compile tor

```bash
git clone https://git.torproject.org/tor.git
cd tor
git checkout tor-0.4.1.5
```
Above we use the tag for tor-0.4.1.5 where the circuit padding framework was
released, feel free to use somethinf newer (avoid HEAD though, can have bugs).

```bash
sh autogen.sh 
./configure
make
```
When you run `./configure` you'll be told of missing dependencies and packages
to install on debian-based distributions. If you want to install on your local
system, run `make install`. For our case we just want the tor binary at
`src/app/tor`.

## Use tor in TB and at a relay
Download and install a fresh Tor Browser (TB) from torproject.org. Make sure it
works. From the command line, relative to the folder created when you extracted
TB, run `./Browser/start-tor-browser --verbose` to get some basic log output.
Note the version of tor, in my case, `Tor 0.4.0.5 (git-bf071e34aa26e096)` as
part of TB 8.5.4. Shut down TB, copy the `tor` binary that you compiled earlier
and replace `Browser/TorBrowser/Tor/tor`. Start TB from the command line again,
you should see a different version, in my case `Tor 0.4.1.5
(git-439ca48989ece545)`.

The relay we run is also on linux, and `tor` is located at `/usr/bin/tor`. To
view relevant logs since last boot `sudo journalctl -b /usr/bin/tor`, where we
find `Tor 0.4.0.5 running on Linux`. Copy the locally compiled `tor` to the
relay at a temporary location and then make sure it's ownership and access
rights are identical to `/usr/bin/tor`. Next, shut down the running tor service
with `sudo service tor stop`, wait for it to stop (typically 30s), copy our
locally compiled tor to replace `/usr/bin/tor` then start the service again.
Checking the logs we see `or 0.4.1.5 (git-439ca48989ece545)`.

Repeatedly shutting down a relay is detrimental to the network and should be
avoided. Sorry about that.

We have one more step left before we move on the machine: configure TB to always
use our middle relay. Edit `Browser/TorBrowser/Data/Tor/torrc` and set
`MiddleNodes <fingerprint>`, where `<fingerprint>` is the fingerprint of the
relay. Start TB, visit a website, and manually confirm that the middle is used
by looking at the circuit display. 

## Add an empty APE machine