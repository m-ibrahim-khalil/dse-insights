FROM python:3.12-slim
RUN pip install --no-cache-dir "psycopg[binary]==3.3.5"
COPY monitoring/exporter/app.py /app/app.py
EXPOSE 9108
CMD ["python", "/app/app.py"]
