FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y \
    unzip \
    libaio1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN wget https://download.oracle.com/otn_software/linux/instantclient/1923000/instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && unzip instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && mv instantclient_* /opt/oracle \
    && rm instantclient-basic-linux.x64-19.23.0.0.0dbru.zip

ENV LD_LIBRARY_PATH=/opt/oracle
ENV ORACLE_LIB_DIR=/opt/oracle

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY config.py .
COPY auth.py .
COPY database.py .
COPY database_edit_agendamento.py .
COPY routes.py .
COPY charts.py .
COPY enviarwpp.py .
COPY rate_limit_config.py .
COPY templates/ ./templates/
COPY static/ ./static/

CMD ["gunicorn", "--bind", "0.0.0.0:6000", "--workers", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--capture-output", "app:app"]
