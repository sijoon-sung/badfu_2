"""Post-run arithmetic only; no model inference or new method selection."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    result = json.loads((ROOT/'remote_results/RESULT.json').read_text(encoding='utf-8'))
    verified = json.loads((ROOT/'remote_results/VERIFIED.json').read_text(encoding='utf-8'))
    assert verified['all_counts_exact']
    rows = result['results']
    labels = json.loads((ROOT/'BENCHMARK_LABELS.json').read_text())
    gaps = {}
    for arm in ('baseline','route'):
        attacks = [r['score'] for r in rows if r['arm'] == arm and r['case'] in labels['badfu_attack']]
        benign = [r['score'] for r in rows if r['arm'] == arm and r['case'] in labels['badfu_benign']]
        assert len(attacks) == 2 and len(benign) == 4
        gaps[arm] = dict(min_attack=min(attacks), max_benign=max(benign), gap=min(attacks)-max(benign))
    improvement = gaps['route']['gap']-gaps['baseline']['gap']
    supported = gaps['route']['gap'] > 0 and improvement >= .05
    summary = dict(gaps=gaps, route_gap_improvement=improvement, preregistered_added_value_supported=supported,
                   universal_trigger_family_independent_detection_validated=False,
                   fuba_successful_latent_positive_available=False,
                   attack_classification_status='calibration_required',
                   inference_scores_are_bounded_search_results_not_operational_TPR_FPR=True,
                   primary_seconds=result['seconds'], independent_counts_exact=True)
    (ROOT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'SCORES.csv').open('w',encoding='utf-8',newline='') as f:
        writer = csv.writer(f); writer.writerow(['case','arm','family','chosen_target','witness','n','score','source_classes_with_witness'])
        for r in rows:
            writer.writerow([r['case'],r['arm'],r['family'],r['target'],r['witness'],r['n'],r['score'],
                             sum(c['witness'] > 0 for c in r['source_counts'])])
    print(json.dumps(summary,indent=2))


if __name__ == '__main__': main()
