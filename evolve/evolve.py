#!/usr/bin/env python3
import machine
import random
import math

import numpy as np

'''
This is more genetic programming than genetic algorithms due to how we represent
the machines to evolve. 

TL;DR Johan suggestions: have advanced selection or simple selection and
mutation, mutation probability can be kept constant, elite fraction a good idea,
was worthwhile to remove all useless individuals instead of keeping for
diversity (Internet seems mixed on this though).

inspiration https://deap.readthedocs.io/en/master/api/tools.html
'''

def mutation(m, probability, exp):
    # with some probability, mutate each part of each state of a machine in place
    for s in m.states:
        if random.random() < probability:
            s.randomize_iat_dist(exp, probability)
        if random.random() < probability:
            s.randomize_length_dist(exp, probability)
        if random.random() < probability:
            s.randomize_transitions(exp, probability)

def crossover(m1, m2, probability):
    # with some probability, performs single-point crossover in place
    if random.random() < probability:
        c = random.randint(0, len(m1.states)-1)
        tmp = m1.states[:c]
        m1.states[:c] = m2.states[:c]
        m2.states[:c] = tmp

def selection(ml, fitness_func):
    # given a list of machines, selects the best, using the fitness function
    # we order, letting next_generation discard

    fl = []
    for mp in ml:
        fl.append(fitness_func(mp))
    
    # sort ml and fl together
    #fl, ml = (list(t) for t in zip(*sorted(zip(fl, ml))))
    idx   = np.argsort(fl)
    fl = list(np.array(fl)[idx])
    ml = list(np.array(ml)[idx])
    fl.reverse()
    ml.reverse()

    return ml, fl

def initial_population(mc, mr, exp):
    pop = []
    for _ in range(exp["population_size"]):
        pop.append([mc.randomize(exp), mr.randomize(exp)])
    return pop

def next_generation(ml, fl, exp):
    """ 
    Given a sorted list of pairs of machines (better to worse) and their
    fitness, creates the next generation of machines. Is elitist, keeping the
    best machines as-is, and includes some machines randomly for diversity. The
    rest of the population is evolved using crossover and mutation from randomly
    selected machines, selected by weight based on their fitness.
    """

    # elitist, pick a fraction of the best for the next generation
    n = math.floor(len(ml)*exp["elitist_frac"])
    ng = ml[:n]

    # diverse, pick a random fraction for the next generation
    n = math.floor(len(ml)*exp["diversity_frac"])
    ng.extend(random.choices(ml, k=n))

    # evolve remaining next generation
    while(len(ng) < len(ml)):
        # select two random parents, weighted by fitness
        parents = random.choices(ml, weights=fl, k=2)
        
        # make two new machines as clones
        m0c = parents[0][0].clone()
        m0r = parents[0][1].clone()
        m1c = parents[1][0].clone()
        m1r = parents[1][1].clone()

        # TODO: crossover between pairs, but never swap roles, with some probability?

        # crossover of states, per role
        crossover(m0c, m1c, exp["crossover_prob"])
        crossover(m0r, m1r, exp["crossover_prob"])

        # mutate each machine
        mutation(m0c, exp["mutation_prob"], exp)
        mutation(m0r, exp["mutation_prob"], exp)
        mutation(m1c, exp["mutation_prob"], exp)
        mutation(m1r, exp["mutation_prob"], exp)

        # done, add to population
        ng.append([m0c, m0r])
        ng.append([m1c, m1r])

    # we may end up evolving one machine too many above in case elitist and
    # diverse fractions result in an uneven number of machines
    return ng[:len(ml)]

def main():
    # can do head and tail independent
    # add probabilistic (consensus parameter) transition from head to tail and done
    # start with safest; simpler and more realistic evaluation of effectiveness
    # efficiency in absolutes (like the Sith!)
    
    # example hardcoded state
    s = machine.MachineState(
        iat_dist=machine.Distribution(machine.DistType.LOG_LOGISTIC, 2, 10),
        length_dist=machine.Distribution(machine.DistType.UNIFORM, 1, 5),
        length_dist_add=1,
        length_dist_max=100,
        transitions=[[machine.Event.PADDING_SENT, 0], [machine.Event.NONPADDING_SENT, 0]]
    )

    # can we create a machine?
    m = machine.Machine(name="goodenough", states=[s])
    print(f"{m}\n")
    print(f"m has ID {m.id()}")

    # can we generate c?
    conditions = "hardcoded_conditions;"
    print(conditions)
    print(m.to_c("generated"))

    # parameters for our experiment in a dict, easier to save
    exp = {}
    exp["num_states"] = 3
    exp["iat_d_low"] = 0.0
    exp["iat_d_high"] = 10.0
    exp["iat_a_low"] = 0
    exp["iat_a_high"] = 10
    exp["iat_m_low"] = 100
    exp["iat_m_high"] = 100*1000
    exp["length_d_low"] = 0
    exp["length_d_high"] = 100
    exp["length_a_low"] = 10
    exp["length_a_high"] = 100
    exp["length_m_low"] = 100
    exp["length_m_high"] = 1*1000

    # random machine check
    r = m.randomize(exp)
    print(r)
    print(r.to_c("random"))

    # mutation check
    r2 = r.clone()
    mutation(r2, 0.5, exp)
    print(f"\n{r}\n\n{r2}")

    # crossover check
    m1 = m.randomize(exp)
    m2 = m.randomize(exp)
    print(f"\n{m1}\n\n{m2}")
    crossover(m1, m2, 1.0)
    print(f"\n{m1}\n\n{m2}")

    # initial population, we evolve machines in *pairs*, highly asymmetrical setting
    exp["name"] = "evolved"
    exp["target_hopnum"] = 1
    exp["population_size"] = 10
    exp["allowed_padding_count_client"] = 1000
    exp["max_padding_percent_client"] = 50
    exp["allowed_padding_count_relay"] = 1000
    exp["max_padding_percent_relay"] = 50
    ## template client and relay machines with our parameters
    mc = machine.Machine(
        is_origin_side=True, name=exp["name"], target_hopnum=exp["target_hopnum"],
        allowed_padding_count=exp["allowed_padding_count_client"], 
        max_padding_percent=exp["max_padding_percent_client"],
        )
    mr = mc.clone()
    mr.is_origin_side = False
    mr.allowed_padding_count = exp["allowed_padding_count_relay"]
    mr.max_padding_percent = exp["max_padding_percent_relay"]
    print("")

    ml = initial_population(mc, mr, exp)
    print(f"ml has {len(ml)} pairs of machines")

    def bad_fit_func(mp):
        return random.random()

    ml, fl = selection(ml, bad_fit_func)

    for i in range(len(fl)):
        print(f"fitness {fl[i]:1.2} for {ml[i]}")

    # next_generation check, can be done without working fitness function
    exp["mutation_prob"] = 0.2
    exp["crossover_prob"] = 0.7
    exp["elitist_frac"] = 0.2
    exp["diversity_frac"] = 0.1

    # create dummy fl
    fl = [f for f in range(10)]
    ng = next_generation(ml, fl, exp)
    print(f"ng has {len(ng)} pairs of machines")

if __name__ == "__main__":
    main()