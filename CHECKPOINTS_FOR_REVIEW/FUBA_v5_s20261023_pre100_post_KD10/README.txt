FUBA v5 / actual before100R → KD-based FU10 model pair

before_classifier.pt: original v5 round100 classifier, exact bytes.
after_unlearning.pt: actual historical-client4-subtraction followed by10KD epochs/400batches.
fixed_generator.pt: same sealed pre100R aggregate G, evaluation only; no trigger/G enters KD training.
Before CA78.58% / ASR28.68888888888889%.
After CA78.95% / ASR28.42222222222222%.
This is an actual KD-based FU pair. Pre-ASR failed, so this is NOT a validated stealth→activation reproduction.
Full10000/non-target9000 evaluation, epsilon.05,pixel[0,1],eval,contiguous NCHW, sameG.
PROTOCOL.txt states source/paper corrections: actual client IDs/weights,10KD,clean unlabeled data,teacher.eval,BN policy, no post-hoc generator fitting. Not untouched author code or all six FU methods.
All10 round bundles contain model/optimizer/RNG. events.jsonl and console.log preserve the training/deletion/evaluation trace. Original100R history remains at D:/FUBA_PAPER_COMPLETION_20261024/attack_100R.
External manifest/seal and local/remote CPU checks are in the separate delivery proof. Prior sealed pre100R remains unchanged.
