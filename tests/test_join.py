"""Unit tests for join key normalization utilities."""
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.utils.join import (
    strip_dashes_13digit, strip_dashes_12digit, strip_dashes_10digit,
    strip_dashes_17digit, strip_to_digits, strip_trailing_r,
    normalize_address, normalize_bbl, normalize_pin,
    pad_digits_9, pad_digits_13, pad_blocklot_7,
    get_normalizer,
)


class TestFloridaFolio:
    def test_miami_dade_13digit(self):
        assert strip_dashes_13digit("01-0101-090-1143") == "0101010901143"

    def test_miami_dade_no_dashes(self):
        assert strip_dashes_13digit("3040290021300") == "3040290021300"

    def test_miami_dade_short_pads(self):
        assert strip_dashes_13digit("123456") == "0000000123456"

    def test_miami_dade_empty(self):
        assert strip_dashes_13digit("") == ""
        assert strip_dashes_13digit(None) == ""

    def test_broward_12digit(self):
        assert strip_dashes_12digit("50-42-19-01-0010") == "504219010010"

    def test_duval_10digit(self):
        assert strip_dashes_10digit("000006-0030") == "0000060030"

    def test_palm_beach_17digit(self):
        assert strip_dashes_17digit("00-41-42-19-00-000-5350") == "00414219000005350"


class TestStripTrailingR:
    def test_trailing_r(self):
        assert strip_trailing_r("0000060030R") == "0000060030"

    def test_no_trailing_r(self):
        assert strip_trailing_r("0000060030") == "0000060030"

    def test_empty(self):
        assert strip_trailing_r("") == ""


class TestAddressNormalization:
    def test_basic_uppercase(self):
        assert normalize_address("123 main street") == "123 MAIN ST"

    def test_strip_unit(self):
        result = normalize_address("456 Oak Ave Apt 3B")
        assert "APT" not in result
        assert result == "456 OAK AVE"

    def test_strip_suite(self):
        result = normalize_address("789 Elm Blvd Suite 100")
        assert "SUITE" not in result

    def test_directionals(self):
        assert normalize_address("100 North Main") == "100 N MAIN"

    def test_collapse_whitespace(self):
        assert normalize_address("123  Main   St") == "123 MAIN ST"

    def test_empty(self):
        assert normalize_address("") == ""
        assert normalize_address(None) == ""


class TestNYCBBL:
    def test_10digit_bbl(self):
        assert normalize_bbl("1-00234-0056") == "1002340056"  # strips dashes, pads to 10

    def test_already_clean(self):
        assert normalize_bbl("1002340056") == "1002340056"


class TestCookCountyPIN:
    def test_pin_with_dashes(self):
        assert normalize_pin("14-33-200-010") == "1433200010"

    def test_pin_clean(self):
        assert normalize_pin("1433200010") == "1433200010"


class TestPadDigits:
    def test_opa_9digit(self):
        assert pad_digits_9("12345") == "000012345"

    def test_hcad_13digit(self):
        assert pad_digits_13("1234567890") == "0001234567890"

    def test_blocklot_7char(self):
        assert pad_blocklot_7("12345") == "0012345"


class TestGetNormalizer:
    def test_known_normalizer(self):
        fn = get_normalizer("normalize_address")
        assert fn("123 Main Street") == "123 MAIN ST"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            get_normalizer("nonexistent_normalizer")

    def test_none_returns_none(self):
        assert get_normalizer(None) is None
