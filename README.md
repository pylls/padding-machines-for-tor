# Padding Machines for Tor
This is the repository for the [NGI Zero PET](https://nlnet.nl/PET/) project
"Padding Machines by Tor". The goal of the project was to create one or more
padding machines for Tor's new [circuit padding
framework](https://blog.torproject.org/new-release-tor-0405). The padding
machines should defend against [Website Fingerprinting (WF)
attacks](https://blog.torproject.org/critique-website-traffic-fingerprinting-attacks).

## Project Results
This project made several contributions with the help of additional funding from
[the Swedish Internet Foundation](https://internetstiftelsen.se/en/) for a
related project.

Notable results:
- [Developer notes on the circuit padding framework](notes/circuit-padding-framework.md).
- [Building a padding machine from scratch](notes/machine-from-scratch.md).
- [Implemented an APE-like padding machine](https://github.com/pylls/tor/tree/circuit-padding-ape-machine). 
- Tor trac tickets: [#31098](https://trac.torproject.org/projects/tor/ticket/31098),
  [#31111](https://trac.torproject.org/projects/tor/ticket/31111),
  [#31112](https://trac.torproject.org/projects/tor/ticket/31112),
  [#31113](https://trac.torproject.org/projects/tor/ticket/31113).

- [A minimal simulator](https://github.com/pylls/circpad-sim) for padding
  machines in Tor's circuit padding framework, see
  [#31788](https://trac.torproject.org/projects/tor/ticket/31788). 
- [Simple collection tools](collect-traces/) for collecting traces for the circpad simulator.
- [The goodenough dataset](dataset/) tailored to the circpad simulator and for
  creating "good enough" machines. 
- [An evaluation tool](evaluation/once.py) for running the Deep Fingerprinting
  (DF) attack against a dataset, producing a number of relevant metrics. Based
  on a port of DF to PyTorch.
- [An example machine](machines/hello-world.md) designed, implemented,
  evaluated, and documented.
- [Evolved machines using genetic programming](machines/phase2). The best
  machine is a more effective defense against DF than WTF-PAD.
- [The final padding machines for Tor](machines/phase3) consisting of a
  cleaned-up version of the best evolved machine and a tailored machine that is
  an even better defense.
- [Tools for evolving machines](evolve/) using genetic programming.
- [Highlights of the
  project](https://lists.torproject.org/pipermail/tor-project/2020-November/003018.html)
  were shared as part of the November 2020 Tor DEMO Day.

The work in the project is documented in a pre-print paper on arxiv. Results
from the pre-print will be incorporated into a later submission to an academic
conference together with new unpublished results (other project).

## Acknowledgements
This project is made possible thanks to a generous grant from the [NGI Zero
PET](https://nlnet.nl/PET/) project, that in turn is made possible with
financial support from the [European Commission's](https://ec.europa.eu/) [Next
Generation Internet](https://www.ngi.eu/) programme, under the aegis of [DG
Communications Networks, Content and
Technology](https://ec.europa.eu/info/departments/communications-networks-content-and-technology_en).
Co-financing (for administrative costs and equipment) is provided by [Computer
Science](https://www.kau.se/en/cs) at [Karlstad
University](https://www.kau.se/en). [The Swedish Internet
Foundation](https://internetstiftelsen.se/en/) also funded part of the work by
enabling me to spend extra time on the simulator (synergies with another
project) and tweaking the Interspace machine.