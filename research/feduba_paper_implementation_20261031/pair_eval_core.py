"""Evaluator-only counts and preregistered operational gates; no server detector."""
from fractions import Fraction
import torch


def evaluation_input(x, delta):
    assert x.ndim == 4 and x.shape[1:] == (3, 32, 32)
    assert delta.shape == (1, 3, 32, 32)
    assert x.dtype == delta.dtype == torch.float32
    assert bool(torch.isfinite(x).all()) and bool(torch.isfinite(delta).all())
    return torch.clamp(x + 1.5 * delta, -1, 1).contiguous()


def counts(labels, clean_logits, triggered_logits, target=2):
    assert labels.ndim == 1 and labels.dtype == torch.int64
    assert clean_logits.shape == triggered_logits.shape == (len(labels), 10)
    assert clean_logits.dtype == triggered_logits.dtype == torch.float32
    assert bool(((labels >= 0) & (labels < 10)).all())
    assert bool(torch.isfinite(clean_logits).all()) and bool(torch.isfinite(triggered_logits).all())
    eligible = labels != target
    return {'N': len(labels), 'clean_correct': int((clean_logits.argmax(1) == labels).sum()),
            'non_target_N': int(eligible.sum()),
            'triggered_target_hits': int(((triggered_logits.argmax(1) == target) & eligible).sum())}


def percentages(value):
    assert value['N'] > 0 and value['non_target_N'] > 0
    assert 0 <= value['clean_correct'] <= value['N']
    assert 0 <= value['triggered_target_hits'] <= value['non_target_N'] <= value['N']
    return {**value, 'CA_pct': 100 * value['clean_correct'] / value['N'],
            'ASR_pct': 100 * value['triggered_target_hits'] / value['non_target_N']}


def operational_gate(rows, limits):
    assert set(rows) == {'pre', 'benign', 'attack'}
    ca = {k: Fraction(100 * v['clean_correct'], v['N']) for k, v in rows.items()}
    asr = {k: Fraction(100 * v['triggered_target_hits'], v['non_target_N']) for k, v in rows.items()}
    threshold = {k: Fraction(str(v)) for k, v in limits.items()}
    checks = {'pre_ASR': asr['pre'] <= threshold['pre_ASR_max_pct'],
              'attack_ASR': asr['attack'] >= threshold['attack_ASR_min_pct'],
              'attack_minus_pre': asr['attack'] - asr['pre'] >= threshold['attack_minus_pre_ASR_min_pp'],
              'attack_minus_benign': asr['attack'] - asr['benign'] >= threshold['attack_minus_benign_FU_ASR_min_pp'],
              'all_three_CA': all(v >= threshold['all_three_CA_min_pct'] for v in ca.values()),
              'both_post_CA_drop': all(ca['pre'] - ca[k] <= threshold['post_CA_drop_max_pp'] for k in ['benign', 'attack'])}
    return {'passed': all(checks.values()), 'checks': checks,
            'attack_minus_pre_ASR_pp': float(asr['attack'] - asr['pre']),
            'attack_minus_benign_ASR_pp': float(asr['attack'] - asr['benign']),
            'post_CA_drop_pp': {k: float(ca['pre'] - ca[k]) for k in ['benign', 'attack']},
            'is_server_detection_threshold': False, 'is_exact_paper_mean_reproduction': False}
