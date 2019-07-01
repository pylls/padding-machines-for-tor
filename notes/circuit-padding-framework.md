# Tor's Circuit Padding Framework 
Notes taken when reading through Tor's circuit padding framework, starting from
tag `tor-0.4.1.3-alpha` at https://gitweb.torproject.org/tor.git/.

Important files added largely for the circuit padding framework:
- `src/core/or/circuitpadding.{h,c}`, 1916 lines of code and 1420 lines of comments.
- `src/core/or/circuitpadding_machines.{h,c}`, 185 lines of code and 232 lines of comments.
- `src/lib/math/prob_distr.{h,c}`, 658 lines of code and 1099 lines of comments. 

That's a significant amount of complexity added to the core of tor. In
comparison, the `src/core/crypto` directory consists of 1389 lines of code (sans
libraries for primitives). 

## What is a "Machine"?
Before we can define a machine we need to define some of the context in which
the machine operates. The machine is part of the _circuit_ padding framework in
Tor, and a circuit is the core construct in Tor for building connections between
relays. Circuits have different _purposes_ depending on on their intended use,
e.g., as part of onion services or for general purpose use. Constants for the
different purposes are found in `src/core/or/circuitlist.h`. TCP streams are
multiplexed inside a circuit as part of a _stream_, and typical operation of tor
involves the frequent connection of both circuits and streams, just like regular
TCP streams. 

So what is a machine? A machine is a state machine that exists _per circuit_,
hence being a ciruit padding framework. The goal of a machine is to inject (pad)
dummy traffic with different goals in mind, such as hiding from a passive
network adversary that the purpose of a circuit is for the purpose of use with
onion services.

A machine is only created on a circuit if specific _conditions_ are met, as shown below:

```c
typedef struct circpad_machine_conditions_t {
  /** Only apply the machine *if* the circuit has at least this many hops */
  unsigned min_hops : 3;

  /** Only apply the machine *if* vanguards are enabled */
  unsigned requires_vanguards : 1;

  /**
   * This machine is ok to use if reduced padding is set in consensus
   * or torrc. This machine will still be applied even if reduced padding
   * is not set; this flag only acts to exclude machines that don't have
   * it set when reduced padding is requested. Therefore, reduced padding
   * machines should appear at the lowest priority in the padding machine
   * lists (aka first in the list), so that non-reduced padding machines
   * for the same purpose are given a chance to apply when reduced padding
   * is not requested. */
  unsigned reduced_padding_ok : 1;

  /** Only apply the machine *if* the circuit's state matches any of
   *  the bits set in this bitmask. */
  circpad_circuit_state_t state_mask;

  /** Only apply a machine *if* the circuit's purpose matches one
   *  of the bits set in this bitmask */
  circpad_purpose_mask_t purpose_mask;

} circpad_machine_conditions_t;
```

Here, `purpose_mask` encodes the purpose of the ciruit discussed earlier, and
`state_mask` covers the state of the circuit itself:

```c
typedef enum {
  /* Only apply machine if the circuit is still building */
  CIRCPAD_CIRC_BUILDING = 1<<0,
  /* Only apply machine if the circuit is open */
  CIRCPAD_CIRC_OPENED = 1<<1,
  /* Only apply machine if the circuit has no attached streams */
  CIRCPAD_CIRC_NO_STREAMS = 1<<2,
  /* Only apply machine if the circuit has attached streams */
  CIRCPAD_CIRC_STREAMS = 1<<3,
  /* Only apply machine if the circuit still allows RELAY_EARLY cells */
  CIRCPAD_CIRC_HAS_RELAY_EARLY = 1<<4,
  /* Only apply machine if the circuit has depleted its RELAY_EARLY cells
   * allowance. */
  CIRCPAD_CIRC_HAS_NO_RELAY_EARLY = 1<<5
} circpad_circuit_state_t;
```

...

To sample delays and/or number of padding cells to send, machines can use:
- histograms with removal
- distributions

...
State split into immutable and mutable parts: mutable per circuit, immutable
once per machine. Immutable is `circpad_state_t`, mutable
`circpad_machine_runtime_t`.

## Current Machines
In `circuitpadding_machines.c` we find two machines that adds padding with the
goal of hiding IP and RP circuits, as used for onion services: 

- The IP hiding machine injects two cells on IP circuit creation on the client
  side, sending them to middle relay. After the the middle relay gets any
  non-padding cells to send to the client, it in turn uniformly random every
  [1,10] ms sends a padding cell to the client, up to a total of uniformly
  random [7,10] padding cells have been sent. 
- The RP hiding machine ...

### The IP Circuit Hiding Machine
TODO: go over in detail, break down code

### The RP Circuit Hiding Machine
TODO