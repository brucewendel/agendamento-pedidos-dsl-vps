import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from auth import (
    login_required, permission_required, authenticate_user, authenticate_user_extended, get_user_info,
    create_whatsapp_token, validate_whatsapp_token, send_whatsapp_token,
    log_rca_auth_attempt, format_phone_number, validate_phone_number,
    cleanup_expired_tokens
)
from database import (
    get_pedidos_pendentes, get_usuarios, get_usuario_by_id,
    get_agendamentos_confirmados, atualizar_agendamento,
    atualizar_telefone_usuario, get_stats_data
)
from charts import generate_all_charts
from rate_limit_config import RATE_LIMITS

# Cria blueprint para as rotas
main_routes = Blueprint('main', __name__)

# Importar limiter será feito via lazy import para evitar circular import
def get_limiter():
    """Obtém a instância do limiter do app"""
    from app import limiter
    return limiter

@main_routes.route('/api/kpis')
@login_required
@permission_required('dashboard')
def api_kpis():
    """API para obter dados dos KPIs"""
    try:
        # Determinar código RCA se aplicável
        codigo_rca = None
        if 'rca_codusur' in session:
            codigo_rca = session.get('rca_codusur')
            
        charts_data = generate_all_charts(codigo_rca)
        return jsonify({
            'success': True,
            'data': charts_data['kpis']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main_routes.route('/api/graficos')
@login_required
@permission_required('dashboard')
def api_graficos():
    """API para obter dados dos gráficos"""
    try:
        # Determinar código RCA se aplicável
        codigo_rca = None
        if 'rca_codusur' in session:
            codigo_rca = session.get('rca_codusur')
            
        charts_data = generate_all_charts(codigo_rca)
        return jsonify({
            'success': True,
            'data': {
                'pedidos_chart': charts_data['pedidos_chart'],
                'status_chart': charts_data['status_chart'],
                'performance_chart': charts_data['performance_chart'],
                'rca_chart': charts_data['rca_chart'],
                'horarios_chart': charts_data['horarios_chart'],
                'tendencia_chart': charts_data['tendencia_chart'],
                'performance_semanal_chart': charts_data['performance_semanal_chart']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main_routes.route('/')
@login_required
@permission_required('dashboard')
def index():
    """Página inicial - redireciona para o painel"""
    return redirect(url_for('main.painel'))

@main_routes.route('/login-modern', methods=['GET', 'POST'])
@main_routes.route('/login_modern.html', methods=['GET', 'POST'])
def login_modern():
    """Página de login modernizada com PWA"""
    if request.method == 'POST':
        # Detectar se é requisição AJAX/fetch (verifica headers)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.accept_mimetypes.accept_json and \
                  not request.accept_mimetypes.accept_html
        
        # Aceita tanto dados JSON quanto form-data
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Limpar espaços em branco
            if username:
                username = username.strip()
            if password:
                password = password.strip()
        
        auth_result, user_type = authenticate_user_extended(username, password)
        if auth_result:
            session['username'] = username
            session['user_type'] = user_type
            
            if user_type == 'admin':
                session['user_info'] = get_user_info(username)
            else:  # user_type == 'pcempr'
                # Para usuários da PCEMPR, criar info básica
                session['user_info'] = {
                    'nome': username,
                    'permissoes': ['dashboard', 'painel', 'relatorio', 'usuarios']
                }
                session['permissions'] = ['dashboard', 'painel', 'relatorio', 'usuarios']
            
            # Se for requisição AJAX/JSON, retorna JSON
            if request.is_json or is_ajax:
                return jsonify({
                    'success': True,
                    'redirect': url_for('main.painel')
                })
            else:
                # Se for form-data tradicional, redireciona diretamente
                return redirect(url_for('main.painel'))
        else:
            # Erro de autenticação
            if request.is_json or is_ajax:
                return jsonify({
                    'success': False,
                    'message': 'Credenciais inválidas'
                }), 401
            else:
                # Para form-data tradicional, renderiza a página com erro
                return render_template('login_modern.html', error='Credenciais inválidas')
    
    return render_template('login_modern.html')

@main_routes.route('/login', methods=['GET', 'POST'])
def login():
    """Redireciona para login modernizado"""
    return redirect(url_for('main.login_modern'))

@main_routes.route('/reset-permissions')
def reset_permissions():
    """Redefine as permissões do usuário atual"""
    if 'username' in session:
        session['permissions'] = ['dashboard', 'painel', 'relatorio', 'usuarios']
        return jsonify({'success': True, 'permissions': session['permissions']})
    elif 'rca_codusur' in session:
        session['permissions'] = ['dashboard', 'painel']
        return jsonify({'success': True, 'permissions': session['permissions']})
    else:
        return jsonify({'success': False, 'message': 'Usuário não logado'}), 401

@main_routes.route('/logout')
def logout():
    """Logout do usuário"""
    session.clear()
    return redirect(url_for('main.login'))

@main_routes.route('/manifest.json')
def manifest():
    """Servir o manifest.json com os headers corretos"""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static', 'manifest.json'))
    response.headers['Content-Type'] = 'application/manifest+json'
    return response

@main_routes.route('/service-worker.js')
def service_worker():
    """Servir o service worker com os headers corretos"""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static', 'service-worker.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@main_routes.route('/login-rca', methods=['GET', 'POST'])
def login_rca():
    """Login para RCAs via WhatsApp"""
    if request.method == 'POST':
        # Detectar se é requisição AJAX (fetch do JavaScript)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        
        # Verifica se os dados vêm como JSON ou FormData
        if request.is_json:
            data = request.get_json()
            step = data.get('step')
        else:
            # Dados vêm do formulário HTML
            data = request.form.to_dict()
            # Determina o step baseado nos campos presentes
            if 'token' in data:
                step = 'validate_token'
            else:
                step = 'request_token'
        
        if step == 'request_token':
            codusur = data.get('codusur') or data.get('codigo_rca')  # Suporte para ambos os nomes
            
            try:
                codusur = int(codusur)
            except (ValueError, TypeError):
                # Para formulário HTML, retorna página com erro
                if not request.is_json:
                    return render_template('login_rca_modern.html', 
                                         error='Código de usuário inválido')
                return jsonify({
                    'success': False,
                    'message': 'Código de usuário inválido'
                }), 400
            
            # Busca o usuário no banco
            usuario = get_usuario_by_id(codusur)
            if not usuario:
                log_rca_auth_attempt(codusur, 'Desconhecido', 'N/A', False, 'Usuário não encontrado')
                # Para requisição AJAX, retorna JSON
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'message': 'Usuário não encontrado'
                    }), 404
                # Para formulário HTML tradicional, retorna página com erro
                return render_template('login_rca_modern.html', 
                                     error='Usuário não encontrado')
            
            telefone = usuario.get('TELEFONE1')
            nome = usuario.get('NOME')
            
            if not telefone or not validate_phone_number(telefone):
                log_rca_auth_attempt(codusur, nome, telefone or 'N/A', False, 'Telefone inválido')
                # Para requisição AJAX, retorna JSON
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'message': 'Telefone não cadastrado ou inválido'
                    }), 400
                # Para formulário HTML tradicional, retorna página com erro
                return render_template('login_rca_modern.html', 
                                     error='Telefone não cadastrado ou inválido')
            
            # Gera e envia token
            token = create_whatsapp_token(codusur, telefone, nome)
            telefone_formatado = format_phone_number(telefone)
            
            print(f"Tentando enviar token {token} para {telefone_formatado} ({nome})")
            
            if send_whatsapp_token(telefone_formatado, token, nome):
                print(f"Token enviado com sucesso para {telefone_formatado}")
                # Para requisição AJAX, retorna JSON
                if is_ajax:
                    return jsonify({
                        'success': True,
                        'message': f'Token enviado via WhatsApp para {nome}',
                        'nome': nome,
                        'show_token': True
                    })
                # Para formulário HTML tradicional, mostra tela de token
                return render_template('login_rca_modern.html', 
                                     show_token=True, 
                                     codigo_rca=codusur,
                                     nome=nome,
                                     success=f'Token enviado via WhatsApp para {nome}')
            else:
                print(f"Falha ao enviar token para {telefone_formatado}")
                log_rca_auth_attempt(codusur, nome, telefone, False, 'Falha no envio do WhatsApp')
                # Para requisição AJAX, retorna JSON
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'message': 'Erro ao enviar token via WhatsApp'
                    }), 500
                # Para formulário HTML tradicional, retorna página com erro
                return render_template('login_rca_modern.html', 
                                     error='Erro ao enviar token via WhatsApp')
        
        elif step == 'validate_token':
            codusur = data.get('codusur') or data.get('codigo_rca')  # Suporte para ambos os nomes
            token = data.get('token')
            
            try:
                codusur = int(codusur)
            except (ValueError, TypeError):
                # Para formulário HTML, retorna página com erro
                if not request.is_json:
                    return render_template('login_rca_modern.html', 
                                         show_token=True, 
                                         codigo_rca=data.get('codigo_rca', ''),
                                         error='Código de usuário inválido')
                return jsonify({
                    'success': False,
                    'message': 'Código de usuário inválido'
                }), 400
            
            is_valid, user_data = validate_whatsapp_token(codusur, token)
            
            if is_valid and user_data:
                # Login bem-sucedido
                session['rca_codusur'] = codusur
                session['rca_nome'] = user_data['nome']
                session['rca_telefone'] = user_data['telefone']
                
                log_rca_auth_attempt(codusur, user_data['nome'], user_data['telefone'], True, 'Login bem-sucedido')
                
                # Para requisição AJAX, retorna JSON com URL de redirecionamento
                if is_ajax:
                    return jsonify({
                        'success': True,
                        'message': 'Login realizado com sucesso!',
                        'redirect': url_for('main.painel')
                    })
                
                # Para formulário HTML tradicional, redireciona diretamente
                return redirect(url_for('main.painel'))
            else:
                # Busca dados do usuário para log
                usuario = get_usuario_by_id(codusur)
                nome = usuario.get('NOME', 'Desconhecido') if usuario else 'Desconhecido'
                telefone = usuario.get('TELEFONE1', 'N/A') if usuario else 'N/A'
                
                log_rca_auth_attempt(codusur, nome, telefone, False, 'Token inválido ou expirado')
                
                # Para requisição AJAX, retorna JSON
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'message': 'Token inválido ou expirado'
                    }), 401
                
                # Para formulário HTML tradicional, retorna página com erro
                return render_template('login_rca_modern.html', 
                                     show_token=True, 
                                     codigo_rca=data.get('codigo_rca', ''),
                                     error='Token inválido ou expirado')
    
    # Limpa tokens expirados
    cleanup_expired_tokens()
    return render_template('login_rca_modern.html')

@main_routes.route('/painel')
def painel():
    """Painel principal para RCAs e usuários PCEMPR"""
    # Verifica se é RCA logado ou usuário PCEMPR
    if 'rca_codusur' not in session and 'username' not in session:
        return redirect(url_for('main.login_rca'))
    
    # Sempre redefinir as permissões para garantir que estejam corretas
    if 'rca_codusur' in session:
        # RCA tem permissões básicas incluindo relatório
        session['permissions'] = ['dashboard', 'painel', 'relatorio']
    elif 'username' in session:
        # Usuário PCEMPR tem todas as permissões
        session['permissions'] = ['dashboard', 'painel', 'relatorio', 'usuarios']
    
    # Obter a aba ativa dos parâmetros da URL, padrão é 'dashboard'
    active_tab = request.args.get('active_tab', 'dashboard')
    
    # Determinar dados do usuário baseado no tipo de login
    if 'rca_codusur' in session:
        # Usuário RCA
        user_name = session.get('rca_nome')
        user_id = session.get('rca_codusur')
    else:
        # Usuário PCEMPR
        user_name = session.get('username')
        user_id = session.get('username')
    
    try:
        # Parâmetros de paginação
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
        
        # Validar per_page (apenas valores permitidos)
        if per_page not in [25, 50, 75, 100]:
            per_page = 25
            
        offset = (page - 1) * per_page
        
        # Determinar código RCA se aplicável
        codigo_rca = None
        if 'rca_codusur' in session:
            codigo_rca = session.get('rca_codusur')
        
        # Inicializar variáveis
        pedidos = []
        total_pedidos = 0
        agendamentos = []
        total_agendamentos = 0
        usuarios = []
        stats = {'agendados_hoje': 0, 'agendados_7_dias': 0}
        
        # OTIMIZAÇÃO: Carregar apenas dados da aba ativa
        if active_tab == 'dashboard':
            # Dashboard só precisa de stats (consulta leve)
            stats = get_stats_data(codigo_rca=codigo_rca)
        
        elif active_tab == 'pendentes':
            # Carregar apenas pedidos pendentes
            numped_filtro = request.args.get('numped_pendentes')
            data_filtro = request.args.get('data_pedido_pendentes')
            codigo_rca_filtro = request.args.get('codigo_rca_pendentes')
            
            # Se usuário administrativo fornecer filtro de código RCA, usar ele ao invés do código da sessão
            if 'username' in session and codigo_rca_filtro:
                codigo_rca = codigo_rca_filtro
            
            pedidos_result = get_pedidos_pendentes(
                codigo_rca=codigo_rca,
                numped_filtro=numped_filtro,
                data_filtro=data_filtro,
                offset=offset,
                per_page=per_page
            )
            
            if isinstance(pedidos_result, tuple):
                pedidos, total_pedidos = pedidos_result
            else:
                pedidos = pedidos_result
                total_pedidos = len(pedidos) if pedidos else 0
        
        elif active_tab == 'confirmados':
            # Carregar apenas agendamentos confirmados
            numped_confirmados = request.args.get('numped_confirmados')
            data_de_confirmados = request.args.get('data_de_confirmados')
            data_ate_confirmados = request.args.get('data_ate_confirmados')
            
            agendamentos_result = get_agendamentos_confirmados(
                codigo_rca=codigo_rca,
                numped_filtro=numped_confirmados,
                data_de=data_de_confirmados,
                data_ate=data_ate_confirmados,
                offset=offset,
                per_page=per_page
            )
            
            if isinstance(agendamentos_result, tuple):
                agendamentos, total_agendamentos = agendamentos_result
            else:
                agendamentos = agendamentos_result
                total_agendamentos = len(agendamentos) if agendamentos else 0
        
        elif active_tab == 'usuarios':
            # Carregar apenas usuários
            filtro_rca = request.args.get('rca')
            filtro_supervisor = request.args.get('supervisor')
            usuarios = get_usuarios(filtro_rca=filtro_rca, filtro_supervisor=filtro_supervisor)
        
        # Definir filtros para o template (mesmo que vazios)
        filtro_rca = request.args.get('rca', '')
        filtro_supervisor = request.args.get('supervisor', '')
        
        # Calcular informações de paginação
        pagination = {
            'page': page,
            'pages': max(1, (total_pedidos + per_page - 1) // per_page),
            'per_page': per_page,
            'total': total_pedidos
        }
        
        pagination_confirmados = {
            'page': page,
            'pages': max(1, (total_agendamentos + per_page - 1) // per_page),
            'per_page': per_page,
            'total': total_agendamentos
        }
        
        return render_template('painel.html', 
                             pedidos_pendentes=pedidos, 
                             agendamentos_confirmados=agendamentos,
                             usuarios=usuarios,
                             filtro_rca=filtro_rca,
                             filtro_supervisor=filtro_supervisor,
                             stats=stats,
                             rca_nome=user_name,
                             rca_codusur=user_id,
                             active_tab=active_tab,
                             pagination=pagination,
                             pagination_confirmados=pagination_confirmados,
                             is_admin=session.get('user_type') in ['admin', 'pcempr'])
    except Exception as e:
        # Em caso de erro, ainda passa dados básicos para evitar erros no template
        pagination = {
            'page': 1,
            'pages': 1,
            'per_page': 25,
            'total': 0
        }
        pagination_confirmados = {
            'page': 1,
            'pages': 1,
            'per_page': 25,
            'total': 0
        }
        
        return render_template('painel.html', 
                             pedidos_pendentes=[], 
                             agendamentos_confirmados=[],
                             usuarios=[],
                             filtro_rca='',
                             filtro_supervisor='',
                             stats={'agendados_hoje': 0, 'agendados_7_dias': 0},
                             rca_nome=user_name,
                             rca_codusur=user_id,
                             active_tab=active_tab,
                             pagination=pagination,
                             pagination_confirmados=pagination_confirmados,
                             is_admin=session.get('user_type') in ['admin', 'pcempr'],
                             error=str(e))

@main_routes.route('/listar_painel')
def listar_painel():
    """Rota para listagem do painel com filtros e paginação - OTIMIZADA"""
    # Verifica se é RCA logado ou usuário PCEMPR
    if 'rca_codusur' not in session and 'username' not in session:
        return redirect(url_for('main.login_rca'))
    
    # Sempre redefinir as permissões para garantir que estejam corretas
    if 'rca_codusur' in session:
        session['permissions'] = ['dashboard', 'painel', 'relatorio']
    elif 'username' in session:
        session['permissions'] = ['dashboard', 'painel', 'relatorio', 'usuarios']
    
    # Obter a aba ativa dos parâmetros da URL
    active_tab = request.args.get('active_tab', 'pendentes')
    
    # Determinar dados do usuário
    if 'rca_codusur' in session:
        user_name = session.get('rca_nome')
        user_id = session.get('rca_codusur')
    else:
        user_name = session.get('username')
        user_id = session.get('username')
    
    try:
        # Parâmetros de paginação
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
        if per_page not in [25, 50, 75, 100]:
            per_page = 25
        offset = (page - 1) * per_page
        
        # Código RCA
        codigo_rca = session.get('rca_codusur') if 'rca_codusur' in session else None
        
        # Inicializar variáveis
        pedidos, total_pedidos = [], 0
        agendamentos, total_agendamentos = [], 0
        usuarios = []
        stats = {'agendados_hoje': 0, 'agendados_7_dias': 0}
        
        # OTIMIZAÇÃO: Carregar apenas dados da aba ativa
        if active_tab == 'dashboard':
            stats = get_stats_data(codigo_rca=codigo_rca)
        elif active_tab == 'pendentes':
            # Se usuário administrativo fornecer filtro de código RCA, usar ele ao invés do código da sessão
            codigo_rca_filtro = request.args.get('codigo_rca_pendentes')
            if 'username' in session and codigo_rca_filtro:
                codigo_rca = codigo_rca_filtro
            
            result = get_pedidos_pendentes(codigo_rca, request.args.get('numped_pendentes'), 
                                          request.args.get('data_pedido_pendentes'), offset, per_page)
            pedidos, total_pedidos = result if isinstance(result, tuple) else (result, len(result or []))
        elif active_tab == 'confirmados':
            result = get_agendamentos_confirmados(codigo_rca, request.args.get('numped_confirmados'),
                                                 request.args.get('data_de_confirmados'), 
                                                 request.args.get('data_ate_confirmados'), offset, per_page)
            agendamentos, total_agendamentos = result if isinstance(result, tuple) else (result, len(result or []))
        elif active_tab == 'usuarios':
            usuarios = get_usuarios(request.args.get('rca'), request.args.get('supervisor'))
        
        # Paginação
        pagination = {
            'page': page,
            'pages': max(1, (total_pedidos + per_page - 1) // per_page),
            'per_page': per_page,
            'total': total_pedidos
        }
        
        pagination_confirmados = {
            'page': page,
            'pages': max(1, (total_agendamentos + per_page - 1) // per_page),
            'per_page': per_page,
            'total': total_agendamentos
        }
        
        return render_template('painel.html', 
                             pedidos_pendentes=pedidos,
                             agendamentos_confirmados=agendamentos,
                             usuarios=usuarios,
                             filtro_rca=request.args.get('rca', ''),
                             filtro_supervisor=request.args.get('supervisor', ''),
                             stats=stats,
                             rca_nome=user_name,
                             rca_codusur=user_id,
                             active_tab=active_tab,
                             pagination=pagination,
                             pagination_confirmados=pagination_confirmados,
                             is_admin=session.get('user_type') in ['admin', 'pcempr'])
    except Exception as e:
        pagination = {
            'page': 1,
            'pages': 1,
            'per_page': 25,
            'total': 0
        }
        pagination_confirmados = {
            'page': 1,
            'pages': 1,
            'per_page': 25,
            'total': 0
        }
        return render_template('painel.html',
                             pedidos_pendentes=[],
                             agendamentos_confirmados=[],
                             usuarios=[],
                             filtro_rca='',
                             filtro_supervisor='',
                             stats={'agendados_hoje': 0, 'agendados_7_dias': 0},
                             rca_nome=user_name,
                             rca_codusur=user_id,
                             active_tab=active_tab,
                             pagination=pagination,
                             pagination_confirmados=pagination_confirmados,
                             is_admin=session.get('user_type') in ['admin', 'pcempr'],
                             error=str(e))

@main_routes.route('/atualizar', methods=['POST'])
def atualizar():
    """Atualiza um agendamento individual"""
    # Verificar se é usuário RCA ou PCEMPR/admin
    if 'rca_codusur' not in session and 'username' not in session:
        return jsonify({'success': False, 'message': 'Não autorizado'}), 401
    
    try:
        # Verifica se os dados vêm como JSON ou FormData
        if request.is_json:
            data = request.get_json()
        else:
            # Converte FormData para dict
            data = request.form.to_dict()
        
        numped = data.get('numped')
        preventrega = data.get('preventrega')
        horaini = data.get('horaini')
        horafim = data.get('horafim')
        observacao = data.get('observacao', '')
        
        # Validações básicas
        if not all([numped, preventrega, horaini, horafim]):
            return jsonify({
                'success': False,
                'message': 'Todos os campos obrigatórios devem ser preenchidos'
            }), 400
        
        # Converte data para formato datetime
        try:
            preventrega_obj = datetime.strptime(preventrega, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de data inválido'
            }), 400
        
        # Atualiza no banco
        result = atualizar_agendamento(numped, preventrega, horaini, horafim, observacao)
        
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'message': result.get('message', 'Agendamento atualizado com sucesso!')
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Erro ao atualizar agendamento')
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@main_routes.route('/atualizar-massa', methods=['POST'])
def atualizar_massa():
    """Atualiza múltiplos agendamentos"""
    # Verificar se é usuário RCA ou PCEMPR/admin
    if 'rca_codusur' not in session and 'username' not in session:
        return jsonify({'success': False, 'message': 'Não autorizado'}), 401
    
    try:
        # Verifica se os dados vêm como JSON ou FormData
        if request.is_json:
            data = request.get_json()
        else:
            # Converte FormData para dict
            data = request.form.to_dict()
        
        # Pega os números dos pedidos selecionados
        numpeds_selecionados = data.get('numpeds_selecionados')
        preventrega = data.get('preventrega')
        horaini = data.get('horaini')
        horafim = data.get('horafim')
        observacao = data.get('observacao', '')
        
        # Validação dos campos obrigatórios
        if not all([numpeds_selecionados, preventrega, horaini, horafim]):
            return jsonify({
                'success': False,
                'message': 'Todos os campos obrigatórios devem ser preenchidos'
            }), 400
        
        # Converte a string de números em lista
        try:
            numped_list = [int(n.strip()) for n in numpeds_selecionados.split(',') if n.strip()]
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Números de pedidos inválidos'
            }), 400
        
        if not numped_list:
            return jsonify({
                'success': False,
                'message': 'Nenhum agendamento selecionado'
            }), 400
        
        # Converte data
        try:
            data_entrega_obj = datetime.strptime(preventrega, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Data inválida'
            }), 400
        
        sucessos = 0
        erros = 0
        erros_agrupados = {}
        pedidos_com_erro = []
        
        for numped in numped_list:
            try:
                # Atualiza no banco
                result = atualizar_agendamento(numped, preventrega, horaini, horafim, observacao)
                
                if result.get('status') == 'success':
                    sucessos += 1
                else:
                    erros += 1
                    pedidos_com_erro.append(numped)
                    erro_msg = result.get("message", "Erro desconhecido")
                    
                    # Agrupa erros similares
                    if erro_msg in erros_agrupados:
                        erros_agrupados[erro_msg].append(numped)
                    else:
                        erros_agrupados[erro_msg] = [numped]
            
            except Exception as e:
                erros += 1
                pedidos_com_erro.append(numped)
                erro_msg = f'Erro interno - {str(e)}'
                if erro_msg in erros_agrupados:
                    erros_agrupados[erro_msg].append(numped)
                else:
                    erros_agrupados[erro_msg] = [numped]
        
        # Monta a mensagem de resposta
        if sucessos > 0 and erros == 0:
            message = f'{sucessos} agendamentos atualizados com sucesso!'
        elif sucessos > 0 and erros > 0:
            message = f'{sucessos} agendamentos atualizados com sucesso. {erros} pedidos não puderam ser agendados.'
        else:
            message = f'Nenhum agendamento foi processado com sucesso. {erros} pedidos não puderam ser agendados.'
        
        # Adiciona detalhes dos erros agrupados
        if erros_agrupados:
            message += '\n\nMotivos:'
            for erro_msg, pedidos in erros_agrupados.items():
                # Remove prefixos desnecessários da mensagem de erro
                erro_limpo = erro_msg.replace('Erro: ', '').replace(f'Erro no pedido {pedidos[0]}: ', '')
                
                if len(pedidos) == 1:
                    message += f'\n• Pedido {pedidos[0]}: {erro_limpo}'
                else:
                    message += f'\n• {len(pedidos)} pedidos: {erro_limpo}'
        
        return jsonify({
            'success': sucessos > 0,
            'message': message,
            'sucessos': sucessos,
            'erros': erros
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

# Rota /usuarios removida - funcionalidade integrada no painel principal

@main_routes.route('/api/usuarios')
@login_required
@permission_required('usuarios')
def api_usuarios():
    """API para obter lista de usuários"""
    try:
        # Obter filtros da query string
        filtro_rca = request.args.get('rca', '')
        filtro_supervisor = request.args.get('supervisor', '')
        
        usuarios_list = get_usuarios(filtro_rca, filtro_supervisor)
        
        # Padronizar campo TELEFONE para compatibilidade com o JavaScript
        for usuario in usuarios_list:
            if 'TELEFONE1' in usuario and 'TELEFONE' not in usuario:
                usuario['TELEFONE'] = usuario['TELEFONE1']
        
        return jsonify({
            'success': True,
            'usuarios': usuarios_list  # Mudança aqui: 'usuarios' em vez de 'data'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main_routes.route('/api/usuarios/<int:codusur>')
@login_required
@permission_required('usuarios')
def api_usuario_detalhes(codusur):
    """API para obter detalhes de um usuário específico"""
    try:
        usuario = get_usuario_by_id(codusur)
        if usuario:
            # Padronizar campo TELEFONE para compatibilidade com o JavaScript
            if 'TELEFONE1' in usuario and 'TELEFONE' not in usuario:
                usuario['TELEFONE'] = usuario['TELEFONE1']
            
            return jsonify({
                'status': 'success',  # Mudança aqui: 'status' em vez de 'success'
                'usuario': usuario    # Mudança aqui: 'usuario' em vez de 'data'
            })
        else:
            return jsonify({
                'status': 'error',    # Mudança aqui: 'status' em vez de 'success'
                'message': 'Usuário não encontrado'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',    # Mudança aqui: 'status' em vez de 'success'
            'message': str(e)
        }), 500

@main_routes.route('/api/usuarios/telefone', methods=['POST'])
@login_required
@permission_required('usuarios')
def api_atualizar_telefone():
    """API para atualizar telefone de usuário"""
    try:
        data = request.get_json()
        codusur = data.get('codusur')
        telefone = data.get('telefone')
        
        if not codusur or not telefone:
            return jsonify({
                'status': 'error',
                'message': 'Código do usuário e telefone são obrigatórios'
            }), 400
        
        # Remover espaços e caracteres especiais para validação
        telefone_numeros = ''.join(filter(str.isdigit, telefone))
        
        # Verificar se telefone (apenas números) não excede 13 caracteres
        if len(telefone_numeros) > 13:
            return jsonify({
                'status': 'error',
                'message': 'Telefone deve ter no máximo 13 dígitos'
            }), 400
        
        if not telefone_numeros:
            return jsonify({
                'status': 'error',
                'message': 'Telefone deve conter pelo menos um número'
            }), 400
        
        success = atualizar_telefone_usuario(codusur, telefone)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Telefone atualizado com sucesso!'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Erro ao atualizar telefone'
            }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro interno: {str(e)}'
        }), 500

@main_routes.route('/api/usuarios/atualizar', methods=['POST'])
@login_required
@permission_required('usuarios')
def api_atualizar_usuario():
    """API para atualizar dados de usuário"""
    try:
        data = request.get_json()
        codusur = data.get('codusur')
        telefone = data.get('telefone')
        
        if not codusur or not telefone:
            return jsonify({
                'success': False,
                'message': 'Código do usuário e telefone são obrigatórios'
            }), 400
        
        if not validate_phone_number(telefone):
            return jsonify({
                'success': False,
                'message': 'Formato de telefone inválido'
            }), 400
        
        success = atualizar_telefone_usuario(codusur, telefone)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Telefone atualizado com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao atualizar telefone'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@main_routes.route('/relatorio')
@login_required
@permission_required('relatorio')
def relatorio():
    """Página de relatórios com agendamentos confirmados"""
    try:
        # Determinar dados do usuário
        if 'rca_codusur' in session:
            user_name = session.get('rca_nome')
            user_id = session.get('rca_codusur')
            codigo_rca = session.get('rca_codusur')
        else:
            user_name = session.get('username')
            user_id = session.get('username')
            codigo_rca = None
        
        print(f"[RELATORIO] Usuario: {user_name}, Codigo RCA: {codigo_rca}")
        
        # Parâmetros de paginação
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
        if per_page not in [25, 50, 75, 100]:
            per_page = 25
        offset = (page - 1) * per_page
        
        # Parâmetros de filtro
        numped_confirmados = request.args.get('numped_confirmados')
        data_de_confirmados = request.args.get('data_de_confirmados')
        data_ate_confirmados = request.args.get('data_ate_confirmados')
        
        print(f"[RELATORIO] Filtros - Numped: {numped_confirmados}, Data De: {data_de_confirmados}, Data Ate: {data_ate_confirmados}")
        print(f"[RELATORIO] Paginacao - Page: {page}, Per Page: {per_page}, Offset: {offset}")
        
        # Buscar agendamentos confirmados
        agendamentos_result = get_agendamentos_confirmados(
            codigo_rca=codigo_rca,
            numped_filtro=numped_confirmados,
            data_de=data_de_confirmados,
            data_ate=data_ate_confirmados,
            offset=offset,
            per_page=per_page
        )
        
        if isinstance(agendamentos_result, tuple):
            agendamentos, total_agendamentos = agendamentos_result
        else:
            agendamentos = agendamentos_result
            total_agendamentos = len(agendamentos) if agendamentos else 0
        
        print(f"[RELATORIO] Resultado - Total: {total_agendamentos}, Registros retornados: {len(agendamentos) if agendamentos else 0}")
        
        # Paginação
        pagination = {
            'page': page,
            'pages': max(1, (total_agendamentos + per_page - 1) // per_page),
            'per_page': per_page,
            'total': total_agendamentos
        }
        
        print(f"[RELATORIO] Renderizando template com {len(agendamentos) if agendamentos else 0} agendamentos")
        
        return render_template('painel.html',
                             pedidos_pendentes=[],
                             agendamentos_confirmados=agendamentos,
                             usuarios=[],
                             filtro_rca='',
                             filtro_supervisor='',
                             stats={'agendados_hoje': 0, 'agendados_7_dias': 0},
                             rca_nome=user_name,
                             rca_codusur=user_id,
                             active_tab='confirmados',
                             pagination=pagination)
    except Exception as e:
        print(f"[RELATORIO] ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Erro ao carregar relatório: {str(e)}", 500

@main_routes.route('/atualizar-telefone', methods=['GET', 'POST'])
@login_required
@permission_required('usuarios')
def atualizar_telefone():
    """Página para atualizar telefone de usuário"""
    if request.method == 'POST':
        data = request.get_json()
        codusur = data.get('codusur')
        telefone = data.get('telefone')
        
        if not codusur or not telefone:
            return jsonify({
                'success': False,
                'message': 'Código do usuário e telefone são obrigatórios'
            }), 400
        
        if not validate_phone_number(telefone):
            return jsonify({
                'success': False,
                'message': 'Formato de telefone inválido'
            }), 400
        
        success = atualizar_telefone_usuario(codusur, telefone)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Telefone atualizado com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao atualizar telefone'
            }), 500
    
    try:
        usuarios_list = get_usuarios()
        return render_template('atualizar_telefone.html', usuarios=usuarios_list)
    except Exception as e:
        return render_template('atualizar_telefone.html', error=str(e))

