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
COPY routes.py .
COPY charts.py .
COPY enviarwpp.py .
COPY templates/ ./templates/
COPY .env .

# Copia e configura o script de entrada
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Cria usuário não-root para segurança
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expõe a porta 5000 (porta padrão da aplicação Flask)
EXPOSE 5000

# Comando para iniciar a aplicação usando o script de entrada
ENTRYPOINT ["./docker-entrypoint.sh"]

