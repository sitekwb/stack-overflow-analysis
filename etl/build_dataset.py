"""Build a slim, decoded Parquet from the TidyTuesday mirror of the
StackOverflow 2024 Developer Survey.

Source (reliable, public, ODbL): rfordatascience/tidytuesday 2024-09-03.
The single-response CSV stores categorical answers as integer codes; the
crosswalk maps (qname, level) -> human label. Numeric/text columns
(country, years_code_pro, converted_comp_yearly) are used as-is.
"""
from pathlib import Path

import pandas as pd

BASE = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/"
    "data/2024/2024-09-03/"
)
SINGLE_URL = BASE + "stackoverflow_survey_single_response.csv"
CROSSWALK_URL = BASE + "qname_levels_single_response_crosswalk.csv"

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "survey_2024.parquet"

# Coded columns to decode via the crosswalk.
CODED_COLS = ["dev_type", "ed_level", "org_size", "remote_work", "age", "ai_select"]
# Columns kept as-is (text / numeric).
PASSTHROUGH_COLS = ["country", "years_code_pro", "converted_comp_yearly"]


def _decode(df: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    for col in CODED_COLS:
        mapping = (
            crosswalk[crosswalk["qname"] == col]
            .set_index("level")["label"]
            .to_dict()
        )
        df[col] = df[col].map(mapping)
    return df


def build() -> pd.DataFrame:
    single = pd.read_csv(SINGLE_URL)
    crosswalk = pd.read_csv(CROSSWALK_URL)

    keep = [c for c in CODED_COLS + PASSTHROUGH_COLS if c in single.columns]
    slim = single[keep].copy()
    slim = _decode(slim, crosswalk)

    # Numeric coercion + sane salary bounds (drop obvious outliers; keep NaN).
    slim["converted_comp_yearly"] = pd.to_numeric(
        slim["converted_comp_yearly"], errors="coerce"
    )
    bad = (slim["converted_comp_yearly"] < 1) | (
        slim["converted_comp_yearly"] > 2_000_000
    )
    slim.loc[bad, "converted_comp_yearly"] = pd.NA

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    slim.to_parquet(OUT_PATH, index=False)
    return slim


if __name__ == "__main__":
    out = build()
    print(f"Wrote {len(out):,} rows, {len(out.columns)} cols -> {OUT_PATH}")
