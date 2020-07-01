# Howto use tweak.py

Below is an example of how to run `tweak.py`:
```
./tweak.py --client dataset-feb/standard/client-traces/ --relay dataset-feb/standard/fakerelay-traces/ -t ../tor --mc client-machine --mr relay-machine --save tmp.pkl
```

The help output explains most flags:

```
usage: tweak.py [-h] --client CLIENT --relay RELAY [-c C] [-p P] [-s S] -t T [-w W] [-l L] --mc MC --mr MR --save SAVE

optional arguments:
  -h, --help       show this help message and exit
  --client CLIENT  input folder of client circpadtrace files
  --relay RELAY    input folder of relay circpadtrace files
  -c C             the number of monitored classes
  -p P             the number of partitions
  -s S             the number of samples
  -t T             path to tor folder (bob/tor, not bob/tor/src)
  -w W             number of workers for simulating machines
  -l L             max length of extracted cells
  --mc MC          path to file of client machine (c-code) to tweak
  --mr MR          path to file of relay machine (c-code) to tweak
  --save SAVE      file to save results to
```

The expected input format (`--client` and `--relay`) is that of the dataset in
this repository. For the tor folder (`-t`), see
[circpad-sim](https://github.com/pylls/circpad-sim). Machines you tweak (`--mc`
and `--mr`) have to be of the appropriate format. Several examples are available
in
[machines/phase2/](https://github.com/pylls/padding-machines-for-tor/tree/master/machines/phase2/).

For how to use tweak.py as part of tweaking a padding machine, see `tweak.sh` in
this folder and the [phase 2
writeup]((https://github.com/pylls/padding-machines-for-tor/tree/master/machines/phase2/)).
