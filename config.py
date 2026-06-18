import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

def _build_oracle_dsn(host, port, service_name, connect_timeout, transport_connect_timeout):
    """Monta um connect descriptor Oracle com timeout de conexao."""
    return (
        "(DESCRIPTION="
        f"(CONNECT_TIMEOUT={connect_timeout})"
        f"(TRANSPORT_CONNECT_TIMEOUT={transport_connect_timeout})"
        "(RETRY_COUNT=0)"
        "(ADDRESS=(PROTOCOL=TCP)"
        f"(HOST={host})"
        f"(PORT={port}))"
        "(CONNECT_DATA="
        f"(SERVICE_NAME={service_name})"
        "))"
    )

def _parse_db_dsn_list():
    """Monta uma lista ordenada de DSNs para failover."""
    db_port = os.getenv("DB_PORT", "").strip()
    db_service_name = os.getenv("DB_SERVICE_NAME", "").strip()
    db_connect_timeout = os.getenv("DB_CONNECT_TIMEOUT", "5").strip()
    db_transport_connect_timeout = os.getenv("DB_TRANSPORT_CONNECT_TIMEOUT", "3").strip()

    dsn_list = []

    db_hosts = os.getenv("DB_HOSTS", "").strip()
    if db_hosts and db_port and db_service_name:
        hosts = [host.strip() for host in db_hosts.split(",") if host.strip()]
        dsn_list.extend(
            _build_oracle_dsn(
                host,
                db_port,
                db_service_name,
                db_connect_timeout,
                db_transport_connect_timeout
            )
            for host in hosts
        )
    elif db_port and db_service_name:
        for env_name in ("DB_HOST_1", "DB_HOST_2", "DB_HOST_3"):
            host = os.getenv(env_name, "").strip()
            if host:
                dsn_list.append(
                    _build_oracle_dsn(
                        host,
                        db_port,
                        db_service_name,
                        db_connect_timeout,
                        db_transport_connect_timeout
                    )
                )

    legacy_dsn = os.getenv("DB_DSN", "").strip()
    if legacy_dsn and legacy_dsn not in dsn_list:
        dsn_list.append(legacy_dsn)

    return dsn_list

# --- Configurações de Banco de Dados ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN_LIST = _parse_db_dsn_list()
DB_DSN = DB_DSN_LIST[0] if DB_DSN_LIST else None

# --- Configurações da Aplicação ---
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 6000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# --- Configurações de WhatsApp ---
API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
NUMERO_ADMIN = os.getenv("NUMERO_ADMIN")

# --- Configurações do Redis para Cache ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis") # 'redis' é o nome do serviço no docker-compose
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") # Se o Redis tiver senha

# --- Armazenamento Temporário ---
# Em produção, usar Redis ou banco de dados
TOKENS_WHATSAPP = {}  # {codusur: {'token': 'XXXX', 'timestamp': timestamp, 'telefone': 'XXXXXXXXX', 'nome': 'Nome do RCA'}}
LOGS_AUTH_RCA = []  # Lista para armazenar logs de tentativas

# --- Paleta de Cores Premium ---
CORES = {
    'primaria': '#6366f1',
    'primaria_clara': '#a5b4fc',
    'primaria_escura': '#4338ca',
    'sucesso': '#10b981',
    'sucesso_clara': '#6ee7b7',
    'alerta': '#f59e0b',
    'alerta_clara': '#fbbf24',
    'critico': '#ef4444',
    'critico_clara': '#f87171',
    'neutro': '#64748b',
    'neutro_claro': '#94a3b8',
    'neutro_escuro': '#334155',
    'background': '#f8fafc',
    'surface': '#ffffff',
    'gradient_primary': ['#6366f1', '#8b5cf6'],
    'gradient_success': ['#10b981', '#059669'],
    'gradient_warning': ['#f59e0b', '#d97706'],
    'gradient_danger': ['#ef4444', '#dc2626']
}

# --- Sistema de Usuários Admin ---
# Usuário admin padrão - em produção deve ser configurado via banco de dados
USUARIOS = {
    'admin': {
        'senha': 'admin',
        'nome': 'Administrador',
        'permissoes': ['dashboard', 'painel', 'relatorio', 'usuarios', 'agendamento']
    }
}
