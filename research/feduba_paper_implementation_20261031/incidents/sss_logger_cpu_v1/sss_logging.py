"""Forward-only attacker observation interface; model parameters are not an input."""
import torch


@torch.inference_mode()
def observe_and_rank(query_logits, indexed_loader, delta, device):
    ranked, observations = [], []
    for x, unused_labels, ids in indexed_loader:
        x = x.to(device).contiguous()
        clean = query_logits(x)
        # Eq.6 uses no clipping and multiplier one; evaluation has a separate policy.
        perturbed = query_logits(x + delta.to(x))
        assert not torch.is_grad_enabled() and clean.shape == perturbed.shape
        assert clean.ndim == 2 and len(clean) == len(ids)
        assert clean.dtype == perturbed.dtype == torch.float32
        scores = torch.linalg.vector_norm(perturbed - clean, ord=2, dim=1)
        assert all(bool(torch.isfinite(v).all()) for v in [x, clean, perturbed, scores])
        observations.append({'source_ids': ids.detach().cpu().clone(), 'x': x.detach().cpu().clone(),
                             'clean_logits': clean.detach().cpu().clone(), 'perturbed_logits': perturbed.detach().cpu().clone(),
                             'score_FP32': scores.detach().cpu().clone(), 'forward_query_calls': 2,
                             'gradient_enabled': False, 'labels_used_in_score': False})
        ranked.extend((int(i), float(score)) for i, score in zip(ids, scores.cpu()))
    assert ranked and len(ranked) == len({i for i, _ in ranked})
    return sorted(ranked, key=lambda item: (-item[1], item[0])), observations
