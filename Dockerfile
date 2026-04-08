# teste de commit
# Use uma imagem base oficial e estável do Python
FROM python:3.10-slim-bullseye

# Instala pacotes do sistema necessários para o Oracle Client
RUN apt-get update && apt-get install -y \
    unzip \
    libaio1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Baixa e instala o Oracle Instant Client
RUN wget https://download.oracle.com/otn_software/linux/instantclient/1923000/instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && unzip instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && mv instantclient_* /opt/oracle \
    && rm instantclient-basic-linux.x64-19.23.0.0.0dbru.zip

# Define as variáveis de ambiente para o Oracle Client
ENV LD_LIBRARY_PATH=/opt/oracle
ENV ORACLE_LIB_DIR=/opt/oracle

# Copia o arquivo de dependências primeiro (para cache do Docker)
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da aplicação
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
COPY .env .

# Comando para iniciar a aplicação usando Gunicorn
# --access-logfile - : logs de acesso no stdout
# --error-logfile - : logs de erro no stdout
# --log-level info : nível de log detalhado
# --capture-output : captura print() do Python
CMD ["gunicorn", "--bind", "0.0.0.0:6000", "--workers", "4", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--capture-output", "app:app"]

