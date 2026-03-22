"""Join key normalization utilities for DeltaScanner.

Each function normalizes a join key value to a standard format
so that keys from different sources can be matched.
"""

import re


def strip_dashes_13digit(value) -> str:
    """Florida folio (Miami-Dade): remove dashes, pad to 13 digits."""
    if value is None or str(value).strip() == "":
        return ""
    s = re.sub(r"[^0-9]", "", str(value).strip())
    return s.zfill(13) if s else ""


def strip_dashes_12digit(value) -> str:
    """Florida folio (Broward): remove dashes, pad to 12 digits."""
    if value is None or str(value).strip() == "":
        return ""
    s = re.sub(r"[^0-9]", "", str(value).strip())
    return s.zfill(12) if s else ""


def strip_dashes_10digit(value) -> str:
    """Florida folio (Duval/Jacksonville): strip dashes, pad to 10 digits."""
    if value is None or str(value).strip() == "":
        return ""
    s = re.sub(r"[^0-9]", "", str(value).strip())
    return s.zfill(10) if s else ""


def strip_dashes_17digit(value) -> str:
    """Florida PCN (Palm Beach): strip dashes, pad to 17 digits."""
    if value is None or str(value).strip() == "":
        return ""
    s = re.sub(r"[^0-9]", "", str(value).strip())
    return s.zfill(17) if s else ""


def strip_to_digits(value) -> str:
    """Strip to digits only, no padding."""
    if value is None or str(value).strip() == "":
        return ""
    return re.sub(r"[^0-9]", "", str(value).strip())


def strip_trailing_r(value) -> str:
    """Strip trailing 'R' suffix from NAL PARCEL_ID, then digits only."""
    if value is None or str(value).strip() == "":
        return ""
    s = str(value).strip()
    if s.upper().endswith("R"):
        s = s[:-1]
    return re.sub(r"[^0-9]", "", s)


def normalize_address(value) -> str:
    """Standard address normalization.
    Uppercase, strip unit/apt/suite, standardize directionals, collapse whitespace."""
    if value is None or str(value).strip() == "":
        return ""
    s = str(value).upper().strip()
    # Remove punctuation
    s = s.replace(",", "").replace(".", "")
    # Standardize street types
    replacements = {
        " STREET": " ST", " AVENUE": " AVE", " BOULEVARD": " BLVD",
        " DRIVE": " DR", " ROAD": " RD", " LANE": " LN",
        " COURT": " CT", " PLACE": " PL", " CIRCLE": " CIR",
        " TERRACE": " TER", " HIGHWAY": " HWY", " PARKWAY": " PKWY",
        " NORTH": " N", " SOUTH": " S", " EAST": " E", " WEST": " W",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    # Strip unit/apt/suite
    s = re.sub(r"\s+(APT|UNIT|STE|SUITE|#|FL|FLOOR|BLDG|BUILDING)\s*.*$", "", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_bbl(value) -> str:
    """NYC BBL: Borough(1) + Block(5, zero-padded) + Lot(4, zero-padded) = 10 chars."""
    if value is None or str(value).strip() == "":
        return ""
    s = re.sub(r"[^0-9]", "", str(value).strip())
    return s.zfill(10) if s else ""


def normalize_pin(value) -> str:
    """Cook County PIN: 10-digit, dashes removed."""
    if value is None or str(value).strip() == "":
        return ""
    s = re.sub(r"[^0-9]", "", str(value).strip())
    return s.zfill(10) if s else ""


def pad_digits(value, length: int) -> str:
    """Zero-pad to specified length."""
    if value is None or str(value).strip() == "":
        return ""
    s = re.sub(r"[^0-9]", "", str(value).strip())
    return s.zfill(length) if s else ""


def pad_digits_9(value) -> str:
    """Pad to 9 digits (Philadelphia OPA account)."""
    return pad_digits(value, 9)


def pad_digits_13(value) -> str:
    """Pad to 13 digits (Houston HCAD account)."""
    return pad_digits(value, 13)


def pad_blocklot_7(value) -> str:
    """Baltimore Block/Lot: BLOCK.zfill(4) + LOT.zfill(3) = 7-char key.
    Expects pre-concatenated block_lot or handles raw values."""
    if value is None or str(value).strip() == "":
        return ""
    s = str(value).strip()
    return s.zfill(7) if s else ""


JOIN_NORMALIZERS = {
    "strip_dashes_13digit": strip_dashes_13digit,
    "strip_dashes_12digit": strip_dashes_12digit,
    "strip_dashes_10digit": strip_dashes_10digit,
    "strip_dashes_17digit": strip_dashes_17digit,
    "strip_to_digits": strip_to_digits,
    "strip_trailing_r": strip_trailing_r,
    "normalize_address": normalize_address,
    "normalize_bbl": normalize_bbl,
    "normalize_pin": normalize_pin,
    "pad_digits_9": pad_digits_9,
    "pad_digits_13": pad_digits_13,
    "pad_blocklot_7": pad_blocklot_7,
}


def get_normalizer(name: str):
    """Get join key normalizer function by name."""
    if name is None:
        return None
    if name not in JOIN_NORMALIZERS:
        raise ValueError(
            f"Unknown join normalizer '{name}'. "
            f"Valid: {list(JOIN_NORMALIZERS.keys())}"
        )
    return JOIN_NORMALIZERS[name]
