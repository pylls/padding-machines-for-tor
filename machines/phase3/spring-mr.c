circpad_machine_spec_t *relay = tor_malloc_zero(sizeof(circpad_machine_spec_t));

relay->name = "spring_relay";
relay->machine_index = 0;
relay->target_hopnum = 2;
relay->is_origin_side = 0;
relay->allowed_padding_count = 1500;
relay->max_padding_percent = 50;
circpad_machine_states_init(relay, 4);
relay->states[0].iat_dist.type = CIRCPAD_DIST_PARETO;
relay->states[0].iat_dist.param1 = 5.460653840184872;
relay->states[0].iat_dist.param2 = 7.080387541173288;
relay->states[0].dist_max_sample_usec = 94722;
relay->states[0].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 1;
relay->states[0].next_state[CIRCPAD_EVENT_PADDING_RECV] = 1;

relay->states[1].iat_dist.type = CIRCPAD_DIST_LOGISTIC;
relay->states[1].iat_dist.param1 = 1.2767765551835941;
relay->states[1].iat_dist.param2 = 0.11492671368700358;
relay->states[1].dist_max_sample_usec = 31443;
relay->states[1].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 2;

relay->states[2].length_dist.type = CIRCPAD_DIST_LOGISTIC;
relay->states[2].length_dist.param1 = 4.11964473793041;
relay->states[2].length_dist.param2 = 2.7250362139341764;
relay->states[2].start_length = 5;
relay->states[2].iat_dist.type = CIRCPAD_DIST_LOGISTIC;
relay->states[2].iat_dist.param1 = 5.232180204916029;
relay->states[2].iat_dist.param2 = 5.469677647300559;
relay->states[2].dist_max_sample_usec = 94733;
relay->states[2].next_state[CIRCPAD_EVENT_PADDING_SENT] = 2;
relay->states[2].next_state[CIRCPAD_EVENT_PADDING_RECV] = 3;

relay->states[3].length_dist.type = CIRCPAD_DIST_LOG_LOGISTIC;
relay->states[3].length_dist.param1 = 1.6167675237934875;
relay->states[3].length_dist.param2 = 6.128003159320049;
relay->states[3].start_length = 5;
relay->states[3].iat_dist.type = CIRCPAD_DIST_UNIFORM;
relay->states[3].iat_dist.param1 = 4.270468437086448;
relay->states[3].iat_dist.param2 = 7.926284402139126;
relay->states[3].dist_max_sample_usec = 55878;
relay->states[3].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 3;
relay->states[3].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 0;
relay->states[3].next_state[CIRCPAD_EVENT_PADDING_RECV] = 2;

relay->machine_num = smartlist_len(relay_padding_machines);
circpad_register_padding_machine(relay, relay_padding_machines);