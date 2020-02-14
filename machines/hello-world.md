# The Hello World Machine
This shows the steps we plan to take to design, implement, evaluate, and
document machines. It's just meant to be an example.

The goal of this example machine is simple: to send at least one padding cell in
each direction, to/from client from/to relay. We don't care about sending more
padding, being efficient, or making much sense. It's just an example.

## Design
Since we don't care much about anything for this machine, and I'm lazy, I'm just
going to take a randomly generated machine from a tool we're in the process of
tweaking.

## Implementation
This gets ugly. Below we look at the client and relay machines:

```c
circpad_machine_spec_t *gen_client = tor_malloc_zero(sizeof(circpad_machine_spec_t));
gen_client->conditions.state_mask = CIRCPAD_CIRC_STREAMS;
gen_client->conditions.purpose_mask = CIRCPAD_PURPOSE_ALL;
gen_client->conditions.reduced_padding_ok = 1;
gen_client->name = "evolved";
gen_client->machine_index = 0;
gen_client->target_hopnum = 1;
gen_client->is_origin_side = 1;
gen_client->allowed_padding_count = 200;
gen_client->max_padding_percent = 50;circpad_machine_states_init(gen_client, 6);
gen_client->states[0].length_dist.type = CIRCPAD_DIST_GEOMETRIC;
gen_client->states[0].length_dist.param1 = 4.814274646108755;
gen_client->states[0].length_dist.param2 = 4.869971264299856;
gen_client->states[0].start_length = 4;
gen_client->states[0].max_length = 505;
gen_client->states[0].iat_dist.type = CIRCPAD_DIST_NONE;
gen_client->states[0].iat_dist.param1 = 7.526266612653222;
gen_client->states[0].iat_dist.param2 = 7.403589208246087;
gen_client->states[0].start_length = 8;
gen_client->states[0].dist_max_sample_usec = 63304;
gen_client->states[0].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 4;
gen_client->states[1].length_dist.type = CIRCPAD_DIST_PARETO;
gen_client->states[1].length_dist.param1 = 4.403617327117251;
gen_client->states[1].length_dist.param2 = 5.996417832959251;
gen_client->states[1].start_length = 6;
gen_client->states[1].max_length = 483;
gen_client->states[1].iat_dist.type = CIRCPAD_DIST_GEOMETRIC;
gen_client->states[1].iat_dist.param1 = 8.361216732993883;
gen_client->states[1].iat_dist.param2 = 0.9264596277951376;
gen_client->states[1].start_length = 8;
gen_client->states[1].dist_max_sample_usec = 7065;
gen_client->states[1].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 2;
gen_client->states[1].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 0;
gen_client->states[2].length_dist.type = CIRCPAD_DIST_WEIBULL;
gen_client->states[2].length_dist.param1 = 1.0426652399191527;
gen_client->states[2].length_dist.param2 = 3.091020838174913;
gen_client->states[2].start_length = 10;
gen_client->states[2].max_length = 887;
gen_client->states[2].iat_dist.type = CIRCPAD_DIST_WEIBULL;
gen_client->states[2].iat_dist.param1 = 5.667292387983577;
gen_client->states[2].iat_dist.param2 = 7.958737236028522;
gen_client->states[2].dist_max_sample_usec = 23447;
gen_client->states[2].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 4;
gen_client->states[2].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 0;
gen_client->states[2].next_state[CIRCPAD_EVENT_PADDING_SENT] = 1;
gen_client->states[3].length_dist.type = CIRCPAD_DIST_PARETO;
gen_client->states[3].length_dist.param1 = 9.929415473412345;
gen_client->states[3].length_dist.param2 = 5.546471576686779;
gen_client->states[3].start_length = 7;
gen_client->states[3].max_length = 936;
gen_client->states[3].iat_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
gen_client->states[3].iat_dist.param1 = 3.332738685735962;
gen_client->states[3].iat_dist.param2 = 6.678039275209297;
gen_client->states[3].start_length = 3;
gen_client->states[3].dist_max_sample_usec = 38700;
gen_client->states[3].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 3;
gen_client->states[3].next_state[CIRCPAD_EVENT_LENGTH_COUNT] = 1;
gen_client->states[4].length_dist.type = CIRCPAD_DIST_UNIFORM;
gen_client->states[4].length_dist.param1 = 2.8857540118794556;
gen_client->states[4].length_dist.param2 = 6.125818574119025;
gen_client->states[4].start_length = 2;
gen_client->states[4].max_length = 820;
gen_client->states[4].iat_dist.type = CIRCPAD_DIST_PARETO;
gen_client->states[4].iat_dist.param1 = 4.519039376257881;
gen_client->states[4].iat_dist.param2 = 7.220421029371751;
gen_client->states[4].start_length = 6;
gen_client->states[4].dist_max_sample_usec = 79621;
gen_client->states[4].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 2;
gen_client->states[4].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 0;
gen_client->states[4].next_state[CIRCPAD_EVENT_PADDING_RECV] = 4;
gen_client->machine_num = smartlist_len(origin_padding_machines);
circpad_register_padding_machine(gen_client, origin_padding_machines);
```
Notice the generated states and their transitions (next_state). We see that no
state transitions to state 3 except for state 3 itself. In other words, state 3
is completely useless. Oh well, such is the life of a generated machine.

```c
circpad_machine_spec_t *gen_relay = tor_malloc_zero(sizeof(circpad_machine_spec_t));
gen_relay->name = "evolved";
gen_relay->machine_index = 0;
gen_relay->target_hopnum = 1;
gen_relay->allowed_padding_count = 2000;
gen_relay->max_padding_percent = 50;circpad_machine_states_init(gen_relay, 6);
gen_relay->states[0].length_dist.type = CIRCPAD_DIST_WEIBULL;
gen_relay->states[0].length_dist.param1 = 1.1119908099375175;
gen_relay->states[0].length_dist.param2 = 9.295631276879977;
gen_relay->states[0].start_length = 9;
gen_relay->states[0].max_length = 166;
gen_relay->states[0].iat_dist.type = CIRCPAD_DIST_NONE;
gen_relay->states[0].iat_dist.param1 = 5.140798889226186;
gen_relay->states[0].iat_dist.param2 = 3.7189363424246693;
gen_relay->states[0].start_length = 8;
gen_relay->states[0].dist_max_sample_usec = 19688;
gen_relay->states[0].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 1;
gen_relay->states[1].length_dist.type = CIRCPAD_DIST_UNIFORM;
gen_relay->states[1].length_dist.param1 = 7.4552261639344355;
gen_relay->states[1].length_dist.param2 = 6.5836447477507445;
gen_relay->states[1].start_length = 8;
gen_relay->states[1].max_length = 567;
gen_relay->states[1].iat_dist.type = CIRCPAD_DIST_WEIBULL;
gen_relay->states[1].iat_dist.param1 = 5.028757716771455;
gen_relay->states[1].iat_dist.param2 = 3.6175408250793497;
gen_relay->states[1].start_length = 2;
gen_relay->states[1].dist_max_sample_usec = 63563;
gen_relay->states[1].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 0;
gen_relay->states[2].length_dist.type = CIRCPAD_DIST_WEIBULL;
gen_relay->states[2].length_dist.param1 = 5.622586262962072;
gen_relay->states[2].length_dist.param2 = 0.30230478680857154;
gen_relay->states[2].start_length = 1;
gen_relay->states[2].max_length = 391;
gen_relay->states[2].iat_dist.type = CIRCPAD_DIST_GEOMETRIC;
gen_relay->states[2].iat_dist.param1 = 9.494124071150765;
gen_relay->states[2].iat_dist.param2 = 4.857852071000062;
gen_relay->states[2].start_length = 5;
gen_relay->states[2].dist_max_sample_usec = 68729;
gen_relay->states[3].length_dist.type = CIRCPAD_DIST_GEOMETRIC;
gen_relay->states[3].length_dist.param1 = 0.7518053414585135;
gen_relay->states[3].length_dist.param2 = 2.2110771083054215;
gen_relay->states[3].start_length = 1;
gen_relay->states[3].max_length = 141;
gen_relay->states[3].iat_dist.type = CIRCPAD_DIST_GEOMETRIC;
gen_relay->states[3].iat_dist.param1 = 3.7855567949957916;
gen_relay->states[3].iat_dist.param2 = 5.158070632109185;
gen_relay->states[3].dist_max_sample_usec = 77068;
gen_relay->states[3].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 2;
gen_relay->states[4].length_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
gen_relay->states[4].length_dist.param1 = 7.327935236568187;
gen_relay->states[4].length_dist.param2 = 4.431830291905961;
gen_relay->states[4].start_length = 5;
gen_relay->states[4].max_length = 105;
gen_relay->states[4].iat_dist.type = CIRCPAD_DIST_UNIFORM;
gen_relay->states[4].iat_dist.param1 = 5.256975990732162;
gen_relay->states[4].iat_dist.param2 = 2.2653274630000197;
gen_relay->states[4].dist_max_sample_usec = 35592;
gen_relay->states[4].next_state[CIRCPAD_EVENT_LENGTH_COUNT] = 2;
gen_relay->machine_num = smartlist_len(relay_padding_machines);
circpad_register_padding_machine(gen_relay, relay_padding_machines);
```

The relay machine is even worse: states 0 and 1 only have transitions to each
other, so states 2-4 are useless.

## Evaluation
Let's see if the above machine does something. Using the circpad simulator we
simulate the goodenough February dataset for the safest security level. We then
pick a random trace and verify that the machine is producing padding:

```
$ cat monitored/1-0.trace | grep circpad_cell_event_padding | wc -l
241
```

The trace contained 241 padding events, great, it does something! 

Let's also see how effective the machine is as a defense against the Deep
Fingerprinting attack by using `/evaluation/once.py` from this repo. 

Results with the machine:
```
threshold  0.0, recall  0.9, precision 0.93, F1 0.91, accuracy 0.92   [tp   898, fpp    17, fnp    53, tn   947, fn    85]
threshold 0.11, recall  0.9, precision 0.93, F1 0.91, accuracy 0.92   [tp   898, fpp    17, fnp    53, tn   947, fn    85]
threshold 0.35, recall  0.9, precision 0.93, F1 0.91, accuracy 0.92   [tp   898, fpp    16, fnp    53, tn   947, fn    86]
threshold 0.53, recall 0.89, precision 0.94, F1 0.91, accuracy 0.92   [tp   887, fpp    12, fnp    45, tn   955, fn   101]
threshold 0.66, recall 0.88, precision 0.96, F1 0.91, accuracy 0.92   [tp   877, fpp     7, fnp    34, tn   966, fn   116]
threshold 0.75, recall 0.86, precision 0.97, F1 0.91, accuracy 0.92   [tp   863, fpp     5, fnp    24, tn   976, fn   132]
threshold 0.82, recall 0.85, precision 0.97, F1 0.91, accuracy 0.92   [tp   854, fpp     4, fnp    20, tn   980, fn   142]
threshold 0.87, recall 0.85, precision 0.98, F1 0.91, accuracy 0.92   [tp   849, fpp     3, fnp    18, tn   982, fn   148]
threshold 0.91, recall 0.84, precision 0.98, F1 0.91, accuracy 0.92   [tp   845, fpp     3, fnp    15, tn   985, fn   152]
threshold 0.93, recall 0.84, precision 0.98, F1  0.9, accuracy 0.91   [tp   838, fpp     2, fnp    14, tn   986, fn   160]
threshold 0.95, recall 0.83, precision 0.98, F1  0.9, accuracy 0.91   [tp   832, fpp     2, fnp    12, tn   988, fn   166]
threshold 0.96, recall 0.83, precision 0.99, F1  0.9, accuracy 0.91   [tp   826, fpp     1, fnp    10, tn   990, fn   173]
threshold 0.97, recall 0.82, precision 0.99, F1  0.9, accuracy  0.9   [tp   818, fpp     1, fnp     9, tn   991, fn   181]
threshold 0.98, recall 0.81, precision 0.99, F1 0.89, accuracy  0.9   [tp   805, fpp     1, fnp     6, tn   994, fn   194]
threshold 0.99, recall  0.8, precision 0.99, F1 0.88, accuracy  0.9   [tp   796, fpp     0, fnp     6, tn   994, fn   204]
threshold 0.99, recall 0.79, precision 0.99, F1 0.88, accuracy 0.89   [tp   787, fpp     0, fnp     5, tn   995, fn   213]
```

And without the machine:
```
threshold  0.0, recall 0.87, precision 0.91, F1 0.89, accuracy 0.91   [tp   868, fpp    34, fnp    51, tn   949, fn    98]
threshold 0.11, recall 0.87, precision 0.91, F1 0.89, accuracy 0.91   [tp   868, fpp    34, fnp    51, tn   949, fn    98]
threshold 0.35, recall 0.87, precision 0.91, F1 0.89, accuracy 0.91   [tp   868, fpp    32, fnp    50, tn   950, fn   100]
threshold 0.53, recall 0.86, precision 0.93, F1  0.9, accuracy 0.91   [tp   863, fpp    22, fnp    43, tn   957, fn   115]
threshold 0.66, recall 0.85, precision 0.94, F1 0.89, accuracy 0.91   [tp   855, fpp    17, fnp    40, tn   960, fn   128]
threshold 0.75, recall 0.85, precision 0.95, F1 0.89, accuracy 0.91   [tp   846, fpp    14, fnp    34, tn   966, fn   140]
threshold 0.82, recall 0.84, precision 0.96, F1  0.9, accuracy 0.91   [tp   841, fpp    10, fnp    28, tn   972, fn   149]
threshold 0.87, recall 0.83, precision 0.97, F1 0.89, accuracy  0.9   [tp   833, fpp     5, fnp    25, tn   975, fn   162]
threshold 0.91, recall 0.82, precision 0.97, F1 0.89, accuracy  0.9   [tp   822, fpp     2, fnp    24, tn   976, fn   176]
threshold 0.93, recall 0.82, precision 0.98, F1 0.89, accuracy  0.9   [tp   816, fpp     2, fnp    18, tn   982, fn   182]
threshold 0.95, recall 0.81, precision 0.98, F1 0.88, accuracy  0.9   [tp   806, fpp     2, fnp    14, tn   986, fn   192]
threshold 0.96, recall  0.8, precision 0.99, F1 0.88, accuracy 0.89   [tp   796, fpp     1, fnp    11, tn   989, fn   203]
threshold 0.97, recall 0.78, precision 0.99, F1 0.87, accuracy 0.89   [tp   781, fpp     0, fnp     9, tn   991, fn   219]
threshold 0.98, recall 0.77, precision 0.99, F1 0.86, accuracy 0.88   [tp   768, fpp     0, fnp     8, tn   992, fn   232]
threshold 0.99, recall 0.76, precision 0.99, F1 0.86, accuracy 0.88   [tp   761, fpp     0, fnp     7, tn   993, fn   239]
threshold 0.99, recall 0.75, precision 0.99, F1 0.86, accuracy 0.87   [tp   752, fpp     0, fnp     5, tn   995, fn   248]
```

As we can see, a random machine is not always a defense at all: in this case it
made the DF attack better, not worse.

## Documentation
This is the documentation. The closer we get to an efficient and effective
machine, the more time we plan to spend.