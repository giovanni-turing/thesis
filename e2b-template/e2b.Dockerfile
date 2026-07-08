# Thesis two-pool simulation fleet template.
# Torch-free: the "silicon" travels as AIC perf parquets; the whole pipeline
# is the aiconfigurator SDK + the ai-dynamo wheel + pandas.
FROM e2bdev/code-interpreter:latest

RUN pip install --no-cache-dir \
    "ai-dynamo==1.2.1" \
    "jinja2>=3.1.0" "packaging>=20.0" "numpy~=1.26.4" "pandas>=2.2.3" \
    "pyarrow>=15.0.0" "pydantic>=2.5" "pyyaml>=6.0" "scipy>=1.13.1" \
    "tqdm>=4.0.0" "munch>=4.0.0" "nvidia-ml-py" "prettytable>=3.16.0" \
    "plotext>=5.3.2" "matplotlib>=3.9.4" "plotly>=6.0.1" "bokeh"

COPY aic-src /opt/aic/src
COPY payload /opt/tese

ENV PYTHONPATH=/opt/aic/src
ENV TESE_TRACE=/opt/tese/data/trace.csv.gz
ENV TESE_WINDOWS=/opt/tese/windows.json
ENV FORECAST_PARQUET=/opt/tese/forecasts/chronos_images.parquet
ENV FORECAST_DIR=/opt/tese/forecasts
