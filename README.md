# Padding Machines for Tor
This is the repository for the [NGI Zero PET](https://nlnet.nl/PET/) project
"Padding Machines by Tor". The goal of the project is to create one or more
padding machines for Tor's new [circuit padding framework](https://blog.torproject.org/new-release-tor-0405).
The padding machines should defend against 
[Website Fingerprinting (WF) attacks](https://blog.torproject.org/critique-website-traffic-fingerprinting-attacks).

## Project plan
The project has three phases:

1. Figure out the details of circuit padding as implemented in Tor and setup
   necessarry infrastructure for collecting WF datasets with and without padding
   machines.
2. Iteratively, design-implement-evaluate padding machines in the search of
   effective and/or efficient designs. Machines are _effective_ if they can
   provide adequate defense against state-of-the-art WF attacks. Machines are
   _efficient_ if their induced bandwidth and/or latency overheads are low.
3.  Document, polish the implementation of, and eventually publish the design of
    the most promising padding machines.

All development will take place here in the open. The goal is to finish the
first phase in time for [PETS 2019](https://www.petsymposium.org/2019/) in
Stockholm July 16-20, to interact with other researchers.

## Acknowledgements
This project is made possible thanks to a generous grant from the [NGI Zero PET](https://nlnet.nl/PET/) 
project, that in turn is made possible with financial support from the 
[European Commission's](https://ec.europa.eu/) [Next Generation Internet](https://www.ngi.eu/) 
programme, under the aegis of 
[DG Communications Networks, Content and Technology](https://ec.europa.eu/info/departments/communications-networks-content-and-technology_en).
Co-financing (for administrative costs and equipment) is provided by 
[Computer Science](https://www.kau.se/en/cs) at [Karlstad University](https://www.kau.se/en). 