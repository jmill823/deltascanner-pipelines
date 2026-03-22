# DeltaScanner Pipelines — Deviations Log

Document every deviation from the build spec here.

## Block 1: Scaffold + Configs

### Austin: Tax weight below 50% floor (CORRECTED)
- **Spec says:** Tax signals must account for >= 50% of composite score
- **Found:** Austin v2 had delinquency_amount at 40%
- **What I did:** Rebalanced to 50/30/20 per Jeff review 2026-03-21
- **Status:** Resolved

### Philadelphia: CE-only model (no tax data)
- **Spec says:** Intersection scoring requires both tax AND CE
- **Found:** Philly has no tax delinquency source (PRR pending)
- **What I did:** Configured as ce_only with `ce_only: true` bypass flag
- **Why:** Philly launched before tax data was available. Needs v3 upgrade when PRR arrives.

### Orlando: CE-only model (no tax data)
- **Spec says:** Intersection scoring requires both tax AND CE
- **Found:** Orlando has no tax delinquency source (PRR pending)
- **What I did:** Configured as ce_only with `ce_only: true` bypass flag
- **Why:** Orlando launched as violations-only. Needs v2 upgrade when PRR arrives.

### Fort Lauderdale: Only 2 scoring components (CORRECTED)
- **Spec says:** Minimum 3 score components
- **Found:** After recency removal, only 2 components remained
- **What I did:** Added delinquency_duration as 3rd component. Rebalanced to 45/15/40 per Jeff review.
- **Status:** Resolved

### Palm Beach: Union scoring in original script
- **Spec says:** Intersection only, never union
- **Found:** palmbeach_score.py uses union approach (tax OR CE parcel spine)
- **What I did:** Set config to intersection. Output count will differ from original.
- **Why:** Intersection is the non-negotiable rule. Palm Beach needs re-validation.

### Miami: Recency component removed (CORRECTED)
- **Spec says:** No freshness-based recency
- **Found:** Miami v1 had score_recency at 10% weight
- **What I did:** Removed recency. Redistributed to 50% duration / 40% amount / 10% active per Jeff review.
- **Status:** Resolved

## Block 2: Migration Validation

### Miami: Intersection scoring reduces parcel count from 17,153 to ~766
- **Before (v1):** 17,153 scored parcels using left join (all tax-delinquent parcels scored)
- **After (v2, intersection):** ~766 parcels (only those with BOTH tax delinquency AND active CE violations)
- **Why the drop:** Original model scored all tax-delinquent parcels; only 766/17,153 (4.5%) have active code violations in the CE system. This is correct behavior — intersection requires both signals.
- **Impact:** Deal flow list shrinks significantly. These 766 parcels are higher-conviction (dual distress signals).
- **Scoring math validated:** V1 weights replicate 17,153/17,153 within 0.1 pts. Normalization exact.

### Austin: Weight rebalancing shifts scores +5.4 mean
- **Before (v2):** Weights 40/35/25, mean score 33.5
- **After (pipelines):** Weights 50/30/20, mean score 38.9
- **Parcel count:** Unchanged (1,231 — already intersection)
- **Scoring math validated:** V2 weights replicate 1,231/1,231 within 0.1 pts.

### Miami: Config join_key field corrected
- **Spec YAML said:** `field: folio` (derived name)
- **Actual CSV column:** `field: "Account Number"` (raw column name with dashes)
- **What I did:** Updated config to use actual column name. Normalizer strips dashes to 13-digit folio.
- **Why:** The universal scorer looks up columns by name; the config must reference the actual CSV header.
