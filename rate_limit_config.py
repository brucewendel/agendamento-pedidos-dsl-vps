"""
Configuração de Rate Limiting para rotas específicas
"""

# Limites para diferentes tipos de rotas
RATE_LIMITS = {
    # Rotas de autenticação - proteção contra brute force
    'login': "5 per 15 minutes",  # Máximo 5 tentativas de login em 15 minutos
    'login_rca': "10 per 10 minutes",  # Login RCA por senha; o bloqueio por conta (5 falhas) fica no banco
    'esqueci_senha': "5 per 15 minutes",  # Pedidos de link de senha por WhatsApp (por IP; há também intervalo por RCA)
    'redefinir_senha': "20 per 15 minutes",  # Abertura/envio do formulário de nova senha
    
    # APIs de leitura
    'api_read': "60 per minute",  # 60 requisições por minuto para APIs de leitura
    'api_kpis': "30 per minute",  # 30 requisições por minuto para KPIs
    'api_graficos': "20 per minute",  # 20 requisições por minuto para gráficos
    
    # APIs de escrita - mais restritivas
    'api_write': "20 per minute",  # 20 requisições de escrita por minuto
    'agendamento': "10 per minute",  # 10 agendamentos por minuto
    'agendamento_massa': "5 per minute",  # 5 agendamentos em massa por minuto
    'atualizar_telefone': "10 per minute",  # 10 atualizações de telefone por minuto
}

# Mensagens de erro personalizadas
ERROR_MESSAGES = {
    'login': {
        'pt': 'Muitas tentativas de login. Aguarde 15 minutos e tente novamente.',
        'en': 'Too many login attempts. Wait 15 minutes and try again.'
    },
    'api': {
        'pt': 'Limite de requisições excedido. Aguarde um momento e tente novamente.',
        'en': 'Rate limit exceeded. Wait a moment and try again.'
    },
    'agendamento': {
        'pt': 'Você está fazendo agendamentos muito rápido. Aguarde um momento.',
        'en': 'You are scheduling too fast. Wait a moment.'
    }
}

def get_rate_limit_error_message(limit_type='api', lang='pt'):
    """Retorna mensagem de erro personalizada para rate limit"""
    return ERROR_MESSAGES.get(limit_type, ERROR_MESSAGES['api']).get(lang, ERROR_MESSAGES['api']['pt'])
