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
