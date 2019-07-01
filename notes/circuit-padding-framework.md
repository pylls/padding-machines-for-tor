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

Placeholder
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