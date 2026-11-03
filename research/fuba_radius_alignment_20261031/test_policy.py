import json
from pathlib import Path
from radius_policy import decay_for_interval, training_radius

values = [training_radius(r) for r in range(100)]
assert values[5] == .3 and values[99] == .05
assert all(.05 <= v <= .3 for v in values)
assert all(a >= b for a, b in zip(values, values[1:]))
d = decay_for_interval()
assert abs(.3 * (1 - d) ** 94 - .05) < 1e-14
assert training_radius(500) == .05 and training_radius(-1) == .3
for args in [(.05, .3, 5, 99), (.3, 0, 5, 99), (.3, .05, 99, 99)]:
    try:
        decay_for_interval(*args)
    except ValueError:
        pass
    else:
        raise AssertionError(args)
r = {'state': 'passed', 'decay': d, 'initial': values[5], 'last': values[99],
     'form': 'IBA Eq4; decay determined by declared finite boundary conditions',
     'unique_author_value_claimed': False}
Path(__file__).with_name('CPU_CONTRACTS.json').write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(r))
