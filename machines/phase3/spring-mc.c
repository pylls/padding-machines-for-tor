circpad_machine_spec_t *client = tor_malloc_zero(sizeof(circpad_machine_spec_t));
client->conditions.state_mask = CIRCPAD_CIRC_STREAMS;
client->conditions.purpose_mask = CIRCPAD_PURPOSE_ALL;
client->conditions.reduced_padding_ok = 1;

client->name = "spring_client";
client->machine_index = 0;
client->target_hopnum = 2;
client->is_origin_side = 1;
client->allowed_padding_count = 1500;
client->max_padding_percent = 50;
circpad_machine_states_init(client, 3);

client->states[0].next_state[CIRCPAD_EVENT_PADDING_RECV] = 1;

client->states[1].next_state[CIRCPAD_EVENT_NONPADDING_RECV] = 2;

client->states[2].length_dist.type = CIRCPAD_DIST_PARETO;
client->states[2].length_dist.param1 = 4.776842508009852;
client->states[2].length_dist.param2 = 4.807709366988267;
client->states[2].start_length = 1;
client->states[2].iat_dist.type = CIRCPAD_DIST_PARETO;
client->states[2].iat_dist.param1 = 3.3391870088596;
client->states[2].iat_dist.param2 = 7.179045336148708;
client->states[2].dist_max_sample_usec = 9445;
client->states[2].next_state[CIRCPAD_EVENT_NONPADDING_SENT] = 1;
client->states[2].next_state[CIRCPAD_EVENT_PADDING_SENT] = 2;

client->machine_num = smartlist_len(origin_padding_machines);
circpad_register_padding_machine(client, origin_padding_machines);