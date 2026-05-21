# StackOverflow 2024 Developer Survey — Interactive Explorer

Interactive Streamlit dashboard exploring the Stack Overflow 2024 Developer
Survey (65,437 respondents). Deployed on Google Cloud Run.

## Live app

- **Public URL:** _(added after deploy)_
- **Short link:** _(added after deploy)_

## What it does

Three tabs with dynamic Plotly charts driven by global sidebar filters
(country, years of professional coding, DevType):

- **💰 Compensation** — median / distribution of yearly USD compensation,
  grouped by country, education, experience, remote work, org size, or age.
- **🤖 AI** — share of respondents using AI tools, broken down by any dimension.
- **🧑‍💻 Developer profile** — distribution of DevType, education, age, etc.

## Data

Source: [TidyTuesday mirror](https://github.com/rfordatascience/tidytuesday/tree/main/data/2024/2024-09-03)
of the Stack Overflow 2024 survey (ODbL). The ETL decodes the coded
single-response columns via the official crosswalk and writes a slim Parquet.

> Note: this reliable mirror does not include the multi-response
> language/database columns, so technology-popularity is out of scope here.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python etl/build_dataset.py          # builds data/survey_2024.parquet
streamlit run app/streamlit_app.py
pytest                               # run tests
```

## Deploy

```bash
bash deploy.sh                       # gcloud run deploy -> public URL
```

## Layout

```
app/streamlit_app.py   UI + dynamic charts
app/data_loader.py     cached parquet loader
etl/build_dataset.py   download + decode -> data/survey_2024.parquet
Dockerfile             container for Cloud Run
deploy.sh              gcloud run deploy
docs/superpowers/      design spec + implementation plan
```
