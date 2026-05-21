"""Load the slim survey Parquet, cached for Streamlit reruns."""
from pathlib import Path

import pandas as pd

try:
    import streamlit as st

    _cache = st.cache_data
except Exception:  # allow import outside Streamlit (tests)
    def _cache(func=None, **_kwargs):
        return func

PARQUET = Path(__file__).resolve().parents[1] / "data" / "survey_2024.parquet"


@_cache
def load_data() -> pd.DataFrame:
    return pd.read_parquet(PARQUET)
