During September and October:
- Finished phase 1 of the project with the completion of a [documented padding
  machine from
  scratch](https://github.com/pylls/padding-machines-for-tor/blob/master/notes/machine-from-scratch.md).
  The guide will [hopefully be included in the Tor
  documentation](https://github.com/mikeperry-tor/tor/blob/circuitpadding-dev-doc/doc/HACKING/CircuitPaddingQuickStart.md)
  in the future.
- Sketched on a [list of websites for one form of evaluating
  machines](https://github.com/pylls/padding-machines-for-tor/tree/master/collect-traces/exp/lists).
- Spent a lot of time thinking about different forms of evaluating machines
  beyond what was originally planned for the project. Decided to "bite the
  bullet" and contribute to building a circuitpadding simulator in Tor's unit
  testing framework. Spent resources from this project and another grant from
  the [Swedish Internet Foundation](https://internetstiftelsen.se/en/). The idea
  from the simulator comes from
  [#31788](https://trac.torproject.org/projects/tor/ticket/31788). Because of
  the joint funding and beyond scope for this project alone, I put the simulator
  in another repository: https://github.com/pylls/circpad-sim . In that repo:
    - Patches to tor for orchestrating circuitpadding traces from the circuitpadding framework, enabling collection of traces using Tor Browser from its logs.
    - A python script to convert from Tor logs to a trace format.
    - A python script for simulating a trace of events at a middle relay.
    - A python script for computing bandwidth overheads caused by padding.
    - A sketch of a python script for converting from a trace to typical formats used for website fingerprinting.
    - An alpha-grade simulator as a test in Tor's circuit padding framework.
- Started the discussion on upstreaming the simulator and getting feedback from Tor developers (see [#31788](https://trac.torproject.org/projects/tor/ticket/31788) and https://github.com/mikeperry-tor/tor/commits/circpad-sim-squashed).
- The decision to write a simulator means that we're behind the original schedule a bit, hoping to wrap up phase 2 somewhere around February 2020. 