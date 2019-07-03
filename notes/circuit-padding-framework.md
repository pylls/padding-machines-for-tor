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

## Background
We briefly cover necessary background here. 

### State Machines
A state machine consists of _states_ and _transitions_ between those states.
Transitions occur due to _events_ or when conditions are met. The [Wikipedia
article](https://en.wikipedia.org/wiki/Finite-state_machine#Concepts_and_terminology)
gives more details.

### Circuits in Tor
A circuit is the core construct in Tor for building connections between relays.
Circuits have different _purposes_ depending on on their intended use, e.g., as
part of onion services or for general purpose use. Constants for the different
purposes are found in `src/core/or/circuitlist.h`, in total 24 different valid
purposes, mostly dealing with client-server roles related to onion services. TCP
streams are multiplexed inside a circuit as part of a _stream_, and typical
operation of tor involves the frequent connection of both circuits and streams,
just like regular TCP streams. 

There are two types of circuits at a relay: either an origin circuit or an or
circuit. An origin circuit is created at the relay itself, while a or circuit is
a circuit that the relay acts as an onion router for. 

## What is a "Machine"?
A machine is a state machine that exists _per circuit_, hence a "circuit padding
framework". A padding machine injects fake (padding) cells with different
goals in mind, such as hiding from a passive network adversary the purpose of a
circuit (e.g., distinguishing between "regular" circuits and onion services). 

`circuitpadding.h` reads bottom-up, so to answer what a machine is we go more
top-down here. There a three primary structs for a machine:
- `circpad_machine_spec_t` The global specification of a machine, immutable.
- `circpad_state_t` Global immutable description of a state and its possible
  transitions as part of a machine.
- `circpad_machine_runtime_t` Per circuit description of the state machine with
  _mutable_ data, kept as small as possible for sake of minimizing memory usage.

So a machine consists of one `circpad_machine_spec_t` that specifies a number of
states and their transitions (`circpad_state_t`), all immutable. For each
circuit, one `circpad_machine_runtime_t` consists mutable data, such as the
current state of the machine on the circuit. 

### Details on `circpad_machine_spec_t`
Below is the full struct:

```c
typedef struct circpad_machine_spec_t {
  /* Just a user-friendly machine name for logs */
  const char *name;

  /** Global machine number */
  circpad_machine_num_t machine_num;

  /** Which machine index slot should this machine go into in
   *  the array on the circuit_t */
  unsigned machine_index : 1;

  /** Send a padding negotiate to shut down machine at end state? */
  unsigned should_negotiate_end : 1;

  // These next three fields are origin machine-only...
  /** Origin side or relay side */
  unsigned is_origin_side : 1;

  /** Which hop in the circuit should we send padding to/from?
   *  1-indexed (ie: hop #1 is guard, #2 middle, #3 exit). */
  unsigned target_hopnum : 3;

  /** If this flag is enabled, don't close circuits that use this machine even
   *  if another part of Tor wants to close this circuit.
   *
   *  If this flag is set, the circuitpadding subsystem will close circuits the
   *  moment the machine transitions to the END state, and only if the circuit
   *  has already been asked to be closed by another part of Tor.
   *
   *  Circuits that should have been closed but were kept open by a padding
   *  machine are re-purposed to CIRCUIT_PURPOSE_C_CIRCUIT_PADDING, hence
   *  machines should take that purpose into account if they are filtering
   *  circuits by purpose. */
  unsigned manage_circ_lifetime : 1;

  /** This machine only kills fascists if the following conditions are met. */
  circpad_machine_conditions_t conditions;

  /** How many padding cells can be sent before we apply overhead limits?
   * XXX: Note that we can only allow up to 64k of padding cells on an
   * otherwise quiet circuit. Is this enough? It's 33MB. */
  uint16_t allowed_padding_count;

  /** Padding percent cap: Stop padding if we exceed this percent overhead.
   * 0 means no limit. Overhead is defined as percent of total traffic, so
   * that we can use 0..100 here. This is the same definition as used in
   * Prop#265. */
  uint8_t max_padding_percent;

  /** State array: indexed by circpad_statenum_t */
  circpad_state_t *states;

  /**
   * Number of states this machine has (ie: length of the states array).
   * XXX: This field is not needed other than for safety. */
  circpad_statenum_t num_states;
} circpad_machine_spec_t;
```
Most fields are self explanatory (but a lot to consider) and we see that care
has been taken to be able to prevent machines from flooding the network with
padding. `machine_index` is as simple as it sounds, currently tor has a
hardcoded array of size `CIRCPAD_MAX_MACHINES`, set to 2. Adding a new machine
will require changes to this. In the future, the plan is to support having
machines defined in torrc and from the consensus, but currently code is missing
for this. 

For understanding the framework, the most important fields are `conditions` and
`states`. Note that `states` is an array of states with a maximum size of
`CIRCPAD_STATENUM_MAX`, currently `UINT16_MAX`. We cover how a state is defined
in the next section, but first, we look closer here at `conditions`. Simply put,
a machine is only active on a circuit if specific _conditions_ are met, as shown
below:

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

The purpose of the circuit is encoded as a `purpose_mask` (we covered purposes
briefly in the background) and `state_mask` covers the state of the circuit:

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
This allows us quite some control over when a machine should be active on a
circuit, important both for creating machines with a specific goal and
performance.

### Details on `circpad_state_t`
On a high-level, each state consists of:
- an IAT histogram or probability distribution
- a length (in terms of number of sent (padding) cells) probability distribution
  with min-max parameters
- an array of _events_ that cause a _transition_ from the current state to
  the same or another state.
- unsigned use_rtt_estimate : 1;
((- We can transition due to events, can we also transition for other reasons?))

The IAT histogram/distribution is used by `circpad_machine_sample_delay()` to
sample a delay (in microseconds) for scheduling a padding cell. There are a wide
range of considerations for the choice of histogram or probability destribution,
far beyond the scope of these notes. Below we provide further details on
possible options supported by the framework. 

The probability distribution for sampling a length: the number of sent (total or
padding) cells while in this state, used by `circpad_choose_state_length()`.
Note: does _not_ resample length when you transition to the same state, feature
or bug?

`circpad_machine_spec_transition()` for transitions. 

#### Histograms
A [histogram](https://en.wikipedia.org/wiki/Histogram) is an estimation of a
probability distribution, so if the padding framework supports directly using
several probability distributions, why add support for histograms? The answer is
due to the idea of [adaptive
padding](https://www.cs.utexas.edu/~shmat/shmat_esorics06.pdf) as part of the
paper [Toward an Efficient Website Fingerprinting
Defense](https://arxiv.org/pdf/1512.00524.pdf) by Juarez _et al._. The idea is
to adapt _when_ to inject padding such that the resulting inter-arrival time
(IAT) of _all_ packets (cells) are shaped according to two histograms: one for
for IAT within _bursts_ of traffic and one for IAT _between_ bursts. 

With the above in mind, we can first see the histogram definition as part of the
immutable `circpad_state_t`:

```c
/**
   * If a histogram is used for this state, this specifies the number of bins
   * of this histogram. Histograms must have at least 2 bins.
   *
   * In particular, the following histogram:
   *
   * Tokens
   *         +
   *      10 |    +----+
   *       9 |    |    |           +---------+
   *       8 |    |    |           |         |
   *       7 |    |    |     +-----+         |
   *       6 +----+ Bin+-----+     |         +---------------+
   *       5 |    | #1 |     |     |         |               |
   *         | Bin|    | Bin | Bin |  Bin #4 |    Bin #5     |
   *         | #0 |    | #2  | #3  |         | (infinity bin)|
   *         |    |    |     |     |         |               |
   *         |    |    |     |     |         |               |
   *       0 +----+----+-----+-----+---------+---------------+
   *         0   100  200   350   500      1000              ∞  microseconds
   *
   * would be specified the following way:
   *    histogram_len = 6;
   *    histogram[] =        {   6,  10,   6,  7,    9,     6 }
   *    histogram_edges[] =  { 0, 100, 200, 350, 500, 1000 }
   *
   * The final bin is called the "infinity bin" and if it's chosen we don't
   * schedule any padding. The infinity bin is strange because its lower edge
   * is the max value of possible non-infinite delay allowed by this histogram,
   * and its upper edge is CIRCPAD_DELAY_INFINITE. You can tell if the infinity
   * bin is chosen by inspecting its bin index or inspecting its upper edge.
   *
   * If a delay probability distribution is used for this state, this is set
   * to 0. */
  circpad_hist_index_t histogram_len;
  /** The histogram itself: an array of uint16s of tokens, whose
   *  widths are exponentially spaced, in microseconds.
   *
   *  This array must have histogram_len elements that are strictly
   *  monotonically increasing. */
  circpad_hist_token_t histogram[CIRCPAD_MAX_HISTOGRAM_LEN];
  /* The histogram bin edges in usec.
   *
   * Each element of this array specifies the left edge of the corresponding
   * bin. The rightmost edge is always infinity and is not specified in this
   * array.
   *
   * This array must have histogram_len elements. */
  circpad_delay_t histogram_edges[CIRCPAD_MAX_HISTOGRAM_LEN+1];
  /** Total number of tokens in this histogram. This is a constant and is *not*
   *  decremented every time we spend a token. It's used for initializing and
   *  refilling the histogram. */
  uint32_t histogram_total_tokens;

  ...

    /** This specifies the token removal strategy to use upon padding and
   *  non-padding activity. */
  circpad_removal_t token_removal;
```

The token removal strategy is the key part of the use of histograms over
probability distributions: 

```c
/**
 * Token removal strategy options.
 *
 * The WTF-PAD histograms are meant to specify a target distribution to shape
 * traffic towards. This is accomplished by removing tokens from the histogram
 * when either padding or non-padding cells are sent.
 *
 * When we see a non-padding cell at a particular time since the last cell, you
 * remove a token from the corresponding delay bin. These flags specify
 * which bin to choose if that bin is already empty.
 */
typedef enum {
  /** Don't remove any tokens */
  CIRCPAD_TOKEN_REMOVAL_NONE = 0,
  /**
   * Remove from the first non-zero higher bin index when current is zero.
   * This is the recommended strategy from the Adaptive Padding paper. */
  CIRCPAD_TOKEN_REMOVAL_HIGHER = 1,
  /** Remove from the first non-zero lower bin index when current is empty. */
  CIRCPAD_TOKEN_REMOVAL_LOWER = 2,
  /** Remove from the closest non-zero bin index when current is empty. */
  CIRCPAD_TOKEN_REMOVAL_CLOSEST = 3,
  /** Remove from the closest bin by time value (since bins are
   *  exponentially spaced). */
  CIRCPAD_TOKEN_REMOVAL_CLOSEST_USEC = 4,
  /** Only remove from the exact bin corresponding to this delay. If
   *  the bin is 0, simply do nothing. Don't pick another bin. */
  CIRCPAD_TOKEN_REMOVAL_EXACT = 5
} circpad_removal_t;
```

#### Probability Distributions
There are support for the following distributions:
```c
/**
 * Distribution types supported by circpad_distribution_sample().
 *
 * These can be used instead of histograms for the inter-packet
 * timing distribution, or to specify a distribution on the number
 * of cells that can be sent while in a specific state of the state
 * machine.
 *
 * Each distribution takes up to two parameters which are described below. */
typedef enum {
  /* No probability distribution is used */
  CIRCPAD_DIST_NONE = 0,
  /* Uniform distribution: param1 is lower bound and param2 is upper bound */
  CIRCPAD_DIST_UNIFORM = 1,
  /* Logistic distribution: param1 is Mu, param2 is sigma. */
  CIRCPAD_DIST_LOGISTIC = 2,
  /* Log-logistic distribution: param1 is Alpha, param2 is 1.0/Beta */
  CIRCPAD_DIST_LOG_LOGISTIC = 3,
  /* Geometric distribution: param1 is 'p' (success probability) */
  CIRCPAD_DIST_GEOMETRIC = 4,
  /* Weibull distribution: param1 is k, param2 is Lambda */
  CIRCPAD_DIST_WEIBULL = 5,
  /* Generalized Pareto distribution: param1 is sigma, param2 is xi */
  CIRCPAD_DIST_PARETO = 6
} circpad_distribution_type_t;

/**
 * Distribution information.
 *
 * This type specifies a specific distribution above, as well as
 * up to two parameters for that distribution. The specific
 * per-distribution meaning of these parameters is specified
 * in circpad_distribution_sample().
 */
typedef struct circpad_distribution_t {
  circpad_distribution_type_t type;
  double param1;
  double param2;
} circpad_distribution_t;
```

The distribution for IAT is selected for a machine as part of the immutable
`circpad_state_t`:

```c
  /**
   * Represents a delay probability distribution (aka IAT distribution). It's a
   * parametrized way of encoding inter-packet delay information in
   * microseconds. It can be used instead of histograms.
   *
   * If it is used, token_removal below must be set to
   * CIRCPAD_TOKEN_REMOVAL_NONE.
   *
   * Start_usec, range_sec, and rtt_estimates are still applied to the
   * results of sampling from this distribution (range_sec is used as a max).
   */
  circpad_distribution_t iat_dist;
  /*  If a delay probability distribution is used, this is used as the max
   *  value we can sample from the distribution. However, RTT measurements and
   *  dist_added_shift gets applied on top of this value to derive the final
   *  padding delay. */
  circpad_delay_t dist_max_sample_usec;
  /*  If a delay probability distribution is used and this is set, we will add
   *  this value on top of the value sampled from the IAT distribution to
   *  derive the final padding delay (We also add the RTT measurement if it's
   *  enabled.). */
  circpad_delay_t dist_added_shift_usec;
```

### Details on `circpad_machine_runtime_t`


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