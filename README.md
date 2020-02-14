# Padding Machines for Tor
This is the repository for the [NGI Zero PET](https://nlnet.nl/PET/) project
"Padding Machines by Tor". The goal of the project is to create one or more
padding machines for Tor's new [circuit padding framework](https://blog.torproject.org/new-release-tor-0405).
The padding machines should defend against 
[Website Fingerprinting (WF) attacks](https://blog.torproject.org/critique-website-traffic-fingerprinting-attacks).

## Project plan
The project has three phases:

1. Figure out the details of circuit padding as implemented in Tor and setup
   necessary infrastructure for collecting WF datasets with and without padding
   machines.
2. Iteratively, design-implement-evaluate padding machines in the search of
   effective and/or efficient designs. Machines are _effective_ if they can
   provide adequate defense against state-of-the-art WF attacks. Machines are
   _efficient_ if their induced bandwidth and/or latency overheads are low.
3.  Document, polish the implementation of, and eventually publish the design of
    the most promising padding machines.

Most development will take place here in the open, sharing results early to help
other researchers in the area. Daily trial-and-error work we spare you from
though.

## Project status
Bi-monthly updates are provided in
[statusreports/](statusreports/)
. 

Phase 1 is completed. Fun results:
- [Developer notes on the circuit padding framework](notes/circuit-padding-framework.md).
- [Building a padding machine from scratch](notes/machine-from-scratch.md).
- [Implemented an APE-like padding machine](https://github.com/pylls/tor/tree/circuit-padding-ape-machine). 
- Tor trac tickets: [#31098](https://trac.torproject.org/projects/tor/ticket/31098),
  [#31111](https://trac.torproject.org/projects/tor/ticket/31111),
  [#31112](https://trac.torproject.org/projects/tor/ticket/31112),
  [#31113](https://trac.torproject.org/projects/tor/ticket/31113).

Currently working on phase 2, expecting to wrap up during spring 2020. Fun
results:
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

## Acknowledgements
This project is made possible thanks to a generous grant from the [NGI Zero PET](https://nlnet.nl/PET/) 
project, that in turn is made possible with financial support from the 
[European Commission's](https://ec.europa.eu/) [Next Generation Internet](https://www.ngi.eu/) 
programme, under the aegis of 
[DG Communications Networks, Content and Technology](https://ec.europa.eu/info/departments/communications-networks-content-and-technology_en).
Co-financing (for administrative costs and equipment) is provided by 
[Computer Science](https://www.kau.se/en/cs) at [Karlstad University](https://www.kau.se/en). 