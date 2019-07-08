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
operation of tor with Tor Browser involves the frequent creation of both
circuits and streams, just like regular TCP streams. 

There are two types of circuits in tor: either an origin circuit or an _or_
circuit. An origin circuit is created at the tor instance itself, while a _or_
circuit is a circuit that the tor instance acts as an onion router for. 

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
- `circpad_machine_runtime_t` Per _circuit_ description of a state machine's
  current state with _mutable_ data, kept as small as possible for sake of
  minimizing memory usage.

So a machine consists of one `circpad_machine_spec_t` that specifies a number of
states and their transitions (`circpad_state_t`), all immutable. For each
circuit, one `circpad_machine_runtime_t` consists of mutable data, such as the
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
may require changes. This limit is for the number of active machines on a
circuit at the same time. In the future, the plan is to support having machines
defined in torrc and from the consensus, but currently code is missing for this.
Having explicit array locations for machines with `machine_index` ensures that
the order machines operate in the framework are deterministic. 

Running padding machines between a relay and a client involves
_negotiation_ to agree to run the machine, and for this `machine_num` uniquely
identifies a machine. 

For understanding the framework, the most important fields are `conditions` and
`states`. Note that `states` is an array of states with a maximum size of
`CIRCPAD_STATENUM_MAX`, currently `UINT16_MAX`, providing more than enough room
for states (for comparison, WTF-PAD has three states). We cover how a state is
defined in the next section, but first, we look closer here at `conditions`.
Simply put, a machine is only active on a circuit if specific _conditions_ are
met, as shown below:

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
- an IAT histogram or probability distribution.
- a flag to use a RTT estimate for IAT.
- a length (in terms of number of sent (padding) cells) probability distribution
  with min-max parameters.
- an array of _events_ that cause a _transition_ from the current state to
  the same or another state.

The IAT histogram/distribution is used by `circpad_machine_sample_delay()` to
sample a delay (in microseconds) for scheduling a single padding cell. There are
a wide range of considerations for the choice of histogram or probability
distribution, far beyond the scope of these notes. For reference, tuning the
histogram is _the_ hard problem for the WTF-PAD defense that inspired the design
of the circuit padding framework and to the best of my knowledge no good
approach exists. Further details on histograms and probability distributions are
below. 

When an IAT is sampled from the histogram/distribution, the RTT flag decides if
an RTT estimate should be added to the sampled delay. The RTT estimate estimates
the delay from the relay to the "exit/website" (note: unsure what this means).
Currently only supported from relay, not the tor client used by Tor Browser. The
idea behind the RTT is to better be able to create realistic padding traffic
that appears (in terms of latency) like traffic from the real exit/website. 

The probability distribution for sampling a length: the maximum number of sent
(total or padding) cells while in this state, used by
`circpad_choose_state_length()`. [Note: does _not_ resample length when you
transition to the same state, feature or bug? Appears to be feature, since
internal states like `CIRCPAD_EVENT_LENGTH_COUNT` also cause a transition.] When
the length is reached, no more padding will be sent, and an event will be
triggered that may trigger a transition.

The array of events that cause a transition are defined as follows:
```c
  /**
   * This is an array that specifies the next state to transition to upon
   * receipt an event matching the indicated array index.
   *
   * This aborts our scheduled packet and switches to the state
   * corresponding to the index of the array. Tokens are filled upon
   * this transition.
   *
   * States are allowed to transition to themselves, which means re-schedule
   * a new padding timer. They are also allowed to temporarily "transition"
   * to the "IGNORE" and "CANCEL" pseudo-states. See #defines below
   * for details on state behavior and meaning.
   */
  circpad_statenum_t next_state[CIRCPAD_NUM_EVENTS];
```

Here, `circpad_statenum_t` is the index of the states array `*states` in
`circpad_machine_spec_t` for the machine. To tie it together, consider the
possible _events_ that can cause a transition:

```c
/**
 * These constants specify the types of events that can cause
 * transitions between state machine states.
 *
 * Note that SENT and RECV are relative to this endpoint. For
 * relays, SENT means packets destined towards the client and
 * RECV means packets destined towards the relay. On the client,
 * SENT means packets destined towards the relay, where as RECV
 * means packets destined towards the client.
 */
typedef enum {
  /* A non-padding cell was received. */
  CIRCPAD_EVENT_NONPADDING_RECV = 0,
  /* A non-padding cell was sent. */
  CIRCPAD_EVENT_NONPADDING_SENT = 1,
  /* A padding cell (RELAY_COMMAND_DROP) was sent. */
  CIRCPAD_EVENT_PADDING_SENT = 2,
  /* A padding cell was received. */
  CIRCPAD_EVENT_PADDING_RECV = 3,
  /* We tried to schedule padding but we ended up picking the infinity bin
   * which means that padding was delayed infinitely */
  CIRCPAD_EVENT_INFINITY = 4,
  /* All histogram bins are empty (we are out of tokens) */
  CIRCPAD_EVENT_BINS_EMPTY = 5,
  /* just a counter of the events above */
  CIRCPAD_EVENT_LENGTH_COUNT = 6
} circpad_event_t;
#define CIRCPAD_NUM_EVENTS ((int)CIRCPAD_EVENT_LENGTH_COUNT+1)
```

Here, the events are between a client (origin) and a relay. At origin, the
events will trigger on any (non)padding to/from the network on the circuit,
while at the relay (non)padding cells are to/from origin on the circuit.

The function `circpad_machine_spec_transition()` is used for transitions, and
there are exactly seven calls in tor's source to cause a transition, one for
each even above. Note that the comment for `CIRCPAD_EVENT_LENGTH_COUNT` is
wrong, the event is triggered when the state has used up its cell count (the
sampled length in state as described above). [TODO: write pull request.]

Finally, it is worth to note is that there are some hardcoded states that are
used internally in the framework:
```c
/**
 * End is a pseudo-state that causes the machine to go completely
 * idle, and optionally get torn down (depending on the
 * value of circpad_machine_spec_t.should_negotiate_end)
 *
 * End MUST NOT occupy a slot in the machine state array.
 */
#define  CIRCPAD_STATE_END         CIRCPAD_STATENUM_MAX

/**
 * "Ignore" is a pseudo-state that means "do not react to this
 * event".
 *
 * "Ignore" MUST NOT occupy a slot in the machine state array.
 */
#define  CIRCPAD_STATE_IGNORE         (CIRCPAD_STATENUM_MAX-1)

/**
 * "Cancel" is a pseudo-state that means "cancel pending timers,
 * but remain in your current state".
 *
 * Cancel MUST NOT occupy a slot in the machine state array.
 */
#define  CIRCPAD_STATE_CANCEL         (CIRCPAD_STATENUM_MAX-2)

/**
 * Since we have 3 pseudo-states, the max state array length is
 * up to one less than cancel's statenum.
 */
#define CIRCPAD_MAX_MACHINE_STATES  (CIRCPAD_STATE_CANCEL-1)
```
When the states of a machine is initalized using
`circpad_machine_states_init()`, for every state and every possible event that
can cause a transition, `CIRCPAD_STATE_IGNORE` is set as the default state,
i.e., do nothing. 

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
The runtime struct contains a number of variables for internal bookkeeping
related to timers, the current state, histogram (if used), amount of padding
sent, etc. This is all transparent from what I can tell right now when creating
machines. Worth to note when creating custom machines is that the struct ends
with the following:

```c
typedef struct circpad_machine_runtime_t {
  ....
/** Max number of padding machines on each circuit. If changed,
 * also ensure the machine_index bitwith supports the new size. */
#define CIRCPAD_MAX_MACHINES    (2)
  /** Which padding machine index was this for.
   * (make sure changes to the bitwidth can support the
   * CIRCPAD_MAX_MACHINES define). */
  unsigned machine_index : 1;
} circpad_machine_runtime_t;
```

## How Machines are Negotiated
The padding negotiation works as follows. At origin,
`circpad_add_matching_machines()` is called every time a circuit changes in one of the following ways:
- a new hop to the circuit, 
- the circuit is built, 
- the purpose of the circuit changed, 
- the circuit is out of RELAY_EARLY cells,
- streams are attached, and 
- streams are detached.

 For each possible machine that has a free machine index at the circuit and
 where the conditions are fulfilled for it to be run, negotiation between an
 origin client and a relay flows as follows:
1. the origin uses `circpad_negotiate_padding()` to send a request to use the
   machine (by global `machine_num`), 
2. the relay parses the request to start padding with
   `circpad_handle_padding_negotiate()`,
3. creates a response with `circpad_padding_negotiated()`, and 
4. finally the client parses the response with
    `circpad_handle_padding_negotiated()`. 

The negotiation can fail due to lack of support for padding in general or the
lack of support for the requested machine (e.g., due to consensus drift once
support is in place).

## Misc notes
I found the below defines confusing at first, they're only used for a test right
now, and would make sense for an explicit WTF PAD machine as part of
`src/core/or/circuitpadding_machines.{h,c}`, not the framework itself.

```c
/**
 * The start state for this machine.
 *
 * In the original WTF-PAD, this is only used for transition to/from
 * the burst state. All other fields are not used. But to simplify the
 * code we've made it a first-class state. This has no performance
 * consequences, but may make naive serialization of the state machine
 * large, if we're not careful about how we represent empty fields.
 */
#define  CIRCPAD_STATE_START       0

/**
 * The burst state for this machine.
 *
 * In the original Adaptive Padding algorithm and in WTF-PAD
 * (https://www.freehaven.net/anonbib/cache/ShWa-Timing06.pdf and
 * https://www.cs.kau.se/pulls/hot/thebasketcase-wtfpad/), the burst
 * state serves to detect bursts in traffic. This is done by using longer
 * delays in its histogram, which represent the expected delays between
 * bursts of packets in the target stream. If this delay expires without a
 * real packet being sent, the burst state sends a padding packet and then
 * immediately transitions to the gap state, which is used to generate
 * a synthetic padding packet train. In this implementation, this transition
 * needs to be explicitly specified in the burst state's transition events.
 *
 * Because of this flexibility, other padding mechanisms can transition
 * between these two states arbitrarily, to encode other dynamics of
 * target traffic.
 */
#define  CIRCPAD_STATE_BURST       1

/**
 * The gap state for this machine.
 *
 * In the original Adaptive Padding algorithm and in WTF-PAD, the gap
 * state serves to simulate an artificial packet train composed of padding
 * packets. It does this by specifying much lower inter-packet delays than
 * the burst state, and transitioning back to itself after padding is sent
 * if these timers expire before real traffic is sent. If real traffic is
 * sent, it transitions back to the burst state.
 *
 * Again, in this implementation, these transitions must be specified
 * explicitly, and other transitions are also permitted.
 */
#define  CIRCPAD_STATE_GAP         2
```

```c
STATIC void
circpad_add_matching_machines(origin_circuit_t *on_circ,
                              smartlist_t *machines_sl)
{
  .....
        /* Set up the machine immediately so that the slot is occupied.
         * We will tear it down on error return, or if there is an error
         * response from the relay. */
        circpad_setup_machine_on_circ(circ, machine);
        if (circpad_negotiate_padding(on_circ, machine->machine_num,
                                  machine->target_hopnum,
                                  CIRCPAD_COMMAND_START) < 0) {
          log_info(LD_CIRC, "Padding not negotiated. Cleaning machine");
          circpad_circuit_machineinfo_free_idx(circ, i);
          circ->padding_machine[i] = NULL;
          on_circ->padding_negotiation_failed = 1;
        } else {
          /* Success. Don't try any more machines */
          return;
        }
      }
    } SMARTLIST_FOREACH_END(machine);
  } FOR_EACH_CIRCUIT_MACHINE_END;
}
```
The return above is a bug? Can only add one machine now, but there might be
`CIRCPAD_MAX_MACHINES`of them. Should be a break to try the next machine index.
PR sent: https://github.com/torproject/tor/pull/1168.

```c
  log_fn(LOG_INFO,LD_CIRC,"\tPadding in %u usec", in_usec);

  // Don't schedule if we have infinite delay.
  if (in_usec == CIRCPAD_DELAY_INFINITE) {
    return circpad_internal_event_infinity(mi);
  }
```
TODO: Move the log to after the check.

There are several references in comments on `monotime_absolute_usec()` being
unpredictably expensive and avoided. This is only used for histograms with token
removal and RTT estimates.

There appears to be a lack of logic for relay-side machines and validating that
they are in fact intended to be running listed machines. This worries me from a
DoS perspective and exit relays: one negotiation packet could cause so much work
if the machine does not take this into account. 

Throughout the code, padding cell = padding packet. Is this really the case?
Won't it just send one cell, where we have room for at least 2 cells in a
typical packet of MTU around 1500ish bytes?

## Current Machines
In `circuitpadding_machines.{h.c}` we find two machines that adds padding with
the goal of hiding IP and RP circuits (making them look like general circuits),
as used for onion services. In gist: 

- The IP hiding machine injects two cells on IP circuit creation on the client
  side (by negotiating padding), sending them to middle relay. After the the
  middle relay gets any non-padding cells to send to the client, it in turn
  uniformly random every [1,10] ms sends a padding cell to the client, up to a
  total of uniformly random [7,10] padding cells have been sent. 
- The RP hiding machine injects one cell (in addition to two negotiation cells)
  during the RP circuit creation on the client side, sending it to the middle
  relay within [0,1] ms. The machine does exactly the same on the relay side. 

### The IP Circuit Hiding Machine
Some minor observations below. 

```c
 /* The client side should never send padding, so it does not need
   * to specify token removal, or a histogram definition or state lengths.
   * That is all controlled by the middle node. */
```
Above is true, if no histogram or prob dist is defined, then eventually in
`circpad_machine_sample_delay()` we end up sampling `CIRCPAD_DELAY_INFINITE` due
to:
```c
  /* If we are out of tokens, don't schedule padding. */
  if (!histogram_total_tokens) {
    return CIRCPAD_DELAY_INFINITE;
  }
```
Not a clean solution.

```c
circpad_machine_relay_hide_intro_circuits(smartlist_t *machines_sl)
{
  ...
  relay_machine->conditions.state_mask = CIRCPAD_CIRC_OPENED;
  relay_machine->target_hopnum = 2;
```
Here, `target_hopnum` is set, but the comment for the attribute of the struct
says:
```c
typedef struct circpad_machine_spec_t {
  ...
  // These next three fields are origin machine-only...
  /** Origin side or relay side */
  unsigned is_origin_side : 1;

  /** Which hop in the circuit should we send padding to/from?
   *  1-indexed (ie: hop #1 is guard, #2 middle, #3 exit). */
  unsigned target_hopnum : 3;
```
since this is the non-origin (relay) machine, `target_hopnum` shouldn't be
needed. One might wonder here what the consequences are for there not being any
mechanism for preventing, say, the guard or exit being negotiated into running a
machine when it's not at the intended hop? 

### The RP Circuit Hiding Machine

```c
circpad_machine_relay_hide_rend_circuits(smartlist_t *machines_sl)
{
  ...
  relay_machine->target_hopnum = 2;
  ...
```
Same issue as for the other machine: this should only be needed for origins
(clients). 

```c
  /* OBFUSCATE_CIRC_SETUP -> END transition when we send our first
   * padding packet and/or hit the state length (the state length is 1). */
  relay_machine->states[CIRCPAD_STATE_OBFUSCATE_CIRC_SETUP].
      next_state[CIRCPAD_EVENT_PADDING_RECV] = CIRCPAD_STATE_END;
  relay_machine->states[CIRCPAD_STATE_OBFUSCATE_CIRC_SETUP].
      next_state[CIRCPAD_EVENT_LENGTH_COUNT] = CIRCPAD_STATE_END;
```
The `CIRCPAD_EVENT_PADDING_RECV` should be `CIRCPAD_EVENT_PADDING_SENT`, seems
like a bug, sent PR https://github.com/torproject/tor/pull/1167.
