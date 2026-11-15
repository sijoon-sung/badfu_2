"""Explicit full-participation schedule of the linked author's original code.

This reproduces source scheduling, including its AFTER-global reference. It is
not an automatic mapping of FUBA's 100-round history to its stated FU20 budget.
"""
import math


def author_schedule(*, global_epochs, interval, local_epochs, calibration_ratio):
    if not all(isinstance(x, int) and x > 0 for x in [global_epochs, interval, local_epochs]):
        raise ValueError('Positive integer epochs and interval required')
    if interval > global_epochs or global_epochs % interval:
        raise ValueError('This declared contract requires complete interval coverage')
    if not 0 < calibration_ratio <= 1:
        raise ValueError('Calibration ratio must be in (0,1]')
    rounds = list(range(interval, global_epochs + 1, interval))
    return {
        'initial_global_round': 0,
        'first_overlay_client_round': rounds[0],
        'calibration_local_epochs': math.ceil(local_epochs * calibration_ratio),
        'calibration': [
            {'old_client_round': r, 'old_global_round': r,
             'old_global_reference': 'AFTER aggregation, literal original source'}
            for r in rounds[1:]
        ],
        'output_updates': len(rounds),
        'calibration_calls': len(rounds) - 1,
        'full_participation_only': True,
        'FUBA_100_to_20_mapping_validated': False,
    }
