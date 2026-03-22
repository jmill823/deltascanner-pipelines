"""Unit tests for extractor modules."""
import os, sys, json, tempfile
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.extract.nal import map_dor_use_code, extract_nal


class TestDORUseCodeMapping:
    def test_vacant(self):
        assert map_dor_use_code("00") == "Vacant"
        assert map_dor_use_code("10") == "Vacant"
        assert map_dor_use_code("15") == "Vacant"

    def test_residential(self):
        assert map_dor_use_code("01") == "Residential"
        assert map_dor_use_code("02") == "Residential"
        assert map_dor_use_code("08") == "Residential"

    def test_commercial(self):
        assert map_dor_use_code("20") == "Commercial"
        assert map_dor_use_code("39") == "Commercial"

    def test_industrial(self):
        assert map_dor_use_code("40") == "Industrial"
        assert map_dor_use_code("49") == "Industrial"

    def test_agricultural(self):
        assert map_dor_use_code("50") == "Agricultural"
        assert map_dor_use_code("69") == "Agricultural"

    def test_institutional(self):
        assert map_dor_use_code("70") == "Institutional"
        assert map_dor_use_code("79") == "Institutional"

    def test_other_ranges(self):
        assert map_dor_use_code("80") == "Other"
        assert map_dor_use_code("99") == "Other"

    def test_empty_returns_other(self):
        assert map_dor_use_code("") == "Other"
        assert map_dor_use_code(None) == "Other"

    def test_padded_single_digit(self):
        assert map_dor_use_code("1") == "Residential"  # "1" -> "01"


class TestNALExtractor:
    def test_extract_nal_basic(self):
        # Create a temp NAL CSV
        df = pd.DataFrame({
            "CO_NO": ["26", "26", "13"],
            "FILE_T": ["R", "R", "R"],
            "PARCEL_ID": ["0000060030R", "0000070040R", "3040290021300"],
            "DOR_UC": ["01", "20", "40"],
            "OWN_NAME": ["Owner A", "Owner B", "Owner C"],
            "PHY_ADDR1": ["100 MAIN ST", "200 OAK AVE", "300 ELM BLVD"],
        })
        src = os.path.join(tempfile.gettempdir(), "test_nal.csv")
        out = os.path.join(tempfile.gettempdir(), "test_nal_out.csv")
        df.to_csv(src, index=False)

        result = extract_nal(src, out, county_code="26", roll_type="R")
        assert len(result) == 2  # only CO_NO 26
        assert "Property_Type" in result.columns
        assert result.iloc[0]["Property_Type"] == "Residential"
        assert result.iloc[1]["Property_Type"] == "Commercial"


class TestSocrataExtractor:
    @patch("scripts.extract.socrata.requests.get")
    def test_socrata_json_pagination(self, mock_get):
        """Test that Socrata JSON extractor handles pagination."""
        page1 = [{"id": i, "val": f"row{i}"} for i in range(3)]
        page2 = []  # empty = done

        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = page1

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = page2

        mock_get.side_effect = [mock_resp1, mock_resp2]

        from scripts.extract.socrata import extract_socrata
        out = os.path.join(tempfile.gettempdir(), "test_socrata.csv")
        df = extract_socrata("https://example.com/resource/test.json", out, page_size=3)
        assert len(df) == 3


class TestArcGISExtractor:
    @patch("scripts.extract.arcgis.requests.get")
    def test_arcgis_pagination(self, mock_get):
        """Test ArcGIS extractor handles pagination and epoch dates."""
        meta_resp = MagicMock()
        meta_resp.json.return_value = {
            "maxRecordCount": 2,
            "fields": [{"name": "DATE_FIELD", "type": "esriFieldTypeDate"}],
        }

        page1_resp = MagicMock()
        page1_resp.json.return_value = {
            "features": [
                {"attributes": {"ID": 1, "DATE_FIELD": 1609459200000}},
                {"attributes": {"ID": 2, "DATE_FIELD": 1612137600000}},
            ]
        }

        page2_resp = MagicMock()
        page2_resp.json.return_value = {"features": []}

        mock_get.side_effect = [meta_resp, page1_resp, page2_resp]

        from scripts.extract.arcgis import extract_arcgis
        out = os.path.join(tempfile.gettempdir(), "test_arcgis.csv")
        df = extract_arcgis("https://example.com/MapServer/0", out)
        assert len(df) == 2
        # Check epoch conversion
        assert df.iloc[0]["DATE_FIELD"] == "2021-01-01"
