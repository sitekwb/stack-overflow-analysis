"""Interactive StackOverflow 2024 Developer Survey dashboard.

Data: TidyTuesday mirror of the SO 2024 survey (single-response, decoded).
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from app.data_loader import load_data

st.set_page_config(page_title="StackOverflow 2024 Survey Explorer", layout="wide")
st.title("StackOverflow Developer Survey 2024 — Interactive Explorer")
st.caption(
    "Source: TidyTuesday mirror of the Stack Overflow 2024 Developer Survey "
    "(65,437 respondents, ODbL)."
)

df = load_data()

# ---- Sidebar global filters ----
st.sidebar.header("Filters")

top_countries = df["country"].value_counts().head(15).index.tolist()
countries = st.sidebar.multiselect(
    "Country",
    sorted(df["country"].dropna().unique()),
    default=top_countries[:6],
)

yc = pd.to_numeric(df["years_code_pro"], errors="coerce")
yc_max = int(yc.dropna().clip(upper=50).max() or 50)
yrs = st.sidebar.slider("Years of professional coding", 0, yc_max, (0, yc_max))

dev_types = sorted(df["dev_type"].dropna().unique())
picked_devtypes = st.sidebar.multiselect("DevType", dev_types)

mask = pd.Series(True, index=df.index)
if countries:
    mask &= df["country"].isin(countries)
yc_filled = yc.fillna(-1)
mask &= (yc_filled >= yrs[0]) & (yc_filled <= yrs[1])
if picked_devtypes:
    mask &= df["dev_type"].isin(picked_devtypes)
fdf = df[mask]

st.caption(f"**{len(fdf):,}** respondents match the current filters.")

# Human-friendly labels for the group-by selectors.
DIM_LABELS = {
    "country": "Country",
    "ed_level": "Education level",
    "years_code_pro": "Years of pro coding",
    "remote_work": "Remote work",
    "org_size": "Org size",
    "age": "Age",
    "dev_type": "DevType",
}

tab_comp, tab_ai, tab_profile = st.tabs(
    ["💰 Compensation", "🤖 AI", "🧑‍💻 Developer profile"]
)

# ---- Tab 1: Compensation (the primary dynamic chart) ----
with tab_comp:
    group_col = st.selectbox(
        "Group by",
        ["country", "ed_level", "years_code_pro", "remote_work", "org_size", "age"],
        format_func=lambda c: DIM_LABELS[c],
    )
    chart_kind = st.radio("Chart", ["Bar (median)", "Box"], horizontal=True)
    cdf = fdf.dropna(subset=["converted_comp_yearly", group_col])

    if group_col == "years_code_pro":
        yc_b = pd.to_numeric(cdf["years_code_pro"], errors="coerce")
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
            cdf.groupby(gcol, observed=True)["converted_comp_yearly"]
            .median()
            .sort_values(ascending=False)
            .head(20)
            .reset_index()
        )
        fig = px.bar(
            agg,
            x=gcol,
            y="converted_comp_yearly",
            labels={
                "converted_comp_yearly": "Median yearly USD",
                gcol: DIM_LABELS[group_col],
            },
            title=f"Median yearly compensation by {DIM_LABELS[group_col]}",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        keep = cdf[gcol].value_counts().head(12).index
        box = cdf[cdf[gcol].isin(keep)]
        fig = px.box(
            box,
            x=gcol,
            y="converted_comp_yearly",
            labels={
                "converted_comp_yearly": "Yearly USD",
                gcol: DIM_LABELS[group_col],
            },
            title=f"Compensation distribution by {DIM_LABELS[group_col]}",
        )
        fig.update_yaxes(range=[0, box["converted_comp_yearly"].quantile(0.95)])
        st.plotly_chart(fig, use_container_width=True)

# ---- Tab 2: AI adoption ----
with tab_ai:
    dim = st.selectbox(
        "Break down by",
        ["country", "ed_level", "remote_work", "org_size", "age"],
        format_func=lambda c: DIM_LABELS[c],
        key="ai_dim",
    )
    adf = fdf.dropna(subset=["ai_select", dim])
    if adf.empty:
        st.info("No AI data for the current selection.")
    else:
        adf = adf.assign(uses_ai=adf["ai_select"].str.startswith("Yes"))
        rate = (
            adf.groupby(dim, observed=True)["uses_ai"]
            .mean()
            .mul(100)
            .round(1)
            .sort_values(ascending=False)
            .head(20)
            .reset_index()
        )
        rate.columns = [dim, "pct_using_ai"]
        fig = px.bar(
            rate,
            x=dim,
            y="pct_using_ai",
            labels={"pct_using_ai": "% using AI tools", dim: DIM_LABELS[dim]},
            title=f"Share using AI tools by {DIM_LABELS[dim]}",
        )
        st.plotly_chart(fig, use_container_width=True)

# ---- Tab 3: Developer profile ----
with tab_profile:
    dim = st.selectbox(
        "Distribution of",
        ["dev_type", "ed_level", "age", "org_size", "remote_work"],
        format_func=lambda c: DIM_LABELS[c],
        key="profile_dim",
    )
    pdf = fdf[dim].dropna()
    if pdf.empty:
        st.info("No data for the current selection.")
    else:
        counts = pdf.value_counts().head(20).reset_index()
        counts.columns = [dim, "respondents"]
        counts["pct"] = (counts["respondents"] / max(len(fdf), 1) * 100).round(1)
        fig = px.bar(
            counts.sort_values("pct"),
            x="pct",
            y=dim,
            orientation="h",
            labels={"pct": "% of filtered respondents", dim: DIM_LABELS[dim]},
            title=f"{DIM_LABELS[dim]} distribution",
        )
        st.plotly_chart(fig, use_container_width=True)
