# DeltaScanner Pipelines — Deviations Log

Document every deviation from the build spec here.

## Block 1: Scaffold + Configs

### Austin: Tax weight below 50% floor
- **Spec says:** Tax signals must account for >= 50% of composite score
- **Found:** Austin v2 has delinquency_amount at 40%, with active_violations (35%) + violation_volume (25%) = 60% CE
- **What I did:** Documented current weights with flag for Jeff review
- **Why:** Austin v2 dropped recency and redistributed without meeting 50% floor. Needs rebalancing.

### Philadelphia: CE-only model (no tax data)
- **Spec says:** Intersection scoring requires both tax AND CE
- **Found:** Philly has no tax delinquency source (PRR pending). Model is violations-only.
- **What I did:** Configured as ce_only model with tax: null
- **Why:** Philly launched before tax data was available. Needs v3 upgrade when PRR arrives.

### Orlando: CE-only model (no tax data)
- **Spec says:** Intersection scoring requires both tax AND CE
- **Found:** Orlando has no tax delinquency source (PRR pending).
- **What I did:** Configured as ce_only model with tax: null.
- **Why:** Orlando launched as violations-only. Needs v2 upgrade when PRR arrives.

### Fort Lauderdale: Only 2 scoring components
- **Spec says:** Minimum 3 score components
- **Found:** After recency removal, Fort Lauderdale has only delinquency_amount (55%) + active_ce (45%)
- **What I did:** Documented with flag. Needs a 3rd component (e.g. delinquency duration).
- **Why:** Original 4-component model had 2 recency components. Removing both left only 2.

### Palm Beach: Union scoring in original script
- **Spec says:** Intersection only, never union
- **Found:** palmbeach_score.py uses union approach (tax OR CE parcel spine)
- **What I did:** Set config to intersection. Universal scorer will enforce.
- **Why:** Palm Beach will need re-validation after switching to intersection.

### Miami: Contains recency component
- **Spec says:** No freshness-based recency
- **Found:** Miami v1 has score_recency at 10% weight (inverted days since most recent violation)
- **What I did:** Marked recency component with TODO for removal.
- **Why:** Miami v1 predates the recency prohibition. Needs v2 rescore.
