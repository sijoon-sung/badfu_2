"""IBA exponential form with explicit finite-run boundary conditions."""
import math


def decay_for_interval(initial=.3, final=.05, first_round=5, last_round=99):
    if not 0 < final <= initial or last_round <= first_round:
        raise ValueError('Require positive bounds and a nonempty decay interval')
    return -math.expm1(math.log(final / initial) / (last_round - first_round))


def training_radius(round_zero_based, *, initial=.3, final=.05, first_round=5, last_round=99):
    decay = decay_for_interval(initial, final, first_round, last_round)
    if round_zero_based <= first_round:
        return initial
    if round_zero_based >= last_round:
        return final
    return max(final, initial * (1 - decay) ** (round_zero_based - first_round))
