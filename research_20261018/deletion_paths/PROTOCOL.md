# Deletion paths beyond spatial patches: exploratory mechanism pilot

2026-10-18. Written before execution. This is a new screening experiment, not a reproduction of BadFU or a validated novel method.

Question: can two deletion orders have an identical safe final classifier while exposing very different risk at intermediate released models, even when every deletion is exact for the specified learner?

We intentionally change the research object from patch repair to the safety of the sequence of released models. Inputs use global color grading and global smooth texture, not a localized patch. These are synthetic styles, not evidence for natural semantic triggers.

Learner: externally pretrained, frozen ImageNet ResNet18 at 96px and a ridge least-squares 10-class head. The frozen encoder was not trained on this experiment's poison/camouflage data. The entire data-dependent trained component is the head. Retraining is exact up to numerical error for this convex learner only; no claim of FedAvg equivalence or full-network certified forgetting. Gram matrices can be aggregated across clients, but this pilot does not execute communication or FedAvg.

Data: CIFAR-10 official training split, 12,000 base examples, 3,000 disjoint role-pool examples, 2,000 disjoint validation examples. Test: 2,000 balanced examples from the official test split. Both synthetic-style operations preserve the original class by assumption. External weights, data arrays, split identities and code are hashed.

Seeds 11,22,33 choose 200 poison examples (non-target originals, relabeled to class 0) and 800 camouflage examples (original labels), disjoint within the role pool. Each is split into two requests: P0/P1/C0/C1. The requester roles are oracle annotations for diagnosis, not supplied as a decision rule. All 16 subsets of pending deletions are retrained; all 24 request orders finish at the identical base-data head. A normal-label control keeps the same image IDs and styles but does not relabel the poison examples.

One ridge penalty is selected per external-feature cache using only base-data validation accuracy, from {0.001,0.01,0.1,1,10}. All later states use this penalty. Objective is sum of squared errors plus the fixed penalty, avoiding implicit changes in regularization due to dataset size. Features are L2-normalized and appended with a constant. Bias is regularized.

Primary descriptive comparisons: start/end risk, camouflage-first and poison-first paths, range of peak risk over all orders, maximum single-request risk versus combined camouflage deletion. If dormancy or activation is weak, report that failure. We do not optimize the attack after examining test outcomes.

An exploratory queue rule selects the order with the lowest maximum validation wrong-class concentration across all prefixes. This uses labeled validation images with the same known global style, not attack-role labels or the target class. It assumes all four requests are already pending, legal processing order is flexible, and intermediate models may be released. It is an exhaustively solved four-request baseline, not a novel scalable scheduler. The test set never selects a schedule. Atomic batch release is a necessary baseline and avoids intermediate exposure if batching is allowed.

Novelty blockers already found: UBA-Inf has on-demand activation; UNCLEAN (arXiv:2506.12522) uses clean forget sets and global frequency triggers; deletion ordering (arXiv:2610.01149) studies order-dependent terminal objectives. Merely switching trigger type or showing that deleting camouflage before poison raises risk is not a new attack principle. A potential contribution would have to address path safety under realistic service constraints, with exact-retraining controls and a useful release/scheduling guarantee. This pilot can support only existence and magnitude in its controlled learner.
