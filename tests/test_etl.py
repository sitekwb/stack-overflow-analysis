from pathlib import Path

import pandas as pd

PARQUET = Path(__file__).resolve().parents[1] / "data" / "survey_2024.parquet"


def test_parquet_exists_and_nonempty():
    assert PARQUET.exists(), "Run etl/build_dataset.py first"
    df = pd.read_parquet(PARQUET)
    assert len(df) > 1000


def test_parquet_has_expected_columns():
    df = pd.read_parquet(PARQUET)
    for col in ["country", "converted_comp_yearly", "dev_type", "ai_select"]:
        assert col in df.columns


def test_coded_columns_are_decoded_to_labels():
    df = pd.read_parquet(PARQUET)
    # Decoded values are strings, not integer codes.
    assert df["dev_type"].dropna().map(type).eq(str).all()
    assert df["ai_select"].dropna().str.startswith(("Yes", "No")).any()
