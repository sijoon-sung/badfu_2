"""Paper Eq.7 selection: labels are deliberately absent from this interface."""
import math


def select_all_classes(owner_ranks, ownership, budget):
    if type(budget) is not int or budget <= 0:
        raise ValueError('budget must be a positive integer')
    candidates, seen = [], set()
    if set(owner_ranks) != set(ownership):
        raise ValueError('rank owners differ from declared owners')
    for owner, rows in owner_ranks.items():
        ids = [i for i, _ in rows]
        if len(set(ids)) != len(ids) or set(ids) != set(ownership[owner]):
            raise ValueError('ranks must contain each owned source ID exactly once')
        if seen.intersection(ids):
            raise ValueError('source ID belongs to more than one owner')
        seen.update(ids)
        for source_id, score in rows:
            if not math.isfinite(score):
                raise ValueError('nonfinite score')
            candidates.append((score, source_id, owner))
    if len(candidates) < budget:
        raise ValueError('budget exceeds available samples')
    top = sorted(candidates, key=lambda row: (-row[0], row[1]))[:budget]
    return {owner: [i for _, i, who in top if who == owner] for owner in owner_ranks}
