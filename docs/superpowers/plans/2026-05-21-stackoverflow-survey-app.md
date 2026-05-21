# StackOverflow 2024 Survey App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a public interactive Streamlit dashboard exploring the StackOverflow 2024 Developer Survey, hosted on Cloud Run, with a shortened TinyURL link.

**Architecture:** One-time ETL downloads the official survey ZIP and writes a slim cleaned Parquet (selected columns only). A Streamlit app loads that Parquet (cached) and renders three tabs of dynamic Plotly charts driven by sidebar filters. The app is containerized and deployed to Cloud Run (`europe-central2`, unauthenticated). Git pushes go to a private GitHub repo on `main` after each task.

**Tech Stack:** Python 3.12, pandas, pyarrow, streamlit, plotly, Docker, gcloud (Cloud Run), gh (GitHub), TinyURL API.

---

### Task 1: Repo bootstrap (GitHub + project skeleton)

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.python-version` (optional, skip if not needed)

- [ ] **Step 1: Create requirements.txt**

```
streamlit==1.40.2
pandas==2.2.3
pyarrow==18.1.0
plotly==5.24.1
requests==2.32.3
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
data/raw/
data/so2024.zip
.DS_Store
```

Note: `data/raw/` and the ZIP are ignored (large); the slim `data/survey_2024.parquet` IS committed.

- [ ] **Step 3: Create the private GitHub repo and push**

Run:
```bash
gh repo create stack-overflow-analysis --private --source=. --remote=origin
git add -A
git commit -m "chore: project skeleton (requirements, gitignore)"
git branch -M main
git push -u origin main
```
Expected: repo `sitekwb/stack-overflow-analysis` created, `main` pushed.

---

### Task 2: ETL — build the slim Parquet

**Files:**
- Create: `etl/build_dataset.py`
- Test: `tests/test_etl.py`

- [ ] **Step 1: Write the ETL script**

`etl/build_dataset.py`:
```python
"""Download the StackOverflow 2024 survey and write a slim cleaned Parquet."""
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

SURVEY_URL = (
    "https://info.stackoverflowsolutions.com/rs/719-EMH-566/images/"
    "stack-overflow-developer-survey-2024.zip"
)
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "survey_2024.parquet"

# Single-value columns kept as-is.
SCALAR_COLS = [
    "ConvertedCompYearly",
    "Country",
    "EdLevel",
    "OrgSize",
    "DevType",
    "YearsCodePro",
    "RemoteWork",
    "AISelect",
]
# Multi-answer columns (semicolon-separated) kept as raw strings; split at app layer.
MULTI_COLS = ["LanguageHaveWorkedWith", "DatabaseHaveWorkedWith"]


def _read_survey_csv() -> pd.DataFrame:
    resp = requests.get(SURVEY_URL, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        name = next(n for n in zf.namelist() if n.endswith("survey_results_public.csv"))
        with zf.open(name) as fh:
            return pd.read_csv(fh, low_memory=False)


def build() -> pd.DataFrame:
    df = _read_survey_csv()
    keep = [c for c in SCALAR_COLS + MULTI_COLS if c in df.columns]
    slim = df[keep].copy()

    # Numeric coercion + sane salary bounds (drop obvious outliers / nulls kept as NaN).
    slim["ConvertedCompYearly"] = pd.to_numeric(
        slim["ConvertedCompYearly"], errors="coerce"
    )
    slim.loc[
        (slim["ConvertedCompYearly"] < 1) | (slim["ConvertedCompYearly"] > 2_000_000),
        "ConvertedCompYearly",
    ] = pd.NA

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    slim.to_parquet(OUT_PATH, index=False)
    return slim


if __name__ == "__main__":
    out = build()
    print(f"Wrote {len(out):,} rows, {len(out.columns)} cols -> {OUT_PATH}")
```

- [ ] **Step 2: Write the ETL test**

`tests/test_etl.py`:
```python
from pathlib import Path

import pandas as pd

PARQUET = Path(__file__).resolve().parents[1] / "data" / "survey_2024.parquet"


def test_parquet_exists_and_nonempty():
    assert PARQUET.exists(), "Run etl/build_dataset.py first"
    df = pd.read_parquet(PARQUET)
    assert len(df) > 1000


def test_parquet_has_expected_columns():
    df = pd.read_parquet(PARQUET)
    for col in ["ConvertedCompYearly", "Country", "LanguageHaveWorkedWith", "AISelect"]:
        assert col in df.columns
```

- [ ] **Step 3: Run the ETL to produce the Parquet**

Run: `python etl/build_dataset.py`
Expected: prints `Wrote <N> rows, ... -> .../data/survey_2024.parquet` (N ≈ 65,000).

- [ ] **Step 4: Run the ETL test**

Run: `pytest tests/test_etl.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add etl/build_dataset.py tests/test_etl.py data/survey_2024.parquet
git commit -m "feat: ETL to slim survey parquet"
git push
```

---

### Task 3: Data loader (cached)

**Files:**
- Create: `app/__init__.py` (empty)
- Create: `app/data_loader.py`
- Test: `tests/test_data_loader.py`

- [ ] **Step 1: Write the loader**

`app/data_loader.py`:
```python
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

MULTI_COLS = ["LanguageHaveWorkedWith", "DatabaseHaveWorkedWith"]


@_cache
def load_data() -> pd.DataFrame:
    return pd.read_parquet(PARQUET)


def explode_multi(df: pd.DataFrame, column: str) -> pd.Series:
    """Split a semicolon-separated multi-answer column into a flat Series of values."""
    return (
        df[column]
        .dropna()
        .str.split(";")
        .explode()
        .str.strip()
    )
```

- [ ] **Step 2: Write the loader test**

`tests/test_data_loader.py`:
```python
import pandas as pd

from app.data_loader import explode_multi, load_data


def test_load_data_nonempty():
    df = load_data()
    assert len(df) > 1000


def test_explode_multi_splits_semicolons():
    df = pd.DataFrame({"LanguageHaveWorkedWith": ["Python;Go", "Python", None]})
    out = explode_multi(df, "LanguageHaveWorkedWith")
    assert (out == "Python").sum() == 2
    assert (out == "Go").sum() == 1
```

- [ ] **Step 3: Run the loader test**

Run: `pytest tests/test_data_loader.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add app/__init__.py app/data_loader.py tests/test_data_loader.py
git commit -m "feat: cached data loader + multi-answer exploder"
git push
```

---

### Task 4: Streamlit app (UI + 3 dynamic tabs)

**Files:**
- Create: `app/streamlit_app.py`

- [ ] **Step 1: Write the app**

`app/streamlit_app.py`:
```python
"""Interactive StackOverflow 2024 survey dashboard."""
import pandas as pd
import plotly.express as px
import streamlit as st

from app.data_loader import explode_multi, load_data

st.set_page_config(page_title="StackOverflow 2024 Survey Explorer", layout="wide")
st.title("StackOverflow Developer Survey 2024 — Interactive Explorer")

df = load_data()

# ---- Sidebar global filters ----
st.sidebar.header("Filters")
top_countries = df["Country"].value_counts().head(15).index.tolist()
countries = st.sidebar.multiselect(
    "Country", sorted(df["Country"].dropna().unique()), default=top_countries[:5]
)

yc = pd.to_numeric(df["YearsCodePro"], errors="coerce")
yc_max = int(yc.dropna().clip(upper=50).max() or 50)
yrs = st.sidebar.slider("Years of professional coding", 0, yc_max, (0, yc_max))

dev_types = sorted(
    explode_multi(df, "DevType").unique()
    if df["DevType"].astype(str).str.contains(";").any()
    else df["DevType"].dropna().unique()
)
picked_devtypes = st.sidebar.multiselect("DevType (contains)", dev_types)

mask = pd.Series(True, index=df.index)
if countries:
    mask &= df["Country"].isin(countries)
yc_filled = yc.fillna(-1)
mask &= (yc_filled >= yrs[0]) & (yc_filled <= yrs[1])
if picked_devtypes:
    dt_pattern = "|".join(picked_devtypes)
    mask &= df["DevType"].fillna("").str.contains(dt_pattern)
fdf = df[mask]

st.caption(f"{len(fdf):,} respondents match the current filters.")

tab_comp, tab_tech, tab_ai = st.tabs(["Compensation", "Technologies", "AI"])

# ---- Tab 1: Compensation (the primary dynamic chart) ----
with tab_comp:
    group_col = st.selectbox(
        "Group by",
        ["Country", "EdLevel", "YearsCodePro", "RemoteWork", "OrgSize"],
    )
    chart_kind = st.radio("Chart", ["Bar (median)", "Box"], horizontal=True)
    cdf = fdf.dropna(subset=["ConvertedCompYearly", group_col])
    if group_col == "YearsCodePro":
        yc_b = pd.to_numeric(cdf["YearsCodePro"], errors="coerce")
        cdf = cdf.assign(
            _grp=pd.cut(
                yc_b,
                bins=[-1, 2, 5, 10, 20, 100],
                labels=["0-2", "3-5", "6-10", "11-20", "20+"],
            )
        )
        gcol = "_grp"
    else:
        gcol = group_col
    if cdf.empty:
        st.info("No salary data for the current selection.")
    elif chart_kind == "Bar (median)":
        agg = (
            cdf.groupby(gcol)["ConvertedCompYearly"]
            .median()
            .sort_values(ascending=False)
            .head(20)
            .reset_index()
        )
        fig = px.bar(
            agg, x=gcol, y="ConvertedCompYearly",
            labels={"ConvertedCompYearly": "Median yearly USD"},
            title=f"Median yearly compensation by {group_col}",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        keep = cdf[gcol].value_counts().head(12).index
        box = cdf[cdf[gcol].isin(keep)]
        fig = px.box(
            box, x=gcol, y="ConvertedCompYearly",
            title=f"Compensation distribution by {group_col}",
        )
        fig.update_yaxes(range=[0, box["ConvertedCompYearly"].quantile(0.95)])
        st.plotly_chart(fig, use_container_width=True)

# ---- Tab 2: Technologies ----
with tab_tech:
    which = st.radio("Category", ["Languages", "Databases"], horizontal=True)
    col = "LanguageHaveWorkedWith" if which == "Languages" else "DatabaseHaveWorkedWith"
    top_n = st.slider("Top N", 5, 30, 15)
    counts = explode_multi(fdf, col).value_counts().head(top_n).reset_index()
    counts.columns = [which, "respondents"]
    counts["%"] = (counts["respondents"] / max(len(fdf), 1) * 100).round(1)
    fig = px.bar(
        counts.sort_values("%"), x="%", y=which, orientation="h",
        title=f"Top {top_n} {which.lower()} (% of filtered respondents)",
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 3: AI ----
with tab_ai:
    dim = st.selectbox("Break down by", ["Country", "EdLevel", "RemoteWork", "OrgSize"])
    adf = fdf.dropna(subset=["AISelect", dim])
    if adf.empty:
        st.info("No AI data for the current selection.")
    else:
        adf = adf.assign(uses_ai=adf["AISelect"].str.startswith("Yes"))
        rate = (
            adf.groupby(dim)["uses_ai"].mean().mul(100).round(1)
            .sort_values(ascending=False).head(20).reset_index()
        )
        rate.columns = [dim, "% using AI tools"]
        fig = px.bar(
            rate, x=dim, y="% using AI tools",
            title=f"Share using AI tools by {dim}",
        )
        st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Smoke-run locally (headless, then stop)**

Run:
```bash
streamlit run app/streamlit_app.py --server.headless true --server.port 8501 &
sleep 8 && curl -sf http://localhost:8501/_stcore/health && echo " OK" ; kill %1
```
Expected: prints `ok OK` (health endpoint responds).

- [ ] **Step 3: Commit**

```bash
git add app/streamlit_app.py
git commit -m "feat: streamlit dashboard with 3 dynamic tabs"
git push
```

---

### Task 5: Containerize

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Write the Dockerfile**

`Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY data/survey_2024.parquet ./data/survey_2024.parquet
ENV PORT=8080
EXPOSE 8080
CMD streamlit run app/streamlit_app.py \
    --server.port=$PORT --server.address=0.0.0.0 \
    --server.headless=true --browser.gatherUsageStats=false
```

- [ ] **Step 2: Write .dockerignore**

`.dockerignore`:
```
data/raw/
data/so2024.zip
tests/
docs/
.git/
__pycache__/
.venv/
```

- [ ] **Step 3: Build and run the container locally**

Run:
```bash
docker build -t so-survey-app . \
  && docker run -d -p 8080:8080 --name so-test so-survey-app \
  && sleep 8 && curl -sf http://localhost:8080/_stcore/health && echo " OK" ; \
  docker rm -f so-test
```
Expected: prints `ok OK`.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: containerize app"
git push
```

---

### Task 6: Deploy to Cloud Run + shorten link

**Files:**
- Create: `deploy.sh`

- [ ] **Step 1: Write deploy.sh**

`deploy.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT="${PROJECT:-genomic-benchmarking}"
REGION="${REGION:-europe-central2}"
SERVICE="${SERVICE:-so-survey-app}"

gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --port 8080

gcloud run services describe "$SERVICE" \
  --project "$PROJECT" --region "$REGION" \
  --format='value(status.url)'
```

- [ ] **Step 2: Deploy**

Run: `bash deploy.sh`
Expected: deploy succeeds; prints the public `https://...run.app` URL.

- [ ] **Step 3: Verify the public URL responds**

Run: `curl -sf "<URL>/_stcore/health" && echo " OK"`
Expected: `ok OK`.

- [ ] **Step 4: Shorten the URL with TinyURL**

Run: `curl -s "https://tinyurl.com/api-create.php?url=<URL>"`
Expected: prints a `https://tinyurl.com/...` short link.

- [ ] **Step 5: Commit and record the link in README**

Create `README.md` with the live + short link, then:
```bash
git add deploy.sh README.md
git commit -m "feat: Cloud Run deploy script + live link"
git push
```

---

## Self-Review

**Spec coverage:**
- Interactive multi-column exploration → Tasks 3-4 (loader + tabs). ✓
- Dynamic chart → Task 4 Compensation tab (group-by + filters redraw). ✓
- Public link, no auth → Task 6 `--allow-unauthenticated`. ✓
- GCP hosting → Task 6 Cloud Run, `europe-central2`. ✓
- Private GitHub repo, push to main per step → Task 1 + push in every task. ✓
- Shortened link → Task 6 Step 4 TinyURL. ✓
- ETL to parquet → Task 2. ✓
- Tests (ETL + smoke) → Task 2 + Task 3 + Task 4 Step 2. ✓

**Placeholder scan:** No TBD/TODO; all code blocks complete. `<URL>` in Task 6 is a runtime value substituted from Step 2 output, not a plan placeholder.

**Type consistency:** `load_data()` and `explode_multi(df, column)` defined in Task 3 are used with matching signatures in Task 4. Column names (`ConvertedCompYearly`, `LanguageHaveWorkedWith`, `AISelect`, etc.) consistent between ETL keep-list and app usage.
