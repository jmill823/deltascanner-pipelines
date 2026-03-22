"""Unit tests for the output validator."""
import os, sys, tempfile
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.score.validate_output import validate


def write_temp_csv(df, name="test.csv"):
    path = os.path.join(tempfile.gettempdir(), name)
    df.to_csv(path, index=False)
    return path


def write_temp_config(config_dict, name="test.yml"):
    import yaml
    path = os.path.join(tempfile.gettempdir(), name)
    with open(path, "w") as f:
        yaml.dump(config_dict, f)
    return path


VALID_CONFIG = {
    "city_id": "test",
    "scoring": {
        "method": "intersection",
        "components": [
            {"name": "delinq_amt", "weight": 0.50, "normalization": "log", "source_field": "x"},
            {"name": "delinq_dur", "weight": 0.20, "normalization": "minmax", "source_field": "y"},
            {"name": "active", "weight": 0.30, "normalization": "log", "source_field": "z"},
        ],
    },
    "output": {"expected_parcel_range": [5, 100]},
}


class TestValidator:
    def test_valid_output_passes(self):
        df = pd.DataFrame({
            "Rank": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "Composite_Score": [90, 80, 70, 60, 50, 40, 30, 20, 15, 10],
            "Score_Version": ["test-v1"] * 10,
            "Address": [f"{i} Main St" for i in range(10)],
            "Zip": ["60601", "60602", "60603", "60604", "60605",
                     "60606", "60607", "60608", "60609", "60610"],
            "Owner_Name": [f"Owner {i}" for i in range(10)],
            "Owner_Mailing_Address": [f"{i} Other St" for i in range(10)],
            "Absentee_Owner": [True, False, True, True, False, True, False, True, False, True],
            "Property_Type": ["Residential"] * 5 + ["Commercial"] * 5,
            "Assessed_Value": [100000 + i * 10000 for i in range(10)],
            "Year_Built": [1990 + i for i in range(10)],
            "Square_Footage": [1500 + i * 100 for i in range(10)],
            "Total_Delinquent_Balance": [5000 + i * 1000 for i in range(10)],
            "Years_Delinquent": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
            "Active_Violations": [3, 2, 1, 4, 0, 2, 1, 3, 0, 1],
            "Total_Violations": [5, 3, 2, 6, 1, 3, 2, 4, 1, 2],
            "Most_Recent_Violation_Date": ["2025-01-01"] * 10,
            "score_delinq_amt": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1],
        })
        csv_path = write_temp_csv(df, "valid_output.csv")
        config_path = write_temp_config(VALID_CONFIG, "valid_config.yml")
        results = validate(csv_path, config_path)
        failures = [r for r in results if not r[1]]
        assert len(failures) == 0, f"Unexpected failures: {failures}"

    def test_100_percent_null_field_fails(self):
        df = pd.DataFrame({
            "Rank": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "Composite_Score": [90, 80, 70, 60, 50, 40, 30, 20, 15, 10],
            "Empty_Field": [None] * 10,
            "Zip": ["60601"] * 10,
            "Absentee_Owner": [True, False] * 5,
            "Property_Type": ["Residential"] * 10,
        })
        csv_path = write_temp_csv(df, "null_field.csv")
        config_path = write_temp_config(VALID_CONFIG, "null_config.yml")
        results = validate(csv_path, config_path)
        null_checks = [r for r in results if "field_not_null:Empty_Field" in r[0]]
        assert len(null_checks) > 0
        assert not null_checks[0][1]  # Should fail

    def test_100_percent_false_absentee_fails(self):
        df = pd.DataFrame({
            "Rank": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "Composite_Score": [90, 80, 70, 60, 50, 40, 30, 20, 15, 10],
            "Absentee_Owner": [False] * 10,
            "Zip": ["60601"] * 10,
            "Property_Type": ["Residential"] * 10,
        })
        csv_path = write_temp_csv(df, "absentee_fail.csv")
        config_path = write_temp_config(VALID_CONFIG, "abs_config.yml")
        results = validate(csv_path, config_path)
        abs_checks = [r for r in results if r[0] == "absentee_owner"]
        assert len(abs_checks) > 0
        assert not abs_checks[0][1]

    def test_parcel_count_out_of_range_fails(self):
        df = pd.DataFrame({
            "Rank": list(range(1, 201)),
            "Composite_Score": list(range(200, 0, -1)),
            "Zip": ["60601"] * 200,
            "Absentee_Owner": [True, False] * 100,
            "Property_Type": ["Residential"] * 200,
        })
        csv_path = write_temp_csv(df, "count_fail.csv")
        config = VALID_CONFIG.copy()
        config["output"] = {"expected_parcel_range": [5, 50]}
        config_path = write_temp_config(config, "count_config.yml")
        results = validate(csv_path, config_path)
        count_checks = [r for r in results if r[0] == "parcel_count"]
        assert len(count_checks) > 0
        assert not count_checks[0][1]

    def test_float_zip_fails(self):
        df = pd.DataFrame({
            "Rank": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "Composite_Score": [90, 80, 70, 60, 50, 40, 30, 20, 15, 10],
            "Zip": ["60601.0", "60602.0", "60603", "60604", "60605",
                     "60606", "60607", "60608", "60609", "60610"],
            "Absentee_Owner": [True, False] * 5,
            "Property_Type": ["Residential"] * 10,
        })
        csv_path = write_temp_csv(df, "zip_fail.csv")
        config_path = write_temp_config(VALID_CONFIG, "zip_config.yml")
        results = validate(csv_path, config_path)
        zip_checks = [r for r in results if r[0] == "zip_format"]
        assert len(zip_checks) > 0
        assert not zip_checks[0][1]
