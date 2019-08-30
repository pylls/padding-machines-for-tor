# A Padding Machine from Scratch

This document describes the process of building a "padding machine" in tor's new
circuit padding framework. Notes were taken as part of porting APE from basket2
to the circuit padding framework. The goal is just to document the process and
provide useful pointers along the way, not create a useful machine. 

The plan is to:
1. clone and compile tor
2. use newly built tor in TB and at small middle relay we run
3. add an empty APE machine in the framework, make it run locally in TB without
   crashing
4. add a log message during padding machine negotiation and observe it in TB and
   at the relay
5. port APE without thinking much about parameters
