circpad_machine_spec_t *relay = tor_malloc_zero(sizeof(circpad_machine_spec_t));

// short define for sampling uniformly random [0,1.0]
const struct uniform_t my_uniform = {
    .base = UNIFORM(my_uniform),
    .a = 0.0,
    .b = 1.0,
};
#define CIRCPAD_UNI_RAND (dist_sample(&my_uniform.base))

// uniformly random select a distribution parameters between [0,10]
#define CIRCPAD_RAND_DIST_PARAM1 (CIRCPAD_UNI_RAND*10)
#define CIRCPAD_RAND_DIST_PARAM2 (CIRCPAD_UNI_RAND*10)

relay->name = "interspace_relay";
relay->machine_index = 0;
relay->target_hopnum = 2;
relay->is_origin_side = 0;
relay->allowed_padding_count = 1500;
relay->max_padding_percent = 50;
circpad_machine_states_init(relay, 4);

if (CIRCPAD_UNI_RAND < 0.5) {
    /*
    machine has following states:
    0. init: don't waste time early
    1. wait: either extend or fake
    2. extend: obfuscate length of existing bursts
    3. fake: inject fake bursts
    */

    // wait for client to send something, no point in doing stuff too early
    relay->states[0].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 1;

    if (CIRCPAD_UNI_RAND < 0.5) {
        // wait: extend real burst
        relay->states[1].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 2;
    } else {
        // wait: inject a fake burst after a while (FIXME: too long below)
        relay->states[1].iat_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
        relay->states[1].iat_dist.param1 = CIRCPAD_UNI_RAND*1000; // alpha, scale and mean
        relay->states[1].iat_dist.param2 = CIRCPAD_UNI_RAND*10000; // shape, when > 1 larger reduces dispersion
        relay->states[1].dist_max_sample_usec = 100000;
        relay->states[1].next_state[CIRCPAD_EVENT_PADDING_SENT] = 3;
    }

    // extend: add fake padding for real bursts
    relay->states[2].length_dist.type = CIRCPAD_DIST_PARETO;
    relay->states[2].length_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[2].length_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[2].start_length = 1;
    relay->states[2].iat_dist.type = CIRCPAD_DIST_PARETO;
    relay->states[2].iat_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[2].iat_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[2].dist_max_sample_usec = 10000;
    relay->states[2].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 1;
    relay->states[2].next_state[CIRCPAD_EVENT_PADDING_SENT] = 2;

    // fake: inject completely fake bursts
    relay->states[3].length_dist.type = CIRCPAD_DIST_PARETO;
    relay->states[3].length_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[3].length_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[3].start_length = 4;
    relay->states[3].iat_dist.type = CIRCPAD_DIST_PARETO;
    relay->states[3].iat_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[3].iat_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[3].dist_max_sample_usec = 10000;
    relay->states[3].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 1;
    relay->states[3].next_state[CIRCPAD_EVENT_PADDING_SENT] = 3;
} else {
    // spring-mr
    relay->states[0].iat_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
    relay->states[0].iat_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[0].iat_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[0].dist_max_sample_usec = 10000;
    relay->states[0].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 1;
    relay->states[0].next_state[CIRCPAD_EVENT_PADDING_RECV] = 1;

    relay->states[1].iat_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
    relay->states[1].iat_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[1].iat_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[1].dist_max_sample_usec = 31443;
    relay->states[1].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 2;

    relay->states[2].length_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
    relay->states[2].length_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[2].length_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[2].start_length = 5;
    relay->states[2].iat_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
    relay->states[2].iat_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[2].iat_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[2].dist_max_sample_usec = 100000;
    relay->states[2].next_state[CIRCPAD_EVENT_PADDING_SENT] = 2;
    relay->states[2].next_state[CIRCPAD_EVENT_PADDING_RECV] = 3;

    relay->states[3].length_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
    relay->states[3].length_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[3].length_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[3].start_length = 5;
    relay->states[3].iat_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
    relay->states[3].iat_dist.param1 = CIRCPAD_RAND_DIST_PARAM1;
    relay->states[3].iat_dist.param2 = CIRCPAD_RAND_DIST_PARAM2;
    relay->states[3].dist_max_sample_usec = 55878;
    relay->states[3].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 3;
    relay->states[3].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 0;
    relay->states[3].next_state[CIRCPAD_EVENT_PADDING_RECV] = 2;
}

relay->machine_num = smartlist_len(relay_padding_machines);
circpad_register_padding_machine(relay, relay_padding_machines);
