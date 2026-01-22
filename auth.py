import json
import random
import string
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
import requests
from config import (
    USUARIOS, TOKENS_WHATSAPP, LOGS_AUTH_RCA,
    API_URL, API_TOKEN, NUMERO_ADMIN
)
from database import get_usuario_by_id, get_usuario_pcempr_by_name, authenticate_pcempr_user

def login_required(f):
    """Decorator para verificar se o usuário está logado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se é usuário PCEMPR ou RCA logado
        if 'username' not in session and 'rca_codusur' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    """Decorator para verificar se o usuário tem a permissão necessária"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verifica se é usuário PCEMPR ou RCA logado
            if 'username' not in session and 'rca_codusur' not in session:
                return redirect(url_for('main.login'))
            
            # Se é usuário RCA, dar permissões básicas automaticamente
            if 'rca_codusur' in session:
                # RCAs têm acesso ao dashboard, painel e relatório
                rca_permissions = ['dashboard', 'painel', 'relatorio']
                if permission not in rca_permissions:
                    return jsonify({'error': 'Permissão insuficiente'}), 403
            else:
                # Usuário PCEMPR - verifica permissões na sessão primeiro
                if 'permissions' in session:
                    user_permissions = session['permissions']
                else:
                    # Fallback para usuários admin no dicionário USUARIOS
                    username = session['username']
                    if username not in USUARIOS:
                        return jsonify({'error': 'Usuário não encontrado'}), 403
                    user_permissions = USUARIOS[username].get('permissoes', [])
                
                if permission not in user_permissions:
                    return jsonify({'error': 'Permissão insuficiente'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def authenticate_user(username, password):
    """Autentica um usuário admin"""
    if username in USUARIOS and USUARIOS[username]['senha'] == password:
        return True
    return False

def authenticate_user_extended(username, password):
    """Autentica um usuário admin ou da PCEMPR"""
    # Primeiro tenta autenticação admin
    if username in USUARIOS and USUARIOS[username]['senha'] == password:
        return True, 'admin'
    
    # Se não for admin, tenta autenticação na PCEMPR
    if authenticate_pcempr_user(username, password):
        return True, 'pcempr'
    
    return False, None

def get_user_info(username):
    """Obtém informações do usuário"""
    if username in USUARIOS:
        return {
            'nome': USUARIOS[username]['nome'],
            'permissoes': USUARIOS[username]['permissoes']
        }
    return None

def generate_token():
    """Gera um token de 6 dígitos"""
    return ''.join(random.choices(string.digits, k=6))



def send_whatsapp_message(telefone, message):
    """Envia mensagem via WhatsApp usando a API configurada"""
    if not API_URL or not API_TOKEN:
        print("API WhatsApp não configurada")
        return False
    
    try:
        headers = {
            'Authorization': f'Bearer {API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Usar o mesmo formato do enviarwpp.py
        data = {
            'number': telefone,  # Mudança: 'phone' -> 'number'
            'body': message,     # Mudança: 'message' -> 'body'
            'userId': 19,
            'queueId': "",
            'sendSignature': False,
            'closeTicket': False
        }
        
        response = requests.post(API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar WhatsApp: {e}")
        return False

def send_whatsapp_token(telefone, token, nome):
    """Envia token via WhatsApp"""
    message = f"‎🔐 Código de Acesso DSL\n\nOlá {nome}!\n\nSeu código de acesso é: {token}\n\n⏰ Este código expira em 5 minutos.\n\nNão compartilhe este código com ninguém."
    return send_whatsapp_message(telefone, message)

def notify_admin_rca_login(nome, telefone, success=True):
    """Notifica o admin sobre tentativa de login de RCA"""
    if not NUMERO_ADMIN:
        return
    
    status = "✅ SUCESSO" if success else "❌ FALHA"
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    message = f"🔐 *Login RCA - {status}*\n\n"
    message += f"👤 **Nome:** {nome}\n"
    message += f"📱 **Telefone:** {telefone}\n"
    message += f"🕒 **Horário:** {timestamp}"
    
    send_whatsapp_message(NUMERO_ADMIN, message)





def create_whatsapp_token(codusur, telefone, nome):
    """Cria e armazena um token WhatsApp para RCA"""
    token = generate_token()
    timestamp = time.time()
    
    TOKENS_WHATSAPP[codusur] = {
        'token': token,
        'timestamp': timestamp,
        'telefone': telefone,
        'nome': nome
    }
    
    return token

def validate_whatsapp_token(codusur, token):
    """Valida um token WhatsApp para RCA"""
    print(f"[DEBUG validate_whatsapp_token] Validando token para codusur={codusur}")
    print(f"[DEBUG validate_whatsapp_token] Token recebido: '{token}' (tipo: {type(token)})")
    print(f"[DEBUG validate_whatsapp_token] Tokens armazenados: {list(TOKENS_WHATSAPP.keys())}")
    
    if codusur not in TOKENS_WHATSAPP:
        print(f"[DEBUG validate_whatsapp_token] codusur {codusur} NÃO encontrado em TOKENS_WHATSAPP")
        return False, None
    
    stored_data = TOKENS_WHATSAPP[codusur]
    print(f"[DEBUG validate_whatsapp_token] Dados armazenados: {stored_data}")
    print(f"[DEBUG validate_whatsapp_token] Token armazenado: '{stored_data['token']}' (tipo: {type(stored_data['token'])})")
    
    current_time = time.time()
    time_diff = current_time - stored_data['timestamp']
    print(f"[DEBUG validate_whatsapp_token] Diferença de tempo: {time_diff:.2f} segundos")
    
    # Token expira em 5 minutos (300 segundos)
    if time_diff > 300:
        print(f"[DEBUG validate_whatsapp_token] Token EXPIRADO (>{time_diff:.2f}s > 300s)")
        del TOKENS_WHATSAPP[codusur]
        return False, None
    
    # Comparar tokens removendo espaços em branco e convertendo para string
    token_armazenado = str(stored_data['token']).strip()
    token_recebido = str(token).strip()
    print(f"[DEBUG validate_whatsapp_token] Comparando: '{token_armazenado}' == '{token_recebido}'")
    
    if token_armazenado == token_recebido:
        print(f"[DEBUG validate_whatsapp_token] Tokens CORRESPONDEM! Login bem-sucedido.")
        nome = stored_data['nome']
        telefone = stored_data['telefone']
        del TOKENS_WHATSAPP[codusur]  # Remove o token após uso
        return True, {'nome': nome, 'telefone': telefone}
    
    print(f"[DEBUG validate_whatsapp_token] Tokens NÃO correspondem!")
    return False, None

def log_rca_auth_attempt(codusur, nome, telefone, success, details=""):
    """Registra tentativa de autenticação de RCA"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'codusur': codusur,
        'nome': nome,
        'telefone': telefone,
        'success': success,
        'details': details,
        'ip': request.remote_addr if request else 'N/A'
    }
    
    LOGS_AUTH_RCA.append(log_entry)
    
    # Mantém apenas os últimos 100 logs
    if len(LOGS_AUTH_RCA) > 100:
        LOGS_AUTH_RCA.pop(0)
    
    # Notifica o admin apenas em caso de sucesso para evitar spam
    if success:
        notify_admin_rca_login(nome, telefone, success)

def get_auth_logs(limit=50):
    """Obtém os logs de autenticação mais recentes"""
    return LOGS_AUTH_RCA[-limit:] if LOGS_AUTH_RCA else []

def cleanup_expired_tokens():
    """Remove tokens expirados (chamado periodicamente)"""
    current_time = time.time()
    expired_threshold = 300  # 5 minutos
    
    # Limpa tokens WhatsApp expirados
    expired_whatsapp = []
    for codusur, data in TOKENS_WHATSAPP.items():
        if current_time - data['timestamp'] > expired_threshold:
            expired_whatsapp.append(codusur)
    
    for codusur in expired_whatsapp:
        del TOKENS_WHATSAPP[codusur]

def format_phone_number(phone):
    """Formata número de telefone para padrão brasileiro"""
    if not phone:
        return phone
    
    # Remove caracteres não numéricos
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Adiciona código do país se necessário
    if len(clean_phone) == 11 and clean_phone.startswith('11'):
        clean_phone = '55' + clean_phone
    elif len(clean_phone) == 10:
        clean_phone = '5511' + clean_phone
    
    return clean_phone

def validate_phone_number(phone):
    """Valida se o número de telefone está no formato correto"""
    if not phone:
        return False
    
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Verifica se tem pelo menos 10 dígitos (telefone brasileiro)
    if len(clean_phone) < 10:
        return False
    
    # Verifica se tem no máximo 13 dígitos (com código do país)
    if len(clean_phone) > 13:
        return False
    
    return True