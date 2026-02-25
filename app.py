from flask import Flask, send_from_directory
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from config import FLASK_SECRET_KEY, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, REDIS_HOST, REDIS_PORT, REDIS_DB
import os

# Cria a aplicação Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = FLASK_SECRET_KEY

# Configura ProxyFix para suportar proxy reverso (Nginx/OpenResty)
# Isso permite que o Flask reconheça corretamente os headers X-Forwarded-*
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Número de proxies que definem X-Forwarded-For
    x_proto=1,    # Número de proxies que definem X-Forwarded-Proto (HTTP/HTTPS)
    x_host=1,     # Número de proxies que definem X-Forwarded-Host
    x_prefix=1    # Número de proxies que definem X-Forwarded-Prefix
)

# Configurações para suportar proxy reverso (Nginx/OpenResty)
app.config['SESSION_COOKIE_SECURE'] = False  # Permite cookies mesmo sem HTTPS direto (proxy reverso)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Permite cookies no mesmo domínio
app.config['REMEMBER_COOKIE_SECURE'] = False
app.config['REMEMBER_COOKIE_HTTPONLY'] = True

# Configurações CSRF
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Token não expira
app.config['WTF_CSRF_SSL_STRICT'] = False  # Não força HTTPS (proxy reverso já gerencia)
app.config['WTF_CSRF_CHECK_DEFAULT'] = True

# Ativa proteção CSRF
csrf = CSRFProtect(app)

# Configura Rate Limiter com Redis
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    default_limits=["200 per day", "50 per hour"],
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window"
)

# Importa rotas depois de criar app e limiter para evitar importação circular
from routes import main_routes

# Registra o blueprint com todas as rotas
app.register_blueprint(main_routes)

# Importa configuração de rate limits e aplica nas rotas críticas
from rate_limit_config import RATE_LIMITS
limiter.limit(RATE_LIMITS['login'])(app.view_functions['main.login_modern'])
limiter.limit(RATE_LIMITS['login_rca'])(app.view_functions['main.login_rca'])
limiter.limit(RATE_LIMITS['api_kpis'])(app.view_functions['main.api_kpis'])
limiter.limit(RATE_LIMITS['api_graficos'])(app.view_functions['main.api_graficos'])
limiter.limit(RATE_LIMITS['agendamento'])(app.view_functions['main.atualizar'])
limiter.limit(RATE_LIMITS['agendamento_massa'])(app.view_functions['main.atualizar_massa'])

# Rota para página offline
@app.route('/offline')
def offline():
    return '''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Offline - DSL Agendamento</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-50 min-h-screen flex items-center justify-center p-4">
        <div class="text-center">
            <div class="w-24 h-24 mx-auto mb-6 bg-orange-100 rounded-full flex items-center justify-center">
                <svg class="w-12 h-12 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"></path>
                </svg>
            </div>
            <h1 class="text-3xl font-bold text-slate-800 mb-2">Você está offline</h1>
            <p class="text-slate-600 mb-6">Verifique sua conexão com a internet</p>
            <button onclick="window.location.reload()" class="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                Tentar Novamente
            </button>
        </div>
    </body>
    </html>
    '''

# Filtro personalizado para converter None em traço
@app.template_filter('none_to_dash')
def none_to_dash(value):
    """Converte valores None, vazios ou 'None' em traço (-)"""
    if value is None or value == 'None' or str(value).strip() == '':
        return '-'
    return value

if __name__ == '__main__':
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )