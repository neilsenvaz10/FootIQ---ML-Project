# 01 Frozen model integrity verification

Executed by `_scripts/e1_integrity_and_identity.py` at the start of this work; table `01_frozen_model_integrity.csv` (12/12 pass).

* Frozen v2-r1 candidate `club_v2_lr_final_candidate.pkl` = `55c1e4c53bcfefd39d5e90a1ce60a75bc697668f7894e425305bdc9a65b3e56c` — **matches the hash quoted in the instruction**; `feature_contract_v2_final.json` and `model_coefficients.json` (the fitted preprocessing lives inside the pickle and in the contract JSON) match `FROZEN.json`.
* The v2-r1 training feature table and dataset v1.1 match their recorded hashes.
* Original v1 artifacts (`multinomial_logreg.pkl` plus the four JSON artifacts) match the v1 `FROZEN.json` (the JSON files compared after CRLF normalisation because git's `autocrlf` rewrote their line endings; the pickle is byte-identical).
* The international World Cup model `v27/live_match_model.pkl` is unchanged against the hash recorded in the previous step.
* Nothing in this work retrains, recalibrates, overwrites or edits the frozen v2 candidate or v1; the logger re-verifies these hashes before every prediction batch (`verify_models()` in `e4_prospective_logger.py`), and the files remain read-only.
