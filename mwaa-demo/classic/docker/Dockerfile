FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pandas boto3 pyarrow

COPY app/pipeline.py .

ENTRYPOINT ["python", "pipeline.py"]
