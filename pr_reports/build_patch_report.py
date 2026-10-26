"""Rebuild D26, its figures, and auditable data from the fixed 70-request cutoff.

No model training, inference, network access, or threshold selection occurs here.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EVIDENCE = HERE / "evidence/patch_interim_20261019_1658"
FIGURES = HERE / "figures/D26"
THRESHOLD = 0.006
LEVELS = (0.2, 0.7, 0.9)
LABELS = {
    "attack_delete_cover": "억제 자료만 삭제(공격)",
    "equal_size_safe": "같은 크기의 안전 삭제",
    "delete_poison": "독성 자료만 삭제",
    "delete_both": "독성·억제 자료 모두 삭제",
    "benign_class_prior": "정상 클래스 편향 대조",
    "label_noise": "패치 없는 오라벨 대조",
    "normal_cover": "정답 라벨 패치 자료 삭제",
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
                     + ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def count(rows):
    attacks = [r for r in rows if r["construction_attack"]]
    controls = [r for r in rows if not r["construction_attack"]]
    latent = [r for r in attacks if r["realized_latent_activation"]]
    return dict(requests=len(rows), attacks=len(attacks), true_positives=sum(r["flag"] for r in attacks),
                controls=len(controls), false_positives=sum(r["flag"] for r in controls),
                latent=len(latent), latent_detected=sum(r["flag"] for r in latent),
                gain_only_true_positives=sum(r["retained_gain_flag"] for r in attacks),
                gain_only_false_positives=sum(r["retained_gain_flag"] for r in controls))


def validate_and_summarize():
    # The original fixed protocol and interim totals are copied only once.
    for source, name in [(REPO / "research_20261019/patch_scale_v1/protocol.json", "protocol.json"),
                         (REPO / "research_20261019/patch_scale_v1/interim_latest.json", "interim_reference.json")]:
        if not (EVIDENCE / name).exists():
            shutil.copyfile(source, EVIDENCE / name)
    raw = read(EVIDENCE / "results.json")
    rows = raw["rows"]
    protocol = read(EVIDENCE / "protocol.json")
    responses = read(EVIDENCE / "probe_responses.json")
    reference = read(EVIDENCE / "interim_reference.json")
    assert len(rows) == 70 and len(raw["completed_cells"]) == 10
    assert len({(r["cell"], r["request"]) for r in rows}) == 70
    assert raw["protocol_sha256"] == sha(EVIDENCE / "protocol.json")
    assert responses["source_hashes"] == protocol["source_hashes"]
    for relative, expected in protocol["source_hashes"].items():
        assert sha(REPO / "research_20261019/patch_scale_v1" / relative) == expected
    lookup = {(r["cell"], r["request"]): r for r in responses["rows"]}
    max_error = 0.0
    for r in rows:
        assert r["threshold"] == THRESHOLD
        assert r["protocol_sha256"] == raw["protocol_sha256"]
        assert r["future_checkpoint_existed_at_prediction"] is False
        assert r["construction_attack"] == (r["request"] == "attack_delete_cover")
        p = lookup[r["cell"], r["request"]]["patch_response"]
        d = {role: {split: np.asarray(values, dtype=np.float32) for split, values in splits.items()}
             for role, splits in p.items()}
        assert all(v.shape == (32, 10) for splits in d.values() for v in splits.values())
        candidate = d["retained"]["development"] - d["pre"]["development"]
        i, t = np.unravel_index(candidate.argmax(), candidate.shape)
        assert (int(i), int(t)) == (r["pattern_index"], r["target"])
        gain = float(d["retained"]["validation"][i, t] - d["pre"]["validation"][i, t])
        contrast = float(d["retained"]["validation"][i, t] - d["forget"]["validation"][i, t])
        score = max(0.0, min(gain, contrast))
        error = max(abs(gain-r["retained_gain"]), abs(contrast-r["branch_contrast"]), abs(score-r["score"]))
        max_error = max(max_error, error)
        assert error < 1e-7, (r["cell"], r["request"], error)
        assert r["flag"] == (score > THRESHOLD)
        assert r["retained_gain_flag"] == (gain > THRESHOLD)
        pre, post = r["pre_actual_trigger_asr"], r["post_actual_trigger_asr"]
        assert abs(post-pre-r["actual_asr_increase"]) < 1e-12
        assert r["realized_latent_activation"] == (pre <= .1 and post >= .5 and post-pre >= .3)
    for r in reference["attacks"] + reference["false_positives"]:
        match = next(x for x in rows if (x["cell"], x["request"]) == (r["cell"], r["request"]))
        for key, value in r.items():
            assert match[key] == value, (key, value, match[key])
    summary = dict(cutoff_kst=raw["report_cutoff_kst"], completed_cells=10, planned_cells=30,
                   completed_requests=70, planned_requests=210, threshold=THRESHOLD,
                   overall=count(rows), by_non_iid={str(x): count([r for r in rows if r["dominant_class_fraction"] == x]) for x in LEVELS},
                   by_request={name: count([r for r in rows if r["request"] == name]) for name in LABELS},
                   exceptions=[r for r in rows if r["flag"] != r["construction_attack"]])
    assert summary["overall"]["true_positives"] == 9
    assert summary["overall"]["false_positives"] == 2
    assert summary["overall"]["gain_only_false_positives"] == 11
    write(EVIDENCE / "summary.json", summary)
    # Preserve every scalar and both class histograms in an ordinary CSV.
    with (EVIDENCE / "results.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()} for r in rows)
    validation = dict(requests_recomputed=70, candidate_selection_recomputed=70,
                      response_shape_per_model_per_split=[32, 10], max_absolute_score_component_error=max_error,
                      frozen_threshold=THRESHOLD, future_absence_record_checked=70,
                      remote_prediction_file_hashes_checked=70,
                      protocol_sha256=raw["protocol_sha256"], source_hashes=responses["source_hashes"],
                      note="Remote saved logits were reduced without inference; local float32 reconstruction checks development selection and validation score. Future-absence checks use the locked experiment records.")
    write(EVIDENCE / "VALIDATION.json", validation)
    return rows, summary


def make_figures(rows, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    font = Path("C:/Windows/Fonts/malgun.ttf")
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({"axes.unicode_minus": False, "font.size": 10.5, "axes.titlesize": 12,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "savefig.facecolor": "white", "pdf.fonttype": 42})
    red, blue, gold, gray = "#BE3347", "#2869A6", "#C88D21", "#555F6B"
    FIGURES.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        fig.savefig(FIGURES / (name + ".png"), dpi=180, bbox_inches="tight")
        fig.savefig(FIGURES / (name + ".pdf"), bbox_inches="tight")
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.8), sharey=True)
    for ax, level in zip(axes, LEVELS):
        values = [r for r in rows if r["dominant_class_fraction"] == level]
        for group, is_attack in enumerate((True, False)):
            chosen = [r for r in values if r["construction_attack"] == is_attack]
            chosen.sort(key=lambda r: (r["score"], r["seed"], r["request"]))
            xs = group + np.linspace(-.19, .19, len(chosen))
            ax.scatter(xs, [r["score"] for r in chosen], c=red if is_attack else blue,
                       marker="^" if is_attack else "o", s=65 if is_attack else 39,
                       alpha=.87, edgecolors="white", linewidths=.6, zorder=3)
            for x, r in zip(xs, chosen):
                if r["flag"] != r["construction_attack"]:
                    name = "미탐: 1005" if is_attack else ("오탐: 오라벨" if r["request"] == "label_noise" else "오탐: 정답 패치")
                    ax.annotate(name, (x, r["score"]), xytext=(-65 if is_attack else -55, 15 if is_attack else 10),
                                textcoords="offset points", fontsize=8.5,
                                arrowprops=dict(arrowstyle="-", color=gray, lw=.8))
        ax.axhline(THRESHOLD, ls="--", color=gray, lw=1.2)
        c = summary["by_non_iid"][str(level)]
        ax.set_title(f"기본 두 클래스 {int(level*100)}%\n공격 {c['true_positives']}/{c['attacks']} · 대조 오탐 {c['false_positives']}/{c['controls']}")
        ax.set_xticks([0, 1], ["공격 요청", "대조 6종"])
        ax.set_xlim(-.5, 1.5); ax.set_ylim(-.0015, .037)
        ax.set_yticks(np.arange(0, .037, .006)); ax.grid(axis="y", alpha=.18)
    axes[0].set_ylabel("패치 탐지 점수 S (평균 확률 차이)")
    axes[-1].text(1.45, THRESHOLD+.0005, "고정 기준 0.006", ha="right", fontsize=8.5, color=gray)
    fig.suptitle("완료 70건: 공격 9/10건 탐지, 대조 요청 2/60건 오탐", fontsize=14, y=1.02)
    fig.text(.5, -.025, "점 하나 = 요청 하나. 같은 높이의 점은 겹침을 줄이기 위해 좌우로 배치했다. 20%는 기본 자료의 클래스 균등 조건.", ha="center", fontsize=9, color=gray)
    fig.tight_layout(); save(fig, "01_score_by_skew")

    fig, ax = plt.subplots(figsize=(10.4, 5.8))
    markers = {.2: "o", .7: "s", .9: "^"}
    for level in LEVELS:
        for attack in (True, False):
            subset = [r for r in rows if r["dominant_class_fraction"] == level and r["construction_attack"] == attack]
            ax.scatter([r["score"] for r in subset], [100*r["actual_asr_increase"] for r in subset],
                       c=red if attack else blue, marker=markers[level], s=64, alpha=.85,
                       edgecolors="white", linewidths=.6, zorder=3)
    ax.axvline(THRESHOLD, color=gray, ls="--", lw=1.2)
    ax.axhline(0, color=gray, lw=.7, alpha=.4)
    ax.set(xlim=(-.001, .037), ylim=(-23, 105), xlabel="패치 탐지 점수 S", ylabel="평가 패턴의 타깃 오분류율 변화 (%p)",
           title="탐지 점수와 실제 잔류 자료 재학습 후 변화")
    for r in summary["exceptions"]:
        label = "미탐: 1005 / 20%" if r["construction_attack"] else "오탐: 1009 / " + ("오라벨" if r["request"] == "label_noise" else "정답 패치")
        offset = (-8, 16) if r["construction_attack"] else ((25, 20) if r["request"] == "label_noise" else (25, -23))
        ax.annotate(label, (r["score"], 100*r["actual_asr_increase"]), xytext=offset,
                    textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color=gray))
    legend = [Line2D([0], [0], marker="o", color="w", markerfacecolor=red, markersize=8, label="공격 구성 요청"),
              Line2D([0], [0], marker="o", color="w", markerfacecolor=blue, markersize=8, label="대조 요청")]
    legend += [Line2D([0], [0], marker=markers[x], color=gray, ls="", label=f"기본 두 클래스 {int(x*100)}%") for x in LEVELS]
    ax.legend(handles=legend, loc="center right", frameon=False, fontsize=9)
    ax.grid(alpha=.15)
    fig.text(.5, -.005, "공격 요청에서는 ASR 변화다. 공격을 심지 않은 대조에서는 같은 평가 패턴에 대한 타깃 오분류율 변화다.", ha="center", fontsize=9, color=gray)
    fig.tight_layout(); save(fig, "02_score_vs_outcome")

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.1), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    for attack in (True, False):
        subset = [r for r in rows if r["construction_attack"] == attack]
        ax.scatter([r["retained_gain"] for r in subset], [r["branch_contrast"] for r in subset],
                   c=red if attack else blue, marker="^" if attack else "o", s=48, alpha=.82,
                   label="공격" if attack else "대조", edgecolors="white", linewidths=.5, zorder=3)
    ax.axvline(THRESHOLD, ls="--", lw=1, color=gray); ax.axhline(THRESHOLD, ls="--", lw=1, color=gray)
    ax.set(xlabel="a: 유지 분기 - 원본의 패치 반응", ylabel="b: 유지 분기 - 삭제 분기의 패치 반응",
           title="같은 후보에서 두 조건을 모두 확인")
    # Bounds include every observation; the shaded area is the joint alarm region.
    xmin = min(-.003, min(r["retained_gain"] for r in rows)-.002)
    xmax = max(.045, max(r["retained_gain"] for r in rows)+.003)
    ymin = min(-.01, min(r["branch_contrast"] for r in rows)-.005)
    ymax = max(.05, max(r["branch_contrast"] for r in rows)+.005)
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
    ax.add_patch(Rectangle((THRESHOLD, THRESHOLD), xmax-THRESHOLD, ymax-THRESHOLD, color="#FBECEE", zorder=0))
    ax.text(THRESHOLD+.002, ymax-.01, "두 조건을 모두 넘으면 경보", color=red, fontsize=9)
    ax.legend(frameon=False, loc="lower right"); ax.grid(alpha=.15)
    ax = axes[1]; x = np.arange(4); width = .35
    counts = [summary["by_non_iid"][str(level)] for level in LEVELS] + [summary["overall"]]
    single = [r["gain_only_false_positives"] for r in counts]
    paired = [r["false_positives"] for r in counts]
    bars1 = ax.bar(x-width/2, single, width, color=gold, label="a만 검사")
    bars2 = ax.bar(x+width/2, paired, width, color=blue, label="a와 b 모두 검사")
    for bars, values in [(bars1, single), (bars2, paired)]:
        ax.bar_label(bars, labels=[f"{v}/{c['controls']}" for v, c in zip(values, counts)], padding=4, fontsize=9)
    ax.set_xticks(x, ["20%", "70%", "90%", "전체"])
    ax.set(ylabel="대조 요청 경보 건수", ylim=(0, 13.2), title="같은 후보·기준값에서 대조 경보 11→2건")
    ax.legend(frameon=False); ax.grid(axis="y", alpha=.15)
    fig.text(.5, -.005, "완료된 동일 70건의 저장 출력 비교. 두 방식 모두 공격 탐지는 9/10건. 분류 기준·후보를 결과에 맞춰 바꾸지 않았다.", ha="center", fontsize=9, color=gray)
    fig.tight_layout(); save(fig, "03_two_branch_comparison")

    attacks = sorted([r for r in rows if r["construction_attack"]], key=lambda r: r["seed"])
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 6.0), sharey=True, gridspec_kw={"width_ratios": [1.45, 1]})
    y = np.arange(len(attacks))
    for ax, before, after, xlabel in [(axes[0], "pre_actual_trigger_asr", "post_actual_trigger_asr", "실제 평가 패턴 ASR (%)"),
                                      (axes[1], "pre_clean_accuracy", "post_clean_accuracy", "정상 정확도 (%)")]:
        for i, r in enumerate(attacks):
            ax.plot([100*r[before], 100*r[after]], [i, i], c=red if not r["flag"] else "#A4AAB0", lw=2)
        ax.scatter([100*r[before] for r in attacks], y, c=blue, s=42, zorder=3, label="삭제 전")
        ax.scatter([100*r[after] for r in attacks], y, c=red, s=42, zorder=3, label="잔류 자료 재학습 후")
        ax.set_xlabel(xlabel); ax.grid(axis="x", alpha=.18)
    axes[0].set_yticks(y, [f"{r['seed']} / {int(r['dominant_class_fraction']*100)}%" + ("  [미탐]" if not r["flag"] else "") for r in attacks])
    axes[0].invert_yaxis(); axes[0].set_xlim(-2, 103); axes[1].set_xlim(50, 73)
    axes[0].set_title("공격 10건: 삭제 전 1.44–17.33% → 삭제 후 88.22–99.67%")
    axes[1].set_title("같은 모델의 정상 정확도")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, -.045), ncol=2, frameon=False, fontsize=9)
    fig.text(.5, -.075, "각 행은 같은 공격 요청의 전후 모델이다. 1005는 ASR이 13.72%→99.61%로 올랐지만 탐지 점수가 기준에 미달했다.", ha="center", fontsize=9, color=gray)
    fig.tight_layout(); save(fig, "04_attack_before_after")


def patch_catalog_update(item, summary):
    item.update(status="중간 결과 고정 · 2026-10-19 16:58 KST · 70/210건",
                verdict="공격 9/10건 탐지, 대조 2/60건 오탐. 90% Non-IID에서 오탐 두 건이 발생했다.",
                result=table(["기본 두 클래스 비중", "공격 탐지", "대조 오탐"],
                             [[f"{int(level*100)}%", f"{c['true_positives']}/{c['attacks']}", f"{c['false_positives']}/{c['controls']}"]
                              for level in LEVELS for c in [summary["by_non_iid"][str(level)]]]),
                validation="고정된 70건의 저장 출력에서 개발 후보와 검증 점수를 다시 계산했다.",
                limit="고정 패치 계열·타깃 0·완료 10조건의 중간 결과다. 추가 순수 정상 삭제 스트레스 실험에는 이 패치 검사를 적용하지 않았다.")
    paths = [p for p in EVIDENCE.iterdir() if p.is_file()]
    paths += list(FIGURES.glob("*.png")) + list(FIGURES.glob("*.pdf"))
    paths += [Path(__file__)]
    paths += [REPO / "research_20261019/patch_scale_v1" / rel for rel in read(EVIDENCE / "protocol.json")["source_hashes"]]
    item["evidence"] = [p.relative_to(REPO).as_posix() for p in sorted(paths)]


def render_report(rows, summary):
    by_level = []
    for level in LEVELS:
        c = summary["by_non_iid"][str(level)]
        by_level.append([f"{int(level*100)}%", f"{c['requests']//7}/10", c["requests"],
                         f"{c['true_positives']}/{c['attacks']}", f"{c['false_positives']}/{c['controls']}"])
    by_level.append(["전체", "10/30", 70, "9/10 (90.0%)", "2/60 (3.3%)"])
    requests = []
    for name, label in LABELS.items():
        values = [r for r in rows if r["request"] == name]
        requests.append([label, f"{sum(r['flag'] for r in values)}/10",
                         f"{min(r['score'] for r in values):.6f}–{max(r['score'] for r in values):.6f}",
                         f"{100*min(r['post_actual_trigger_asr'] for r in values):.2f}–{100*max(r['post_actual_trigger_asr'] for r in values):.2f}%"])
    exceptions = []
    for r in summary["exceptions"]:
        exceptions.append(["미탐" if r["construction_attack"] else "오탐", f"{r['seed']} / {int(r['dominant_class_fraction']*100)}%",
                           LABELS[r["request"]], f"{r['score']:.6f}",
                           f"{100*r['pre_actual_trigger_asr']:.2f}→{100*r['post_actual_trigger_asr']:.2f}%",
                           f"{100*r['pre_clean_accuracy']:.2f}→{100*r['post_clean_accuracy']:.2f}%"])
    audit = []
    for r in sorted(rows, key=lambda r: (r["seed"], list(LABELS).index(r["request"]))):
        audit.append([f"{r['seed']} / {int(r['dominant_class_fraction']*100)}%", r["request"],
                      f"{r['score']:.6f}", "경보" if r["flag"] else "통과",
                      f"{100*r['pre_actual_trigger_asr']:.2f}→{100*r['post_actual_trigger_asr']:.2f}%"])
    body = r"""# D26 — 고정 패치 탐지는 Non-IID에서 위험한 삭제 요청을 구별하는가?

**중간 판정:** 완료 70건에서 공격 **9/10건을 탐지**했고, 대조 요청 **2/60건을 오탐**했다. 70% 조건의 완료 사례는 모두 구별했지만, 20% 조건에서 공격 한 건을 놓쳤고 90% 조건에서 대조 두 건을 공격으로 판정했다. **Non-IID 전체에서 완전히 구별됐다고 결론 내릴 수 없다.**

**보고 범위:** 2026년 10월 19일 **16:58 KST**까지 완료된 10조건·70요청. 전체 계획은 30조건·210요청이다. 이후 완료되는 결과와 섞지 않고 이 시점의 결과를 보존했다. 이 리포트는 패치 탐지 실험 하나를 다룬다.

## 가설 한 줄

유지·삭제 복제 모델의 패치 반응을 함께 비교하면, 정상 클래스 편향이 큰 상황에서도 백도어를 활성화하는 삭제 요청을 구별할 수 있다.

## 실험 한 줄

10개 새 시드 × 기본 두 클래스 비중 20/70/90% × 삭제 요청 7종을 구성하고, 삭제 후 잔류 자료로 40라운드 재학습한 실제 결과와 사전에 고정한 패치 탐지 판정을 비교했다.

## 실행 한 줄

```powershell
.\pr_reports\run.ps1 D26 -Action Run
```

저장소 루트의 PowerShell에서 실행한다. DISLAB의 진행 중인 같은 작업을 확인하고, 중단된 미완료 작업은 같은 설정으로 이어서 실행한다. 실행 중인 배치를 중복 생성하지 않는다. **새 초기화로 별도 210건을 시작하는 명령은 아니다.**

보고서·그래프를 이 70건으로 다시 만들려면 `python .\pr_reports\build_patch_report.py`를 실행한다. NumPy·Matplotlib이 필요하며 GPU 학습과 네트워크 접속은 수행하지 않는다. 원본 행과 점수 재계산 검증도 함께 갱신한다.

## 무엇을 비교했는가

요청마다 원본 모델 $	heta_0$를 복제해 **남길 자료 $R$로 학습한 모델 $	heta_R$**과 **지울 자료 $F$로 학습한 모델 $	heta_F$**를 만든다. 두 복제 모델 모두 해당 자료의 정답 라벨로 일반적인 손실 감소 학습을 한다. $	heta_F$는 삭제를 수행한 모델이 아니라 삭제 자료에 대한 반응을 보는 진단 모델이다.

세 모델에 같은 정상 이미지와 같은 패치 이미지를 넣어 **패치가 특정 클래스의 예측 확률을 얼마나 더 높이는지** 비교한다. 탐지 판정을 먼저 파일에 고정한 뒤, 잔류 자료만으로 처음부터 다시 학습한 모델의 실제 ASR을 평가한다. 100스텝 복제 진단과 40라운드 잔류 자료 재학습은 목적과 설정이 다르다.

## 데이터와 Non-IID 조건

| 항목 | 고정한 설정 |
|---|---|
| 자료·모델 | CIFAR-10, ResNet18, 클래스 10개 |
| 초기화 | ImageNet 사전학습 가중치를 불러온 뒤 첫 Conv를 3×3/stride 1, maxpool을 Identity, FC를 512→10으로 교체 |
| 입력 | 32×32 RGB, 0–1 범위. 평균 (0.4914, 0.4822, 0.4465), 표준편차 (0.2023, 0.1994, 0.2010)로 정규화 |
| 기본 자료 | 총 6,000장, 클래스당 600장. 클라이언트 5명, 각 1,200장 |
| 분포 조건 | 각 클라이언트에 지정한 두 클래스의 합계 비중 20%, 70%, 90% |
| 새 시드 | 1001–1010. 같은 시드의 분포 조건들은 자료·초기화를 공유하도록 설계 |
| 공격자·요청자 | 클라이언트 0. 나머지 네 클라이언트는 기본 자료 유지 |
| 실제 공격 패턴 | 오른쪽 아래 4×4 RGB 무작위 패턴, 생성 시드 20261018 고정 |
| 실제 공격 타깃 | 클래스 0 고정. 탐지 후보 선택은 10개 클래스를 모두 검색 |

분포 비중은 공격 자료 등을 추가하기 **전의 기본 1,200장**에 대한 값이다. 클라이언트 0의 기본 라벨별 장수는 다음과 같다. 다른 클라이언트에도 각자 지정한 클래스 쌍을 같은 방식으로 배분한다.

| 기본 두 클래스 비중 | 클래스 0·1 각각 | 나머지 8개 클래스 각각 | 의미 |
|---|---|---|---|
| 20% | 120장 | 120장 | 기본 자료는 클래스 균등 |
| 70% | 420장 | 45장 | 두 클래스에 집중 |
| 90% | 540장 | 15장 | 더 강한 클래스 편향 |

추가 자료를 붙이면 요청자의 최종 라벨 비중은 이 값과 달라진다. 여기서 “90% 조건”은 모든 학습 자료의 90%가 두 클래스라는 뜻이 아니다.

## 삭제 요청 7종: 무엇을 남기고 무엇을 지웠는가

$B$: 요청자의 정상 기본 자료 1,200장. $P$: 원래 정답이 0이 아닌 이미지에 실제 패턴을 넣고 라벨을 0으로 바꾼 독성 자료 180장. $C$: 같은 실제 패턴을 넣되 원래 정답 라벨을 유지한 억제 자료 720장. $Q$: 패치 없는 정상 클래스 0 자료 180장. $N$: $P$와 같은 원본 이미지에 패치를 넣지 않고 라벨만 0으로 바꾼 오라벨 자료 180장이다.

| 요청 / 코드 이름 | 삭제 전 요청자 자료 | 남기는 $R$ | 삭제하는 $F$ | 비교 목적 |
|---|---|---|---|---|
| 공격 / `attack_delete_cover` | $B+P+C$ | $B+P$: 1,380장 | $C$: 720장 | 독성을 남기고 억제만 제거 |
| 같은 크기 안전 삭제 / `equal_size_safe` | $B+P+C$ | $B+C_{180}$: 1,380장 | $P+C_{540}$: 720장 | 공격과 유지·삭제 장수 동일, 독성 제거 |
| 독성 삭제 / `delete_poison` | $B+P+C$ | $B+C$: 1,920장 | $P$: 180장 | 독성만 제거 |
| 양쪽 삭제 / `delete_both` | $B+P+C$ | $B$: 1,200장 | $P+C$: 900장 | 독성·억제 모두 제거 |
| 정상 클래스 편향 / `benign_class_prior` | $B+Q+C$ | $B+Q$: 1,380장 | $C$: 720장 | 독성 대신 정상 클래스 0 추가 |
| 오라벨 / `label_noise` | $B+N+C$ | $B+N$: 1,380장 | $C$: 720장 | 독성 대신 패치 없는 오라벨 추가 |
| 정답 패치 삭제 / `normal_cover` | $B+C$ | $B$: 1,200장 | $C$: 720장 | 타깃 라벨 독성을 심지 않은 조건 |

**대조 6종은 모두 원본 이미지로만 구성한 순수 정상 클라이언트 전체 삭제가 아니다.** 특히 `normal_cover`에도 정답 라벨을 붙인 패치 자료 $C$가 들어간다. 이 구성을 빼고 “일반적인 Non-IID 정상 삭제에서 오탐 3.3%”라고 일반화하면 안 된다.

## 학습·진단·평가 설정

| 구분 | 설정 |
|---|---|
| 삭제 전 모델 학습 | FedAvg 40라운드, 매 라운드 5명 모두 참여, 클라이언트 자료 장수로 가중 평균 |
| 클라이언트 학습 | 매 라운드 1 epoch, batch 64, SGD 학습률 0.01, momentum·weight decay 없음, 증강 없음, 전체 네트워크 학습 |
| 삭제 후 기준 모델 | 해당 $R$과 나머지 4명 자료로 같은 초기화에서 40라운드 재학습. 1스텝 근사 언러닝 결과가 아님 |
| 복제 진단 | $	heta_R,	heta_F$ 각각 100 SGD 스텝, 학습률 0.01, batch 32, 복원 추출 |
| 복제 학습 범위 | `layer4`만 갱신. FC·다른 블록 고정. BN은 eval로 통계 고정 |
| 복제 제약 | gradient norm clipping 1.0, 정상 기준 자료 500장에 대한 KL 가중치 2.0 |
| 공통 조건 | 두 복제 분기는 같은 난수 스트림과 같은 정상 기준 자료 사용 |
| 탐지 입력 | 개발용 정상 200장 + 검증용 정상 200장, 각각 클래스당 20장. 기준 500장과 학습 자료에서 분리 |
| 패치 후보 | 4개 모서리 × 8종 = 32개. 모서리마다 검정·흰색·체커·역체커·무작위 4개, 크기 4×4 |
| 후보 패턴 난수 | 시드 919191. 실제 공격 패턴의 시드 20261018과 별도 |
| 후보 선택 | 개발 자료에서 32패턴 × 10타깃 검색. 선택한 한 후보만 검증 자료로 판정 |
| 판정 기준 | $S>0.006$ 고정. 새 결과를 보고 임계값 변경·입력 최적화하지 않음 |
| 실제 성능 평가 | 공식 시험 자료 2,000장, 클래스당 200장. 타깃 0 원본 제외 1,800장으로 ASR 측정 |

**정상 이미지가 필요한 방법이다.** 정상 기준 500장과 별도 탐지용 400장을 사용한다. 현재 구현은 DISLAB에서 유지·삭제 원본 자료도 읽어 복제 모델을 학습한다. 두 그래디언트만 서버에 보내는 배포 방식까지 검증한 실험은 아니다. 실제 공격 패턴은 평가에만 사용하고 탐지 점수에는 주지 않지만, 탐지기는 4×4 모서리 패치 계열을 가정한다.

## 실제로 사용한 수식

### 1. 두 복제 모델을 만드는 손실

원본 모델은 $	heta_0$, 정상 기준 자료는 $A$, $p_\theta(c\mid x)$는 클래스 $c$의 softmax 확률이다. 두 분기는 각각 $D=R$, $D=F$에 대해 아래 손실을 줄인다.

$$
\mathcal L_D(\theta)
= \frac{1}{|D|}\sum_{(x,y)\in D}\operatorname{CE}(p_\theta(\cdot\mid x),y)
+2\frac{1}{|A|}\sum_{a\in A}
\operatorname{KL}\!\left(p_{\theta_0}(\cdot\mid a)\,\|\,p_\theta(\cdot\mid a)\right),
\qquad D\in\{R,F\}.
$$

각 스텝에서는 $D$와 $A$에서 32장씩 뽑아 계산한다. **CE는 해당 자료의 라벨을 학습하고, KL은 정상 기준 이미지에서 원본 출력과 멀어지는 것을 제한한다.** 두 분기 모두 양의 CE를 최소화한다.

### 2. 패치 자체가 더한 반응

$T_\delta x$는 이미지 $x$의 지정 위치를 패턴 $\delta$로 바꾼 입력이다. 후보 타깃 $t$와 원래 정답이 다른 이미지들만 사용한다. $Q$는 개발 또는 검증 자료다.

$$
r_\theta^Q(\delta,t)
=\frac{1}{|Q_{\ne t}|}\sum_{(x,y)\in Q_{\ne t}}
\left[p_\theta(t\mid T_\delta x)-p_\theta(t\mid x)\right],
\qquad Q_{\ne t}=\{(x,y)\in Q:y\ne t\}.
$$

개발·검증 각각 200장 중 후보 타깃 클래스 20장을 빼므로, 후보마다 180장이 들어간다. **패치 입력의 타깃 확률에서 원본 입력의 타깃 확률을 뺀다.** ASR이나 로짓 값 자체를 탐지 점수로 쓰는 것이 아니다.

### 3. 개발 자료에서 후보를 고르고 검증 자료에서 고정 판정

$$
(\hat\delta,\hat t)=\operatorname*{argmax}_{\delta,t}
\left[r_{\theta_R}^{\mathrm{dev}}(\delta,t)-r_{\theta_0}^{\mathrm{dev}}(\delta,t)\right].
$$

이 후보 하나를 그대로 검증 자료로 넘겨 아래 두 값을 계산한다.

$$
a=r_{\theta_R}^{\mathrm{val}}(\hat\delta,\hat t)-r_{\theta_0}^{\mathrm{val}}(\hat\delta,\hat t),
\qquad
b=r_{\theta_R}^{\mathrm{val}}(\hat\delta,\hat t)-r_{\theta_F}^{\mathrm{val}}(\hat\delta,\hat t).
$$

$$
S=\max\{0,\min(a,b)\},\qquad
\mathrm{alarm}=\mathbf1[S>0.006].
$$

**의미:** 유지 분기의 패치 반응이 원본보다 커지고($a$), 동시에 삭제 분기보다도 커져야($b$) 경보를 낸다. 기준 0.006은 평균 예측 확률의 **0.6%p** 차이다. 공격 성공률 0.6%를 뜻하지 않는다. 검증 자료에서 점수가 가장 좋은 패치를 다시 고르지 않는다.

### 4. 일반적인 클래스 변화와 어떻게 구별하려는가

$d_R(x)=p_{\theta_R}(t\mid x)-p_{\theta_0}(t\mid x)$로 쓰면,

$$
a=\mathbb E_{x\in Q_{\ne\hat t}^{\mathrm{val}}}
\left[d_R(T_{\hat\delta}x)-d_R(x)\right].
$$

유지 분기 학습으로 타깃 확률이 올라가더라도 원본 입력과 패치 입력에서 똑같이 올라가면 이 차이는 0이다. 그래서 단순한 클래스 확률 상승보다 **입력에 패치를 넣었을 때 추가로 발생하는 변화**를 측정한다. 삭제 분기와의 비교 $b$도 같은 방식이다.

다만 Non-IID에 의한 변화가 두 입력에서 같다는 보장은 없다. **이 수식이 모든 Non-IID 효과를 제거한다는 증명은 없으며, 이번 90% 조건에서 실제 오탐도 나왔다.**

### 5. 실제 삭제 후 ASR과 정상 정확도

평가용 실제 패턴을 $\tau$, 실제 타깃을 0으로 고정한다.

$$
\operatorname{ASR}(\theta)=\frac{1}{1800}\sum_{i:y_i\ne0}
\mathbf1\!\left[\operatorname*{argmax}_c p_\theta(c\mid T_\tau x_i)=0\right].
$$

정상 정확도는 패치 없는 시험 이미지 2,000장 전체에서 정답 비율로 계산한다. 공격을 심지 않은 대조에도 같은 평가 패턴을 넣을 수 있다. 그때 나오는 값은 **해당 패턴의 타깃 오분류율**이며 공격자가 존재했다는 뜻은 아니다.

## 결과 1 — 분포 조건별 탐지

{{BY_LEVEL}}

![분포 조건별 패치 탐지 점수와 고정 임계값](../figures/D26/01_score_by_skew.png)

**그림 1.** 점 하나는 완료된 요청 하나다. 70%에서는 완료된 공격·대조가 구별됐다. 20%의 공격 한 건은 점수가 0.006에 못 미쳤다. 90%에서는 대조 두 건이 0.006을 넘었다. 이 중간 결과의 비율은 독립적인 다수 시드의 확정 성능 추정치가 아니다.

## 결과 2 — 무엇을 위험하다고 판정했는가

{{BY_REQUEST}}

경보 건수는 공격 행에서는 탐지 건수, 나머지 행에서는 오탐 건수다. 마지막 열은 공격 행에서는 ASR, 대조 행에서는 같은 평가 패턴의 타깃 오분류율이다.

![패치 탐지 점수와 실제 삭제 후 타깃 오분류율 변화](../figures/D26/02_score_vs_outcome.png)

**그림 2.** 공격 10건의 실제 ASR 상승은 모두 82%p 이상이었지만 탐지기는 한 건을 놓쳤다. 대조 60건 중에도 패치 점수가 높아진 두 건이 있었다. 따라서 **탐지 점수는 실제 ASR의 직접 측정값이나 동일한 척도가 아니다.**

## 결과 3 — 삭제 분기와의 비교가 실제로 도움이 됐는가

같은 개발 후보와 같은 임계값에서 $a>0.006$만 적용하면 대조 **11/60건**에 경보가 난다. $a,b$를 모두 요구하는 현재 식은 대조 **2/60건**에 경보를 냈다. 두 방식의 공격 탐지는 모두 **9/10건**이었다.

![두 분기 판정 조건과 유지 분기만 사용할 때의 경보 건수](../figures/D26/03_two_branch_comparison.png)

**그림 3.** 왼쪽의 점 하나는 같은 요청의 $(a,b)$다. 두 값이 모두 기준을 넘는 영역에서 경보를 낸다. 오른쪽은 같은 저장 출력에서 계산한 비교로, 삭제 분기 $b$를 추가했을 때 대조 경보가 9건 줄었다. 새 학습을 서로 다르게 수행한 비교가 아니다.

## 결과 4 — 공격 요청의 실제 전후 성능

![공격 10건의 삭제 전후 ASR 및 정상 정확도](../figures/D26/04_attack_before_after.png)

**그림 4.** 공격 삭제 후 실제 ASR은 **88.22–99.67%**였다. 같은 모델의 정상 정확도와 함께 보면, 정상 정확도만으로 타깃 패턴에 대한 위험을 판단하기 어렵다는 점을 확인할 수 있다. 이 결과는 여기서 사용한 자료·학습 조건에 대한 관측이다.

## 반드시 남겨야 하는 실패 사례

{{EXCEPTIONS}}

- **1005 / 20% 미탐:** $a=0.005454$, $b=0.014224$여서 작은 값 $a$가 기준에 못 미쳤다. 실제 ASR은 13.72%→99.61%로 상승했다. 왜 이 시드의 반응 증가가 작았는지에 대한 추가 원인 실험은 하지 않았다.
- **1009 / 90% 오라벨 오탐:** $a=0.020202$, $b=0.013516$으로 둘 다 기준을 넘었다. 실제 평가 패턴의 타깃 오분류율은 0.00%→8.83%였다. 패치 없는 오라벨 추가 조건에서도 현재 점수가 커질 수 있다.
- **1009 / 90% 정답 패치 삭제 오탐:** $a=0.009712$, $b=0.008483$으로 둘 다 기준을 넘었다. 타깃 라벨 독성을 심지 않았는데도 경보가 났으며, 평가 패턴 오분류율은 0.06%→5.22%였다.

보조 집계로, 사전 기준 **삭제 전 ASR≤10%, 삭제 후 ASR≥50%, 상승≥30%p**를 모두 만족한 잠복 활성화 사례는 7건이고 7건 모두 탐지했다. 그러나 삭제 전 ASR이 10%를 넘는 공격 구성 3건도 주 집계에 그대로 남겼다. **7/7만 제시해 미탐 1건을 제외하지 않는다.**

## 현재 결론과 남은 검증 범위

**이 설정에서는 공격을 대체로 구별했고, 유지 분기만 보는 것보다 삭제 분기를 함께 보는 것이 대조 경보를 줄였다.** 다만 강한 편향에서의 오탐과 균등 기본 분포에서의 미탐이 확인됐다. 현재 식을 Non-IID 전반의 완전한 구별 방법으로 확정할 수 없다.

- 전체 210건 중 70건만 완료했다. 완료 분포는 20% 3시드, 70% 4시드, 90% 3시드로 아직 동일 시드의 3수준 짝 비교가 다 채워지지 않았다.
- 요청 7종은 같은 학습 조건과 자료를 공유한다. 70개 요청을 70개의 독립 학습 시드로 세지 않는다.
- 실제 공격은 타깃 0, 같은 4×4 오른쪽 아래 패턴 하나로 고정했다. 다른 위치·크기·타깃·공격 계열로의 일반화는 이 결과에서 확인하지 않았다.
- 쉽게 맞히는 정상 자료를 많이 지우는 별도 스트레스 실험에는 아직 이 패치 검사를 적용하지 않았다. 그 조건에서도 오탐이 없다고 말할 수 없다.
- CIFAR-10 일부 자료를 쓴 조정된 학습 설정이다. BadFU 저자 코드 전체 재현이나 최종 서비스의 거부·전체 삭제 정책을 검증한 결과로 해석하지 않는다.

## 검증과 근거

완료된 원본 70행을 DISLAB에서 가져오고, 보존된 출력으로부터 계산한 32패턴×10클래스 반응을 이용해 **개발 후보 선택 70건과 검증 점수 70건을 다시 계산**했다. 수식의 $a,b,S$와 저장 값의 최대 절대 오차는 **{{MAX_ERROR}}**다. 임계값은 전부 0.006, 해당 삭제 후 모델이 생성되기 전에 판정이 고정됐다는 기록도 70건 확인했다. 원본 판정 파일의 SHA256도 원격 읽기 단계에서 모두 대조했다.

| 파일 | 용도 |
|---|---|
| [protocol.json](../evidence/patch_interim_20261019_1658/protocol.json) | 학습·분포·탐지·평가 설정과 고정 소스 해시 |
| [results.csv](../evidence/patch_interim_20261019_1658/results.csv) | 완료 70건의 점수·후보·유지/삭제 장수·전후 성능 |
| [results.json](../evidence/patch_interim_20261019_1658/results.json) | 위 수치와 체크포인트·판정 파일 해시, 완료 시각 |
| [summary.json](../evidence/patch_interim_20261019_1658/summary.json) | 분포별·요청별 집계와 세 실패 사례 |
| [probe_responses.json](../evidence/patch_interim_20261019_1658/probe_responses.json) | 저장 로짓에서 줄인 패턴 반응 배열. 모든 후보와 점수 재계산 가능 |
| [VALIDATION.json](../evidence/patch_interim_20261019_1658/VALIDATION.json) | 수식·후보·임계값·소스 해시 대조 결과 |
| [scale_patch_experiment.py](../../research_20261019/patch_scale_v1/sources/scale_patch_experiment.py) | 실행한 학습·복제·탐지·평가 구현 |
| [probe_information.py](../../research_20261019/patch_scale_v1/sources/reference/probe_information.py) | 고정 패치 은행과 확률 반응 계산 |
| [build_patch_report.py](../build_patch_report.py) | 이 리포트의 수치 검증·그래프·본문 생성 |

프로토콜 SHA256: `bfc1f78230b943c0c8c03ac11b3881abdb085788a2d5c5910a379fc7b0c58200`.

인쇄용 벡터 그래프: [분포별 점수](../figures/D26/01_score_by_skew.pdf), [점수와 실제 변화](../figures/D26/02_score_vs_outcome.pdf), [두 분기 비교](../figures/D26/03_two_branch_comparison.pdf), [공격 전후 성능](../figures/D26/04_attack_before_after.pdf).

## 부록 — 완료 70건의 개별 판정

표시한 점수는 소수 여섯째 자리로 반올림했다. 판정은 반올림 전 값과 엄격 부등호 $S>0.006$으로 계산했다. 원래 정밀도는 CSV/JSON에 보존했다.

{{AUDIT}}
"""
    replacements = {
        "{{BY_LEVEL}}": table(["기본 두 클래스 비중", "완료 조건", "평가 요청", "공격 탐지", "대조 오탐"], by_level),
        "{{BY_REQUEST}}": table(["요청", "경보", "점수 범위", "실제 삭제 후 타깃 오분류율"], requests),
        "{{EXCEPTIONS}}": table(["종류", "시드 / 비중", "요청", "점수", "전후 ASR / 패턴 오분류율", "전후 정상 정확도"], exceptions),
        "{{MAX_ERROR}}": f"{read(EVIDENCE / 'VALIDATION.json')['max_absolute_score_component_error']:.1e}",
        "{{AUDIT}}": table(["시드 / 비중", "요청", "탐지 점수", "판정", "전후 ASR / 패턴 오분류율"], audit),
    }
    for before, after in replacements.items():
        body = body.replace(before, after)
    assert "{{" not in body
    return body


def prepare():
    rows, summary = validate_and_summarize()
    make_figures(rows, summary)
    return rows, summary


if __name__ == "__main__":
    # The catalog builder calls prepare() and the rich renderer for D26.
    from build_reports import build
    build()
