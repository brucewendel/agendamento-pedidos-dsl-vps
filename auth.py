import hashlib
import json
import random
import secrets
import string
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from config import (
    USUARIOS, TOKENS_WHATSAPP, LOGS_AUTH_RCA,
    API_URL, API_TOKEN, NUMERO_ADMIN, APP_BASE_URL
)
from database import get_usuario_by_id, get_usuario_pcempr_by_name, authenticate_pcempr_user, redis_client
from enviarwpp import send_message, send_cta_message

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


def send_whatsapp_token(telefone, token, nome):
    """Envia token via WhatsApp usando endpoint CTA com botão de copiar"""
    header = "🔐 Código de Acesso DSL"
    text = f"Olá {nome}!\n\nSeu código de acesso é: {token}"
    footer = "Não compartilhe este código com ninguém."
    
    # Enviar via endpoint CTA com botão de copiar
    number, success, response = send_cta_message(
        number=telefone,
        header=header,
        text=text,
        footer=footer,
        button_value=token,
        button_label="Copiar código",
        button_type="copy",
        create_ticket=False
    )
    
    return success  # Retorna True se enviado com sucesso

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
    
    send_message(message, numero_destino=NUMERO_ADMIN)

def create_whatsapp_token(codusur, telefone, nome):
    """Cria e armazena um token WhatsApp para RCA"""
    token = generate_token()
    timestamp = time.time()
    
    # Garantir que codusur seja inteiro
    codusur = int(codusur)
    
    token_data = {
        'token': token,
        'timestamp': timestamp,
        'telefone': telefone,
        'nome': nome
    }
    
    # Armazenar em Redis (preferencial) ou memória (fallback)
    if redis_client:
        try:
            redis_key = f"rca_token:{codusur}"
            redis_client.setex(redis_key, 300, json.dumps(token_data))  # Expira em 5 minutos
            print(f"[DEBUG create_whatsapp_token] Token '{token}' armazenado no Redis para codusur={codusur}")
        except Exception as e:
            print(f"[WARN] Erro ao armazenar token no Redis: {e}. Usando memória.")
            TOKENS_WHATSAPP[codusur] = token_data
    else:
        TOKENS_WHATSAPP[codusur] = token_data
        print(f"[DEBUG create_whatsapp_token] Token '{token}' armazenado em memória para codusur={codusur}")
    
    return token

def validate_whatsapp_token(codusur, token):
    """Valida um token WhatsApp para RCA"""
    print(f"[DEBUG validate_whatsapp_token] Validando token para codusur={codusur} (tipo: {type(codusur)})")
    print(f"[DEBUG validate_whatsapp_token] Token recebido RAW: '{token}' (tipo: {type(token)})")
    print(f"[DEBUG validate_whatsapp_token] Token recebido repr: {repr(token)}")
    
    # Garantir que codusur seja inteiro para comparação
    try:
        codusur = int(codusur)
        print(f"[DEBUG validate_whatsapp_token] codusur convertido para int: {codusur}")
    except (ValueError, TypeError):
        print(f"[DEBUG validate_whatsapp_token] ERRO ao converter codusur para int")
        return False, None
    
    # Buscar token no Redis primeiro, depois na memória
    stored_data = None
    
    if redis_client:
        try:
            redis_key = f"rca_token:{codusur}"
            redis_value = redis_client.get(redis_key)
            if redis_value:
                stored_data = json.loads(redis_value)
                print(f"[DEBUG validate_whatsapp_token] Token encontrado no Redis")
            else:
                print(f"[DEBUG validate_whatsapp_token] Token NÃO encontrado no Redis")
        except Exception as e:
            print(f"[WARN] Erro ao buscar token no Redis: {e}")
    
    # Fallback para memória se não encontrou no Redis
    if not stored_data and codusur in TOKENS_WHATSAPP:
        stored_data = TOKENS_WHATSAPP[codusur]
        print(f"[DEBUG validate_whatsapp_token] Token encontrado na memória")
    
    if not stored_data:
        print(f"[DEBUG validate_whatsapp_token] codusur {codusur} NÃO encontrado")
        return False, None
    
    print(f"[DEBUG validate_whatsapp_token] Dados armazenados: {stored_data}")
    print(f"[DEBUG validate_whatsapp_token] Token armazenado: '{stored_data['token']}' (tipo: {type(stored_data['token'])})")
    
    current_time = time.time()
    time_diff = current_time - stored_data['timestamp']
    print(f"[DEBUG validate_whatsapp_token] Diferença de tempo: {time_diff:.2f} segundos")
    
    # Token expira em 5 minutos (300 segundos) - verificação adicional
    if time_diff > 300:
        print(f"[DEBUG validate_whatsapp_token] Token EXPIRADO (>{time_diff:.2f}s > 300s)")
        # Remover do Redis e memória
        if redis_client:
            try:
                redis_client.delete(f"rca_token:{codusur}")
            except:
                pass
        if codusur in TOKENS_WHATSAPP:
            del TOKENS_WHATSAPP[codusur]
        return False, None
    
    # Limpar e normalizar tokens - remover TODOS os espaços e caracteres não numéricos
    token_armazenado = ''.join(filter(str.isdigit, str(stored_data['token'])))
    token_recebido = ''.join(filter(str.isdigit, str(token)))
    
    print(f"[DEBUG validate_whatsapp_token] Token armazenado LIMPO: '{token_armazenado}' (len={len(token_armazenado)})")
    print(f"[DEBUG validate_whatsapp_token] Token recebido LIMPO: '{token_recebido}' (len={len(token_recebido)})")
    print(f"[DEBUG validate_whatsapp_token] Comparando: '{token_armazenado}' == '{token_recebido}'")
    
    if token_armazenado == token_recebido:
        print(f"[DEBUG validate_whatsapp_token] ✅ Tokens CORRESPONDEM! Login bem-sucedido.")
        nome = stored_data['nome']
        telefone = stored_data['telefone']
        
        # Remover token do Redis e memória após uso
        if redis_client:
            try:
                redis_client.delete(f"rca_token:{codusur}")
            except:
                pass
        if codusur in TOKENS_WHATSAPP:
            del TOKENS_WHATSAPP[codusur]
        
        return True, {'nome': nome, 'telefone': telefone}
    
    print(f"[DEBUG validate_whatsapp_token] ❌ Tokens NÃO correspondem!")
    print(f"[DEBUG validate_whatsapp_token] Diferença char por char:")
    for i, (c1, c2) in enumerate(zip(token_armazenado, token_recebido)):
        if c1 != c2:
            print(f"[DEBUG validate_whatsapp_token]   Posição {i}: '{c1}' != '{c2}'")
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
    """Formata número de telefone para padrão brasileiro com código do país"""
    if not phone:
        return phone
    
    # Remove TODOS os caracteres não numéricos (parênteses, espaços, hífens, etc)
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Adiciona código do país 55 se necessário
    # Formato esperado: 5585999999999 (13 dígitos)
    if len(clean_phone) == 11:
        # Número com DDD + 9 dígitos (celular) - adiciona código do país
        clean_phone = '55' + clean_phone
    elif len(clean_phone) == 10:
        # Número com DDD + 8 dígitos (fixo) - adiciona código do país
        clean_phone = '55' + clean_phone
    elif len(clean_phone) == 13 and clean_phone.startswith('55'):
        # Já tem código do país - mantém como está
        pass
    elif len(clean_phone) < 10:
        # Número muito curto - retorna como está para validação falhar
        pass

    # Envio sem o 9 adicional: 55 + DDD + 9XXXXXXXX -> 55 + DDD + XXXXXXXX
    # (a API de WhatsApp aceita mas não entrega quando o número vai com o nono dígito)
    if len(clean_phone) == 13 and clean_phone.startswith('55') and clean_phone[4] == '9':
        clean_phone = clean_phone[:4] + clean_phone[5:]

    print(f"[DEBUG format_phone_number] Entrada: '{phone}' -> Saída: '{clean_phone}'")
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


# ============================================
# SENHA DO RCA + REDEFINICAO POR LINK NO WHATSAPP
# ============================================

SENHA_MIN_LEN = 8
SENHA_MAX_LEN = 128
MAX_TENTATIVAS_LOGIN = 5
BLOQUEIO_MINUTOS = 15
RESET_TTL_SEG = 1800        # validade do link: 30 minutos
RESET_COOLDOWN_SEG = 60     # intervalo minimo entre links para o mesmo RCA

def hash_senha(senha):
    """Gera o hash (com salt) da senha; nunca guardamos a senha pura."""
    return generate_password_hash(senha, method='pbkdf2:sha256:600000')

def verificar_senha(senha_hash, senha):
    """Confere a senha digitada contra o hash salvo."""
    if not senha_hash or not senha:
        return False
    try:
        return check_password_hash(senha_hash, senha)
    except Exception:
        return False

def validar_senha_nova(senha):
    """Retorna a mensagem de erro da regra de senha, ou None se estiver ok."""
    if not senha or len(senha) < SENHA_MIN_LEN:
        return f'A senha deve ter pelo menos {SENHA_MIN_LEN} caracteres.'
    if len(senha) > SENHA_MAX_LEN:
        return f'A senha deve ter no máximo {SENHA_MAX_LEN} caracteres.'
    if senha.isdigit():
        return 'A senha não pode ter apenas números.'
    return None

def _reset_key(token):
    # No Redis fica so o hash do token: quem ler o Redis nao consegue montar o link
    return "rca_reset:" + hashlib.sha256(token.encode()).hexdigest()

def criar_token_reset(codusur):
    """Cria um token de uso unico para definir/redefinir a senha. Invalida o anterior."""
    if not redis_client:
        return None
    try:
        token = secrets.token_urlsafe(32)
        key = _reset_key(token)
        pointer = f"rca_reset_user:{int(codusur)}"
        anterior = redis_client.get(pointer)
        pipe = redis_client.pipeline()
        if anterior:
            pipe.delete(anterior)
        pipe.setex(key, RESET_TTL_SEG, str(int(codusur)))
        pipe.setex(pointer, RESET_TTL_SEG, key)
        pipe.execute()
        return token
    except Exception as e:
        print(f"[ERRO criar_token_reset] {e}")
        return None

def consultar_token_reset(token):
    """Retorna o codusur dono do token (sem consumir) ou None se invalido/expirado."""
    if not redis_client or not token:
        return None
    try:
        valor = redis_client.get(_reset_key(token))
        return int(valor) if valor else None
    except Exception as e:
        print(f"[ERRO consultar_token_reset] {e}")
        return None

def invalidar_token_reset(token):
    """Apaga o token (uso unico) depois de a senha ser gravada."""
    if not redis_client or not token:
        return
    try:
        redis_client.delete(_reset_key(token))
    except Exception as e:
        print(f"[ERRO invalidar_token_reset] {e}")

def _reservar_envio_reset(codusur):
    """True se pode enviar agora; False se ja enviou ha menos de RESET_COOLDOWN_SEG."""
    if not redis_client:
        return True
    try:
        return bool(redis_client.set(f"rca_reset_cd:{int(codusur)}", 1, nx=True, ex=RESET_COOLDOWN_SEG))
    except Exception:
        return True

def _liberar_envio_reset(codusur):
    if not redis_client:
        return
    try:
        redis_client.delete(f"rca_reset_cd:{int(codusur)}")
    except Exception:
        pass

def solicitar_reset_senha(codusur):
    """Gera o link de definir/redefinir senha e envia por WhatsApp (texto simples).

    Retorna (ok, motivo). O motivo e so para log: a rota responde sempre igual
    para nao revelar quais codigos existem.
    """
    usuario = get_usuario_by_id(codusur)
    if not usuario:
        return False, 'usuario_inexistente'

    nome = usuario.get('NOME')
    telefone = usuario.get('TELEFONE1')
    if not telefone or not validate_phone_number(telefone):
        return False, 'telefone_invalido'

    if not _reservar_envio_reset(codusur):
        return False, 'cooldown'

    token = criar_token_reset(codusur)
    if not token:
        return False, 'sem_redis'

    link = f"{APP_BASE_URL}/redefinir-senha/{token}"
    mensagem = "\n\n".join([
        f"Olá {nome}!",
        "Recebemos um pedido para definir a senha do seu acesso ao DSL Agendamento.",
        f"Acesse o link (válido por {RESET_TTL_SEG // 60} minutos):\n{link}",
        "Se não foi você, ignore esta mensagem.",
    ])
    # API_URL aponta para o endpoint CTA (exige "text" + botoes), entao o envio vai por send_cta_message
    _, enviado, _ = send_cta_message(
        number=format_phone_number(telefone),
        header="🔐 Definir senha - DSL",
        text=mensagem,
        footer="Não compartilhe este link com ninguém.",
        button_value=link,
        button_label="Copiar link",
        button_type="copy",
        create_ticket=False
    )
    if enviado:
        return True, 'enviado'
    _liberar_envio_reset(codusur)  # falhou: nao gastar o intervalo de 1 minuto
    return False, 'falha_envio'
