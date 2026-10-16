# Perfect performance sanity check



All checks use Development only. Every saved model-matrix row and target was reconstructed from raw rows at steps 1–400; arrays were not rewritten. Train steps 1–320 and Validation steps 321–400 are strictly disjoint.

## Leakage evidence

{
  "verified_rows": {
    "train": 4388788,
    "validation": 1398242
  },
  "exact_reconstruction": true,
  "prohibited_column_mutation_invariant": true,
  "train_steps": [
    1,
    320
  ],
  "validation_steps": [
    321,
    400
  ],
  "shared_rows": false,
  "shared_rows_evidence": "Strictly disjoint step values; exact rows include step; Phase 1 found no exact duplicates",
  "production_used": false,
  "feature_names": [
    "step",
    "amount",
    "oldbalanceOrg",
    "oldbalanceDest",
    "amount_to_oldbalanceOrg",
    "orig_balance_zero",
    "orig_balance_emptied",
    "dest_is_merchant",
    "type_CASH_IN",
    "type_CASH_OUT",
    "type_DEBIT",
    "type_PAYMENT",
    "type_TRANSFER",
    "type_UNKNOWN"
  ],
  "preprocessing_review": "Row-local features have no fit; logistic StandardScaler fitted by Pipeline on Train only",
  "matrix_sha256": {
    "train_X.npy": "4a74d6444772904aa01e524e178627c1e4c5b6efb8443c5da7870cd0a8da16e9",
    "train_y.npy": "d6500bdffc2eb7fdb7a93fe92ee66224e48305c88adc8a935a917a3351239647",
    "validation_X.npy": "dc1066ec7f9d3cd8cea756c9dc4ae6b7d5dd94b7d7e2a9f8b1344cab3bcfb2dd",
    "validation_y.npy": "32f5950840801da44ba733ced3aa5b7b1b52ff463cc8e21ad6d677479c19cb29"
  },
  "phase2_source_sha256": {
    "src/fraud_detection/features.py": "73badebaa186e2fc323fd6c46de784b5002c380dca7ac360a70f7a9a32c0f28a",
    "src/fraud_detection/modeling.py": "e14378a4b51691ef03bdebc45c7018a83a2ce1832d503c19544c8d4d7e69cfc3",
    "scripts/run_baselines.py": "214fdac476209b002446ba32222f442df65a3f4c0b0c8600f745667583d860e6",
    "PHASE_2_MODELING_REPORT.md": "d95c8e5fdcd5573e9a9754db22bf74e84e81ae33dc5d52a1ef66fe0dc917ab9b"
  },
  "all_fraud_development_steps": 137,
  "all_fraud_step_transactions": 1524,
  "seconds": 61.56280160000097,
  "conclusion": "B: No implementation leakage detected; near-deterministic simulator patterns. C: Operational availability and external validity remain uncertain."
}

The fixed MODEL_COLUMNS list excludes isFraud, isFlaggedFraud, raw IDs, new balances and every post-event derivative. Raw reconstruction confirms columns were not replaced by accidental target-derived data. Mutating labels, flags, post-event balances and IDs (preserving only destination prefix) leaves features identical. Source review confirms no fitted transformer spans Train and Validation. This provides evidence against implementation leakage, not proof that the simulator contains no target-related shortcuts.

## Univariate separation

Both high and low score directions are reported descriptively. AP for binary features is based on only two score groups and is not equivalent to precision among positive-feature rows. Constant features return prevalence AP and ROC 0.5. These checks do not select or remove model predictors.

| segment | feature | pr_auc_high | pr_auc_low | roc_auc_high |
| --- | --- | --- | --- | --- |
| train | step | 0.02113342 | 0.00104179 | 0.46204322 |
| train | amount | 0.01309433 | 0.00130569 | 0.78350650 |
| train | oldbalanceOrg | 0.00214300 | 0.00047405 | 0.80300810 |
| train | oldbalanceDest | 0.00067205 | 0.00119398 | 0.36681187 |
| train | amount_to_oldbalanceOrg | 0.00260020 | 0.00116140 | 0.68857726 |
| train | orig_balance_zero | 0.00081609 | 0.00121758 | 0.33796384 |
| train | orig_balance_emptied | 0.97868185 | 0.00080537 | 0.98947065 |
| train | dest_is_merchant | 0.00082232 | 0.00124161 | 0.33101328 |
| train | type_CASH_IN | 0.00082232 | 0.00105278 | 0.39045647 |
| train | type_CASH_OUT | 0.00099498 | 0.00072848 | 0.57410970 |
| train | type_DEBIT | 0.00082232 | 0.00082744 | 0.49690606 |
| train | type_PAYMENT | 0.00082232 | 0.00124161 | 0.33101328 |
| train | type_TRANSFER | 0.00287368 | 0.00063547 | 0.70751449 |
| train | type_UNKNOWN | 0.00082232 | 0.00082232 | 0.50000000 |
| validation | step | 0.00068204 | 0.00054489 | 0.54252289 |
| validation | amount | 0.00668282 | 0.00151457 | 0.78445063 |
| validation | oldbalanceOrg | 0.00401586 | 0.00035467 | 0.81948373 |
| validation | oldbalanceDest | 0.00051752 | 0.00090464 | 0.36830634 |
| validation | amount_to_oldbalanceOrg | 0.00189616 | 0.00089605 | 0.67853368 |
| validation | orig_balance_zero | 0.00062007 | 0.00093753 | 0.33103338 |
| validation | orig_balance_emptied | 0.98157826 | 0.00060955 | 0.99078341 |
| validation | dest_is_merchant | 0.00062078 | 0.00093203 | 0.33292340 |
| validation | type_CASH_IN | 0.00062078 | 0.00079808 | 0.38885188 |
| validation | type_CASH_OUT | 0.00075134 | 0.00054987 | 0.57406857 |
| validation | type_DEBIT | 0.00062078 | 0.00062524 | 0.49642866 |
| validation | type_PAYMENT | 0.00062078 | 0.00093203 | 0.33292340 |
| validation | type_TRANSFER | 0.00214046 | 0.00047997 | 0.70772749 |
| validation | type_UNKNOWN | 0.00062078 | 0.00062078 | 0.50000000 |

## Simple rules

Rules use fixed tolerances from Phase 2 and no learned thresholds. The ratio check uses a prespecified 1e-6 diagnostic tolerance on stored float32; the emptied feature itself was computed from raw float64 with absolute monetary tolerance 0.01. Rules with incomplete recall or false positives explain most separation without being equivalent to the label.

| segment | rule | pr_auc | precision_05 | recall_05 | tp | fp | tn | fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | TRANSFER | 0.00287368 | 0.00494674 | 0.49736769 | 1795 | 361070 | 4024109 | 1814 |
| train | CASH_OUT | 0.00099498 | 0.00116583 | 0.50263231 | 1814 | 1554164 | 2831015 | 1795 |
| train | TRANSFER_or_CASH_OUT | 0.00188082 | 0.00188082 | 1.00000000 | 3609 | 1915234 | 2469945 | 0 |
| train | origin_zero | 0.00081609 | 0.00001924 | 0.00775838 | 28 | 1455137 | 2930042 | 3581 |
| train | amount_approximately_prior_balance | 0.97868185 | 0.99971703 | 0.97894154 | 3533 | 1 | 4385178 | 76 |
| train | ratio_approximately_one_positive_balance | 0.97895885 | 1.00000000 | 0.97894154 | 3533 | 0 | 4385179 | 76 |
| train | risky_type_and_requested_emptying | 0.97895885 | 1.00000000 | 0.97894154 | 3533 | 0 | 4385179 | 76 |
| validation | TRANSFER | 0.00214046 | 0.00366013 | 0.50000000 | 434 | 118141 | 1279233 | 434 |
| validation | CASH_OUT | 0.00075134 | 0.00088190 | 0.50000000 | 434 | 491684 | 905690 | 434 |
| validation | TRANSFER_or_CASH_OUT | 0.00142134 | 0.00142134 | 1.00000000 | 868 | 609825 | 787549 | 0 |
| validation | origin_zero | 0.00062007 | 0.00000211 | 0.00115207 | 1 | 473829 | 923545 | 867 |
| validation | amount_approximately_prior_balance | 0.98157826 | 1.00000000 | 0.98156682 | 852 | 0 | 1397374 | 16 |
| validation | ratio_approximately_one_positive_balance | 0.98157826 | 1.00000000 | 0.98156682 | 852 | 0 | 1397374 | 16 |
| validation | risky_type_and_requested_emptying | 0.98157826 | 1.00000000 | 0.98156682 | 852 | 0 | 1397374 | 16 |

## Conclusion

A. No implementation evidence of direct target, business-rule, post-event, identifier or temporal leakage was detected.

B. Near-deterministic simulator patterns are present: requested account emptying and transaction type sharply separate the target. Low-volume steps can contain only fraud, adding a simulation scheduling shortcut. This explains why very high AP is plausible without prohibited predictors.

C. Pending uncertainty: pre-execution balance availability and merchant-prefix semantics in a real system; simulation label-generation mechanisms; single-holdout stability; external transferability and score calibration. A dataset-level generator shortcut cannot be ruled out by an implementation audit. Do not infer extraordinary real-world performance.

The same Validation will subsequently support tuning and early stopping as authorized. Its final scores will then be development-selection estimates, not independent unbiased test evidence. Production remains reserved.
