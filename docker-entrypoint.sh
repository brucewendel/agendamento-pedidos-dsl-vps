#!/bin/bash

# Script de entrada para o container Docker
# Configura o ambiente e inicia a aplicação Flask

set -e

echo "🚀 Iniciando Sistema de Agendamento..."

# Verifica se as variáveis de ambiente essenciais estão definidas
if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_DSN" ]; then
    echo "❌ Erro: Variáveis de ambiente do banco de dados não configuradas!"
    echo "   Certifique-se de definir DB_USER, DB_PASSWORD e DB_DSN"
    exit 1
fi

# Verifica se a chave secreta do Flask está definida
if [ -z "$FLASK_SECRET_KEY" ]; then
    echo "⚠️  Aviso: FLASK_SECRET_KEY não definida. Gerando uma chave temporária..."
    export FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
fi

# Configura o ambiente Flask para produção
export FLASK_ENV=production
export FLASK_DEBUG=False

# Cria diretório de backups se não existir
mkdir -p /app/backups

echo "✅ Configuração concluída!"
echo "📊 Iniciando aplicação na porta 5000..."

# Inicia a aplicação Flask
exec python app.py