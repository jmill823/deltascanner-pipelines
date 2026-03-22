"""Unit tests for the universal scorer and config validation."""
import pytest
import pandas as pd
import numpy as np
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.utils.schema import validate_config
from scripts.score.normalize import (
    log_normalize, minmax_normalize, binary_normalize,
    linear_normalize, get_normalizer,
)


class TestConfigValidation:
    def test_weights_must_sum_to_one(self):
        config = {
            "city_id": "test",
            "scoring": {
                "method": "intersection",
                "components": [
                    {"name": "a", "weight": 0.50, "normalization": "log", "source_field": "x"},
                    {"name": "b", "weight": 0.30, "normalization": "log", "source_field": "y"},
                    {"name": "c", "weight": 0.10, "normalization": "log", "source_field": "z"},
                ],
            },
        }
        with pytest.raises(ValueError, match="weights sum to"):
            validate_config(config)

    def test_weights_summing_to_one_passes(self):
        config = {
            "city_id": "test",
            "scoring": {
                "method": "intersection",
                "components": [
                    {"name": "delinq_amt", "weight": 0.50, "normalization": "log", "source_field": "x"},
                    {"name": "delinq_dur", "weight": 0.20, "normalization": "minmax", "source_field": "y"},
                    {"name": "active", "weight": 0.30, "normalization": "log", "source_field": "z"},
                ],
            },
        }
        assert validate_config(config) is True

    def test_tax_weight_below_50_percent_fails(self):
        config = {
            "city_id": "test",
            "scoring": {
                "method": "intersection",
                "components": [
                    {"name": "delinq_amt", "weight": 0.30, "normalization": "log", "source_field": "x"},
                    {"name": "active_violations", "weight": 0.40, "normalization": "log", "source_field": "y"},
                    {"name": "case_volume", "weight": 0.30, "normalization": "log", "source_field": "z"},
                ],
            },
        }
        with pytest.raises(ValueError, match="Tax weight"):
            validate_config(config)

    def test_fewer_than_3_components_fails(self):
        config = {
            "city_id": "test",
            "scoring": {
                "method": "intersection",
                "components": [
                    {"name": "delinq_amt", "weight": 0.60, "normalization": "log", "source_field": "x"},
                    {"name": "active", "weight": 0.40, "normalization": "log", "source_field": "y"},
                ],
            },
        }
        with pytest.raises(ValueError, match="scoring components"):
            validate_config(config)

    def test_ce_only_bypasses_tax_weight_check(self):
        config = {
            "city_id": "test",
            "ce_only": True,
            "scoring": {
                "method": "ce_only",
                "components": [
                    {"name": "violations", "weight": 0.50, "normalization": "log", "source_field": "x"},
                    {"name": "severity", "weight": 0.30, "normalization": "tiered", "source_field": "y"},
                    {"name": "structural", "weight": 0.20, "normalization": "linear", "source_field": "z"},
                ],
            },
        }
        assert validate_config(config) is True

    def test_recency_normalization_rejected(self):
        config = {
            "city_id": "test",
            "scoring": {
                "method": "intersection",
                "components": [
                    {"name": "delinq_amt", "weight": 0.50, "normalization": "log", "source_field": "x"},
                    {"name": "delinq_dur", "weight": 0.20, "normalization": "minmax", "source_field": "y"},
                    {"name": "recency", "weight": 0.30, "normalization": "recency", "source_field": "z"},
                ],
            },
        }
        with pytest.raises(ValueError, match="recency"):
            validate_config(config)

    def test_union_method_rejected(self):
        config = {
            "city_id": "test",
            "scoring": {
                "method": "union",
                "components": [
                    {"name": "delinq_amt", "weight": 0.50, "normalization": "log", "source_field": "x"},
                    {"name": "delinq_dur", "weight": 0.20, "normalization": "minmax", "source_field": "y"},
                    {"name": "active", "weight": 0.30, "normalization": "log", "source_field": "z"},
                ],
            },
        }
        with pytest.raises(ValueError, match="method"):
            validate_config(config)


class TestNormalization:
    def test_log_normalize_basic(self):
        s = pd.Series([0, 1, 10, 100, 1000])
        result = log_normalize(s)
        assert result.min() == 0.0
        assert abs(result.max() - 1.0) < 0.001
        assert result.is_monotonic_increasing

    def test_log_normalize_all_zeros(self):
        s = pd.Series([0, 0, 0])
        result = log_normalize(s)
        assert (result == 0.0).all()

    def test_log_normalize_all_same(self):
        s = pd.Series([5, 5, 5])
        result = log_normalize(s)
        assert (result == result.iloc[0]).all()

    def test_minmax_normalize_basic(self):
        s = pd.Series([0, 25, 50, 75, 100])
        result = minmax_normalize(s)
        assert result.iloc[0] == 0.0
        assert result.iloc[-1] == 1.0
        assert abs(result.iloc[2] - 0.5) < 0.001

    def test_minmax_normalize_all_same(self):
        s = pd.Series([42, 42, 42])
        result = minmax_normalize(s)
        assert (result == 0.0).all()

    def test_binary_normalize(self):
        s = pd.Series([0, 1, 0, True, False, "yes"])
        result = binary_normalize(s)
        assert result.iloc[0] == 0.0
        assert result.iloc[1] == 1.0

    def test_composite_score_range(self):
        """Composite = sum(weight * normalized) * 100 should be 0-100."""
        s1 = log_normalize(pd.Series([0, 50, 100]))
        s2 = minmax_normalize(pd.Series([0, 50, 100]))
        composite = (0.6 * s1 + 0.4 * s2) * 100
        assert composite.min() >= 0
        assert composite.max() <= 100

    def test_recency_normalizer_raises(self):
        with pytest.raises(ValueError, match="prohibited"):
            get_normalizer("recency")

    def test_inverse_days_normalizer_raises(self):
        with pytest.raises(ValueError, match="prohibited"):
            get_normalizer("inverse_days")
