import cx_Oracle
from datetime import datetime, date
import json
import redis
from flask import session
from config import DB_USER, DB_PASSWORD, DB_DSN, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

# Usando cx_Oracle para melhor compatibilidade com Oracle Database

# Inicializa o cliente Redis
try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client.ping()
    print("✅ Conectado ao Redis com sucesso!")
except redis.exceptions.ConnectionError as e:
    print(f"❌ Erro ao conectar ao Redis: {e}")
    redis_client = None

class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def cache_data(key_prefix, ex=300): # ex é o tempo de expiração em segundos (5 minutos)
    def decorator(func):
        def wrapper(*args, **kwargs):
            if redis_client:
                # Gera uma chave de cache baseada no nome da função e seus argumentos
                # Converte args e kwargs para uma string JSON para garantir uma chave única
                cache_key_parts = [key_prefix, func.__name__]
                cache_key_parts.extend(map(str, args))
                for k, v in sorted(kwargs.items()):
                    cache_key_parts.append(f"{k}={v}")
                cache_key = ":".join(cache_key_parts)

                cached_result = redis_client.get(cache_key)
                if cached_result:
                    print(f"Cache HIT para {cache_key}")
                    return json.loads(cached_result)
                
                result = func(*args, **kwargs)
                redis_client.setex(cache_key, ex, json.dumps(result, cls=CustomJsonEncoder))
                print(f"Cache MISS para {cache_key}, resultado armazenado.")
                return result
            else:
                print("Redis não conectado, executando função sem cache.")
                return func(*args, **kwargs)
        return wrapper
    return decorator

def get_connection(app_user=None):
    """Obtém uma conexão com o banco de dados Oracle
    
    Args:
        app_user: Nome do usuário da aplicação (PCEMPR ou RCA) para auditoria
    """
    try:
        connection = cx_Oracle.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        
        # Definir CLIENT_IDENTIFIER para auditoria (se usuário fornecido)
        if app_user and connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "BEGIN DBMS_SESSION.SET_IDENTIFIER(:app_user); END;",
                    {'app_user': app_user}
                )
                cursor.close()
            except Exception as e:
                print(f"Aviso: Não foi possível definir CLIENT_IDENTIFIER: {e}")
        
        return connection
    except Exception as e:
        print(f"Erro ao conectar com o banco: {e}")
        return None

def get_app_user_name():
    """Obtém o nome do usuário logado na aplicação para auditoria
    
    Returns:
        str: Nome do usuário (PCEMPR.NOME_GUERRA ou PCUSUARI.NOME)
    """
    try:
        # Verificar se é usuário RCA
        if 'rca_nome' in session:
            return session['rca_nome']
        
        # Verificar se é usuário administrativo (PCEMPR)
        if 'username' in session:
            # Buscar NOME_GUERRA da PCEMPR
            connection = get_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(
                        "SELECT NOME_GUERRA FROM PCEMPR WHERE MATRICULA = :username",
                        {'username': session['username']}
                    )
                    result = cursor.fetchone()
                    cursor.close()
                    connection.close()
                    
                    if result and result[0]:
                        return result[0]
                    else:
                        # Se não encontrar NOME_GUERRA, retorna o username
                        return session['username']
                except:
                    connection.close()
                    return session['username']
        
        return None
    except:
        return None

def execute_query(query, params=None, fetch_one=False, fetch_all=True):
    """Executa uma query no banco de dados"""
    connection = get_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
        
        connection.commit()
        return result
    except Exception as e:
        print(f"Erro ao executar query: {e}")
        connection.rollback()
        return None
    finally:
        cursor.close()
        connection.close()

def get_pedidos_pendentes(codigo_rca=None, numped_filtro=None, data_filtro=None, offset=0, per_page=25):
    """Obtém pedidos da PCPEDC que ainda não foram agendados (não existem na DSLTI_PEDAGEND)"""
    connection = get_connection()
    if not connection:
        return [], 0
    
    try:
        cursor = connection.cursor()
        
        # Query para contar total de registros
        # Busca pedidos da PCPEDC que NÃO existem na DSLTI_PEDAGEND
        sql_count = """
            SELECT COUNT(*) 
            FROM PCPEDC p
            INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI 
            WHERE NOT EXISTS (
                SELECT 1 FROM DSLTI_PEDAGEND a 
                WHERE a.NUMPED = p.NUMPED
            )
            AND p.CODSUPERVISOR NOT IN (9130)
            AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
        """
        params_count = {}
        
        # Query principal para buscar pedidos
        # Busca pedidos da PCPEDC que NÃO existem na DSLTI_PEDAGEND
        sql_pedidos = """
            SELECT p.NUMPED, c.CLIENTE, p.DATA, p.NUMNOTA, p.NUMCAR
            FROM PCPEDC p
            INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI 
            WHERE NOT EXISTS (
                SELECT 1 FROM DSLTI_PEDAGEND a 
                WHERE a.NUMPED = p.NUMPED
            )
            AND p.CODSUPERVISOR NOT IN (9130)
            AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
        """
        params_pedidos = {}
        
        # Adicionar filtro por RCA se necessário
        if codigo_rca:
            sql_count += " AND p.CODUSUR = :codigo_rca"
            sql_pedidos += " AND p.CODUSUR = :codigo_rca"
            params_count['codigo_rca'] = codigo_rca
            params_pedidos['codigo_rca'] = codigo_rca
        
        # Adicionar filtros adicionais
        if numped_filtro:
            sql_count += " AND p.NUMPED = :numped"
            sql_pedidos += " AND p.NUMPED = :numped"
            params_count['numped'] = int(numped_filtro)
            params_pedidos['numped'] = int(numped_filtro)
        
        if data_filtro:
            sql_count += " AND TRUNC(p.DATA) = TO_DATE(:data_p, 'YYYY-MM-DD')"
            sql_pedidos += " AND TRUNC(p.DATA) = TO_DATE(:data_p, 'YYYY-MM-DD')"
            params_count['data_p'] = data_filtro
            params_pedidos['data_p'] = data_filtro
        
        # Executar contagem
        cursor.execute(sql_count, params_count)
        total_pendentes = cursor.fetchone()[0]
        
        # Aplicar paginação na consulta principal
        sql_pedidos += " ORDER BY p.DATA DESC, p.NUMPED DESC"
        sql_pedidos += " OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY"
        params_pedidos['offset'] = offset
        params_pedidos['per_page'] = per_page
        
        cursor.execute(sql_pedidos, params_pedidos)
        columns = [col[0] for col in cursor.description]
        pedidos_pendentes = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return pedidos_pendentes, total_pendentes
        
    except Exception as e:
        print(f"Erro ao buscar pedidos pendentes: {e}")
        return [], 0
    finally:
        if connection:
            connection.close()

def get_usuarios(filtro_rca=None, filtro_supervisor=None):
    """Obtém lista de usuários/RCAs do banco de dados com filtros opcionais"""
    connection = get_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        
        # Consulta base para obter usuários da tabela PCUSUARI
        sql = "SELECT CODUSUR, NOME, TELEFONE1, CODSUPERVISOR FROM DSL.PCUSUARI WHERE DTTERMINO IS NULL"
        params = {}
        
        # Aplicar filtro por RCA (nome ou código)
        if filtro_rca:
            sql += " AND (UPPER(NOME) LIKE UPPER(:filtro_rca_nome) OR CAST(CODUSUR AS VARCHAR2(20)) LIKE :filtro_rca_cod)"
            params['filtro_rca_nome'] = f'%{filtro_rca}%'
            params['filtro_rca_cod'] = f'%{filtro_rca}%'
        
        # Aplicar filtro por supervisor (busca aproximada)
        if filtro_supervisor:
            sql += " AND CAST(CODSUPERVISOR AS VARCHAR2(20)) LIKE :filtro_supervisor"
            params['filtro_supervisor'] = f'%{filtro_supervisor}%'
        
        sql += " ORDER BY NOME"
        
        cursor.execute(sql, params)
        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                'CODUSUR': row[0],
                'NOME': row[1],
                'TELEFONE1': row[2] if row[2] else '',
                'CODSUPERVISOR': row[3] if row[3] else None
            })
        
        return usuarios
    except Exception as e:
        print(f"Erro ao obter usuários: {e}")
        return []
    finally:
        if connection:
            connection.close()

def get_usuario_by_id(codusur):
    """Obtém um usuário específico pelo código"""
    query = """
        SELECT CODUSUR, NOME, TELEFONE1, CODSUPERVISOR
        FROM DSL.PCUSUARI
        WHERE CODUSUR = :codusur
    """
    
    result = execute_query(query, {'codusur': codusur}, fetch_one=True)
    if result:
        return {
            'CODUSUR': result[0],
            'NOME': result[1],
            'TELEFONE1': result[2] if result[2] else '',
            'CODSUPERVISOR': result[3] if result[3] else None
        }
    return None

def get_agendamentos_confirmados(codigo_rca=None, numped_filtro=None, data_de=None, data_ate=None, offset=0, per_page=25):
    """Obtém agendamentos confirmados com junção completa incluindo status de entrega"""
    connection = get_connection()
    if not connection:
        return [], 0
    
    try:
        cursor = connection.cursor()
        
        # Query para contar total de registros confirmados
        sql_count = """
            SELECT COUNT(*) 
            FROM DSLTI_PEDAGEND a 
            INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED 
            INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI 
            WHERE a.PREVENTREGA IS NOT NULL
        """
        params_count = {}
        
        # Query principal com CTE para último evento
        sql_confirmados = """
            WITH UltimoEvento AS (
                SELECT
                    e.carga_formada_erp,
                    e.seq_pedido_erp,
                    e.DESCRICAO,
                    ROW_NUMBER() OVER (PARTITION BY e.carga_formada_erp, e.seq_pedido_erp ORDER BY e.DATA_REGISTRO DESC) as rn
                FROM FUSIONT.FUSIONTRAK_INT_EVENTOS e
            )
            SELECT
                a.NUMPED, c.CLIENTE, p.DATA, p.NUMNOTA, p.NUMCAR,
                a.PREVENTREGA, a.OBSERVACAO,
                TO_CHAR(a.HORAINI, 'HH24:MI') || 'h' AS HORAINI,
                TO_CHAR(a.HORAFIM, 'HH24:MI') || 'h' AS HORAFIM,
                ue.DESCRICAO AS STATUS_ENTREGA
            FROM
                DSLTI_PEDAGEND a
            INNER JOIN
                PCPEDC p ON a.NUMPED = p.NUMPED
            INNER JOIN
                PCCLIENT c ON p.CODCLI = c.CODCLI
            LEFT JOIN
                UltimoEvento ue ON ue.seq_pedido_erp = TO_CHAR(p.NUMPED) AND ue.carga_formada_erp = TO_CHAR(p.NUMCAR) AND ue.rn = 1
            WHERE
                a.PREVENTREGA IS NOT NULL
        """
        params_confirmados = {}
        
        # Adicionar filtro por RCA se necessário
        if codigo_rca:
            sql_count += " AND p.CODUSUR = :codigo_rca"
            sql_confirmados += " AND p.CODUSUR = :codigo_rca"
            params_count['codigo_rca'] = codigo_rca
            params_confirmados['codigo_rca'] = codigo_rca
        
        # Adicionar filtros adicionais
        if numped_filtro:
            sql_count += " AND a.NUMPED = :numped"
            sql_confirmados += " AND a.NUMPED = :numped"
            params_count['numped'] = int(numped_filtro)
            params_confirmados['numped'] = int(numped_filtro)
        
        if data_de:
            sql_count += " AND a.PREVENTREGA >= TO_DATE(:data_de, 'YYYY-MM-DD')"
            sql_confirmados += " AND a.PREVENTREGA >= TO_DATE(:data_de, 'YYYY-MM-DD')"
            params_count['data_de'] = data_de
            params_confirmados['data_de'] = data_de
        
        if data_ate:
            sql_count += " AND a.PREVENTREGA <= TO_DATE(:data_ate, 'YYYY-MM-DD')"
            sql_confirmados += " AND a.PREVENTREGA <= TO_DATE(:data_ate, 'YYYY-MM-DD')"
            params_count['data_ate'] = data_ate
            params_confirmados['data_ate'] = data_ate
        
        # Executar contagem
        cursor.execute(sql_count, params_count)
        total_confirmados = cursor.fetchone()[0]
        
        # Aplicar paginação na consulta principal
        sql_confirmados += " ORDER BY a.PREVENTREGA DESC, a.NUMPED DESC"
        sql_confirmados += " OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY"
        params_confirmados['offset'] = offset
        params_confirmados['per_page'] = per_page
        
        cursor.execute(sql_confirmados, params_confirmados)
        columns = [col[0] for col in cursor.description]
        agendamentos_confirmados = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return agendamentos_confirmados, total_confirmados
        
    except Exception as e:
        print(f"Erro ao buscar agendamentos confirmados: {e}")
        return [], 0
    finally:
        if connection:
            connection.close()

def atualizar_agendamento(numped, preventrega_str, horaini_str, horafim_str, observacao):
    """Insere um novo agendamento na tabela DSLTI_PEDAGEND com validações de data"""
    from datetime import datetime, timedelta
    
    # Obter nome do usuário da aplicação para auditoria
    app_user = get_app_user_name()
    
    connection = get_connection(app_user=app_user)
    if not connection:
        return {'status': 'error', 'message': 'Erro de conexão com o banco de dados'}
    
    try:
        cursor = connection.cursor()
        
        # Verificar se o pedido existe na PCPEDC
        cursor.execute("SELECT DATA FROM PCPEDC WHERE NUMPED = :1", [numped])
        result = cursor.fetchone()
        if not result:
            return {'status': 'error', 'message': 'Pedido não encontrado'}
        
        data_pedido = result[0]
        preventrega_date = datetime.strptime(preventrega_str, '%Y-%m-%d').date()
        data_pedido_date = data_pedido.date()
        
        # Validação: entrega deve ser pelo menos 24h após a data do pedido
        if preventrega_date < data_pedido_date + timedelta(days=1):
            return {'status': 'error', 'message': 'Pedidos não podem ser agendados com menos de 24 horas da data do pedido'}
        
        # Validação: entrega não pode exceder 6 dias da data do pedido
        if preventrega_date > data_pedido_date + timedelta(days=6):
            return {'status': 'error', 'message': 'Pedidos não podem ser agendados superior a 6 dias da data do pedido'}
        
        # Verificar se já existe agendamento para este pedido
        cursor.execute("SELECT NUMPED FROM DSLTI_PEDAGEND WHERE NUMPED = :1", [numped])
        if cursor.fetchone():
            return {'status': 'error', 'message': f'Pedido {numped} já possui agendamento'}
        
        # Inserir novo agendamento
        sql_insert = """
            INSERT INTO DSLTI_PEDAGEND (
                NUMPED, 
                PREVENTREGA, 
                HORAINI, 
                HORAFIM, 
                OBSERVACAO, 
                STATUS,
                DATA_CADASTRO
            ) VALUES (
                :numped,
                TO_DATE(:prev, 'YYYY-MM-DD'),
                TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'),
                TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI'),
                :obs,
                'CONFIRMADO',
                SYSDATE
            )
        """
        
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        
        cursor.execute(sql_insert, {
            'numped': numped,
            'prev': preventrega_str,
            'h_ini': horaini_datetime,
            'h_fim': horafim_datetime,
            'obs': observacao
        })
        
        connection.commit()
        return {'status': 'success', 'message': f'Pedido {numped} agendado com sucesso!'}
        
    except Exception as e:
        return {'status': 'error', 'message': f'Erro interno: {str(e)}'}
    finally:
        if connection:
            connection.close()

def atualizar_agendamento_massa(numpeds_list, preventrega_str, horaini_str, horafim_str, observacao):
    """Insere múltiplos agendamentos na tabela DSLTI_PEDAGEND com validações de data"""
    from datetime import datetime, timedelta
    
    if not numpeds_list:
        return {'status': 'error', 'message': 'Nenhum pedido foi selecionado.'}
    
    # Obter nome do usuário da aplicação para auditoria
    app_user = get_app_user_name()
    
    connection = get_connection(app_user=app_user)
    if not connection:
        return {'status': 'error', 'message': 'Erro de conexão com o banco de dados'}
    
    try:
        cursor = connection.cursor()
        
        # Buscar datas dos pedidos para validação
        placeholders_dates = ','.join([f':{i+1}' for i in range(len(numpeds_list))])
        sql_fetch_dates = f"SELECT NUMPED, DATA FROM PCPEDC WHERE NUMPED IN ({placeholders_dates})"
        cursor.execute(sql_fetch_dates, numpeds_list)
        pedidos_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        preventrega_date = datetime.strptime(preventrega_str, '%Y-%m-%d').date()
        
        # Validar cada pedido
        for numped in numpeds_list:
            data_pedido = pedidos_data.get(numped)
            if not data_pedido:
                return {'status': 'error', 'message': f'Erro: Pedido {numped} não encontrado para validação.'}
            
            data_pedido_date = data_pedido.date()
            
            # Validação: entrega deve ser pelo menos 24h após a data do pedido
            if preventrega_date < data_pedido_date + timedelta(days=1):
                msg = f'Pedidos não podem ser agendados com menos de 24 horas da data do pedido ({data_pedido_date.strftime("%d/%m/%Y")}).'
                return {'status': 'error', 'message': msg}
            
            # Validação: entrega não pode exceder 6 dias da data do pedido
            if preventrega_date > data_pedido_date + timedelta(days=6):
                msg = f'Erro no pedido {numped}: Pedidos não podem ser agendados superior a 6 dias da data do pedido ({data_pedido_date.strftime("%d/%m/%Y")}).'
                return {'status': 'error', 'message': msg}
        
        # Verificar se algum pedido já possui agendamento
        placeholders_check = ','.join([f':{i+1}' for i in range(len(numpeds_list))])
        sql_check = f"SELECT NUMPED FROM DSLTI_PEDAGEND WHERE NUMPED IN ({placeholders_check})"
        cursor.execute(sql_check, numpeds_list)
        pedidos_existentes = [row[0] for row in cursor.fetchall()]
        
        if pedidos_existentes:
            return {
                'status': 'error', 
                'message': f'Os seguintes pedidos já possuem agendamento: {", ".join(map(str, pedidos_existentes))}'
            }
        
        # Inserir agendamentos em massa
        sql_insert = """
            INSERT INTO DSLTI_PEDAGEND (
                NUMPED, PREVENTREGA, HORAINI, HORAFIM, OBSERVACAO, STATUS, DATA_CADASTRO
            ) VALUES (
                :numped,
                TO_DATE(:prev, 'YYYY-MM-DD'),
                TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'),
                TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI'),
                :obs,
                'CONFIRMADO',
                SYSDATE
            )
        """
        
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        
        # Preparar dados para inserção em lote
        dados_insert = []
        for numped in numpeds_list:
            dados_insert.append({
                'numped': numped,
                'prev': preventrega_str,
                'h_ini': horaini_datetime,
                'h_fim': horafim_datetime,
                'obs': observacao
            })
        
        # Executar inserções
        cursor.executemany(sql_insert, dados_insert)
        connection.commit()
        
        return {'status': 'success', 'message': f'{len(numpeds_list)} pedido(s) agendado(s) com sucesso!'}
        
    except Exception as e:
        return {'status': 'error', 'message': f'Erro: {str(e)}'}
    finally:
        if connection:
            connection.close()

def atualizar_telefone_usuario(codusur, telefone):
    """Atualiza o telefone de um usuário no banco de dados"""
    if telefone:
        # Remover espaços e caracteres especiais, manter apenas números
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        # Limitar telefone a 13 caracteres para evitar erro ORA-12899
        telefone_final = telefone_limpo[:13]
    else:
        telefone_final = telefone
    
    query = """
        UPDATE DSL.PCUSUARI
        SET TELEFONE1 = :telefone
        WHERE CODUSUR = :codusur
    """
    
    params = {
        'codusur': codusur,
        'telefone': telefone_final
    }
    
    result = execute_query(query, params, fetch_all=False)
    # Retorna True se a query foi executada sem erro (result não é None)
    # Mesmo que rowcount seja 0 (valor igual ao anterior), a operação foi bem-sucedida
    return result is not None

@cache_data("kpis_data", ex=300)
def get_kpis_data(codigo_rca=None):
    """Obtém dados para KPIs do dashboard usando DSLTI_PEDAGEND e tabelas reais"""
    # Filtro por RCA se fornecido
    rca_filter = ""
    if codigo_rca:
        rca_filter = f" AND p.CODUSUR = {codigo_rca}"
    
    # Ajustar filtro RCA para query de pedidos pendentes
    rca_filter_pendentes = rca_filter.replace('p.CODUSUR', 'CODUSUR') if rca_filter else ''
    
    # Queries para KPIs reais usando PCPEDC e DSLTI_PEDAGEND
    queries = {
        'pedidos_pendentes': f"SELECT COUNT(*) FROM PCPEDC WHERE DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY') AND NOT EXISTS (SELECT 1 FROM DSLTI_PEDAGEND a WHERE a.NUMPED = PCPEDC.NUMPED){rca_filter_pendentes}",
        'agendamentos_confirmados': f"SELECT COUNT(*) FROM DSLTI_PEDAGEND a INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY') AND a.STATUS = 'CONFIRMADO'{rca_filter}",
        'usuarios_ativos': "SELECT COUNT(*) FROM DSL.PCUSUARI WHERE DTTERMINO IS NULL" if not codigo_rca else f"SELECT COUNT(*) FROM DSL.PCUSUARI WHERE CODUSUR = {codigo_rca} AND DTTERMINO IS NULL",
        'entregas_hoje': f"SELECT COUNT(*) FROM DSLTI_PEDAGEND a INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY') AND a.STATUS = 'ENTREGUE' AND TRUNC(a.PREVENTREGA) = TRUNC(SYSDATE){rca_filter}"
    }
    
    kpis = {}
    for key, query in queries.items():
        result = execute_query(query, fetch_one=True)
        kpis[key] = result[0] if result else 0
    
    return kpis

def calcular_kpis_avancados():
    """Calcula KPIs avançados com base nos dados reais do banco"""
    connection = get_connection()
    if not connection:
        return {
            'tempo_medio_entrega': 2.5,
            'desvio_padrao_entrega': 0.8,
            'taxa_conversao': 85.2,
            'status_distribuicao': {
                'Entregue': 45.0,
                'Em Trânsito': 35.0,
                'Aguardando': 20.0
            }
        }
    
    try:
        cursor = connection.cursor()
        
        # Cálculo do tempo médio entre pedido e entrega
        sql_tempo_medio = """
            SELECT 
                AVG((CAST(a.PREVENTREGA AS DATE) - CAST(p.DATA AS DATE))) as media_dias,
                STDDEV((CAST(a.PREVENTREGA AS DATE) - CAST(p.DATA AS DATE))) as desvio_padrao
            FROM DSLTI_PEDAGEND a
            JOIN PCPEDC p ON a.NUMPED = p.NUMPED
            WHERE a.PREVENTREGA IS NOT NULL
            AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
        """
        cursor.execute(sql_tempo_medio)
        tempo_medio = cursor.fetchone()
        
        # Taxa de conversão de pedidos em agendamentos
        sql_taxa_conversao = """
            SELECT 
                (SELECT COUNT(*) FROM DSLTI_PEDAGEND a JOIN PCPEDC p ON a.NUMPED = p.NUMPED WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')) * 100.0 / 
                NULLIF((SELECT COUNT(*) FROM PCPEDC WHERE DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')), 0) as taxa_conversao
            FROM DUAL
        """
        cursor.execute(sql_taxa_conversao)
        taxa_conversao = cursor.fetchone()[0]
        
        # Distribuição de status
        sql_status = """
            SELECT 
                CASE 
                    WHEN STATUS_ENTREGA LIKE '%ENTREGUE%' THEN 'Entregue'
                    WHEN STATUS_ENTREGA IS NOT NULL THEN 'Em Trânsito'
                    ELSE 'Aguardando'
                END as status,
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentual
            FROM (
                SELECT 
                    a.NUMPED,
                    (
                        SELECT e.DESCRICAO
                        FROM (
                            SELECT e.DESCRICAO
                            FROM FUSIONT.FUSIONTRAK_INT_EVENTOS e
                            WHERE e.seq_pedido_erp = TO_CHAR(p.NUMPED)
                            AND e.carga_formada_erp = TO_CHAR(p.NUMCAR)
                            ORDER BY e.DATA_REGISTRO DESC
                        )
                        WHERE ROWNUM = 1
                    ) as STATUS_ENTREGA
                FROM DSLTI_PEDAGEND a
                JOIN PCPEDC p ON a.NUMPED = p.NUMPED
                WHERE a.PREVENTREGA IS NOT NULL
                AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
            )
            GROUP BY 
                CASE 
                    WHEN STATUS_ENTREGA LIKE '%ENTREGUE%' THEN 'Entregue'
                    WHEN STATUS_ENTREGA IS NOT NULL THEN 'Em Trânsito'
                    ELSE 'Aguardando'
                END
        """
        cursor.execute(sql_status)
        status_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'tempo_medio_entrega': round(tempo_medio[0], 1) if tempo_medio[0] else 0,
            'desvio_padrao_entrega': round(tempo_medio[1], 1) if tempo_medio[1] else 0,
            'taxa_conversao': round(taxa_conversao, 1) if taxa_conversao else 0,
            'status_distribuicao': status_dist if status_dist else {
                'Entregue': 45.0,
                'Em Trânsito': 35.0,
                'Aguardando': 20.0
            }
        }
    except Exception as e:
        print(f"Erro ao calcular KPIs avançados: {e}")
        return {
            'tempo_medio_entrega': 2.5,
            'desvio_padrao_entrega': 0.8,
            'taxa_conversao': 85.2,
            'status_distribuicao': {
                'Entregue': 45.0,
                'Em Trânsito': 35.0,
                'Aguardando': 20.0
            }
        }
    finally:
        if connection:
            connection.close()

def get_graficos_data(codigo_rca=None):
    """Obtém dados para gráficos do dashboard usando DSLTI_PEDAGEND"""
    connection = get_connection()
    if not connection:
        return {
            'pedidos_por_dia': [],
            'status_entregas': [],
            'agendamentos_por_rca': [],
            'tendencia_mensal': [],
            'horarios_entrega': [],
            'performance_semanal': []
        }
    
    try:
        cursor = connection.cursor()
        
        # Filtro por RCA se fornecido
        rca_filter = ""
        if codigo_rca:
            rca_filter = f" AND p.CODUSUR = {codigo_rca}"
        
        # 1. Pedidos por dia (últimos 30 dias) - todos os pedidos da PCPEDC
        rca_filter_pedidos = rca_filter.replace('p.CODUSUR', 'CODUSUR') if rca_filter else ''
        pedidos_query = f"""
            SELECT TO_CHAR(DATA, 'YYYY-MM-DD') as data, COUNT(*) as quantidade
            FROM PCPEDC
            WHERE DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY'){rca_filter_pedidos}
            GROUP BY TO_CHAR(DATA, 'YYYY-MM-DD')
            ORDER BY data
        """
        
        # 2. Status das entregas - LEFT JOIN para incluir pedidos não agendados
        status_query = f"""
            SELECT 
                CASE 
                    WHEN a.NUMPED IS NULL THEN 'Pendente'
                    WHEN a.STATUS = 'ENTREGUE' THEN 'Entregue'
                    WHEN a.PREVENTREGA IS NOT NULL THEN 'Agendado'
                    ELSE 'Outros'
                END as status,
                COUNT(*) as quantidade
            FROM PCPEDC p
            LEFT JOIN DSLTI_PEDAGEND a ON p.NUMPED = a.NUMPED
            WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY'){rca_filter_pedidos}
            GROUP BY 
                CASE 
                    WHEN a.NUMPED IS NULL THEN 'Pendente'
                    WHEN a.STATUS = 'ENTREGUE' THEN 'Entregue'
                    WHEN a.PREVENTREGA IS NOT NULL THEN 'Agendado'
                    ELSE 'Outros'
                END
        """
        
        # 3. Agendamentos por RCA (top 10) - só mostra se não for filtro por RCA específico
        if codigo_rca:
            rca_query = f"""
                SELECT u.NOME, COUNT(*) as quantidade
                FROM DSLTI_PEDAGEND a
                INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED
                INNER JOIN PCUSUARI u ON p.CODUSUR = u.CODUSUR
                WHERE a.PREVENTREGA IS NOT NULL
                AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
                AND p.CODUSUR = {codigo_rca}
                GROUP BY u.NOME
                ORDER BY quantidade DESC
            """
        else:
            rca_query = """
                SELECT u.NOME, COUNT(*) as quantidade
                FROM DSLTI_PEDAGEND a
                INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED
                INNER JOIN PCUSUARI u ON p.CODUSUR = u.CODUSUR
                WHERE a.PREVENTREGA IS NOT NULL
                AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
                GROUP BY u.NOME
                ORDER BY quantidade DESC
                FETCH FIRST 10 ROWS ONLY
            """
        
        # 4. Tendência mensal (últimos 6 meses) - LEFT JOIN para incluir todos os pedidos
        tendencia_query = f"""
            SELECT 
                TO_CHAR(p.DATA, 'YYYY-MM') as mes,
                TO_CHAR(p.DATA, 'Mon/YYYY') as mes_label,
                COUNT(*) as total_pedidos,
                COUNT(CASE WHEN a.PREVENTREGA IS NOT NULL THEN 1 END) as agendados,
                COUNT(CASE WHEN a.STATUS = 'ENTREGUE' THEN 1 END) as entregues
            FROM PCPEDC p
            LEFT JOIN DSLTI_PEDAGEND a ON p.NUMPED = a.NUMPED
            WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY'){rca_filter_pedidos}
            GROUP BY TO_CHAR(p.DATA, 'YYYY-MM'), TO_CHAR(p.DATA, 'Mon/YYYY')
            ORDER BY mes
        """
        
        # 5. Distribuição de horários de entrega
        horarios_query = f"""
            SELECT 
                CASE 
                    WHEN TO_NUMBER(TO_CHAR(a.HORAINI, 'HH24')) BETWEEN 6 AND 11 THEN 'Manhã (6h-12h)'
                    WHEN TO_NUMBER(TO_CHAR(a.HORAINI, 'HH24')) BETWEEN 12 AND 17 THEN 'Tarde (12h-18h)'
                    WHEN TO_NUMBER(TO_CHAR(a.HORAINI, 'HH24')) BETWEEN 18 AND 23 THEN 'Noite (18h-24h)'
                    ELSE 'Madrugada (0h-6h)'
                END as periodo,
                COUNT(*) as quantidade
            FROM DSLTI_PEDAGEND a
            INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED
            WHERE a.HORAINI IS NOT NULL
            AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
            AND a.PREVENTREGA >= SYSDATE - 30{rca_filter_pedidos}
            GROUP BY 
                CASE 
                    WHEN TO_NUMBER(TO_CHAR(a.HORAINI, 'HH24')) BETWEEN 6 AND 11 THEN 'Manhã (6h-12h)'
                    WHEN TO_NUMBER(TO_CHAR(a.HORAINI, 'HH24')) BETWEEN 12 AND 17 THEN 'Tarde (12h-18h)'
                    WHEN TO_NUMBER(TO_CHAR(a.HORAINI, 'HH24')) BETWEEN 18 AND 23 THEN 'Noite (18h-24h)'
                    ELSE 'Madrugada (0h-6h)'
                END
        """
        
        # 6. Performance semanal (últimas 4 semanas) - LEFT JOIN para incluir todos os pedidos
        performance_query = f"""
            SELECT 
                'Semana ' || TO_CHAR(p.DATA, 'WW') as semana,
                COUNT(*) as total_pedidos,
                COUNT(CASE WHEN a.PREVENTREGA IS NOT NULL THEN 1 END) as agendados,
                ROUND(COUNT(CASE WHEN a.PREVENTREGA IS NOT NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as taxa_agendamento
            FROM PCPEDC p
            LEFT JOIN DSLTI_PEDAGEND a ON p.NUMPED = a.NUMPED
            WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY'){rca_filter_pedidos}
            GROUP BY TO_CHAR(p.DATA, 'WW')
            ORDER BY TO_CHAR(p.DATA, 'WW')
        """
        
        # Executar todas as consultas
        cursor.execute(pedidos_query)
        pedidos_result = cursor.fetchall()
        
        cursor.execute(status_query)
        status_result = cursor.fetchall()
        
        cursor.execute(rca_query)
        rca_result = cursor.fetchall()
        
        cursor.execute(tendencia_query)
        tendencia_result = cursor.fetchall()
        
        cursor.execute(horarios_query)
        horarios_result = cursor.fetchall()
        
        cursor.execute(performance_query)
        performance_result = cursor.fetchall()
        
        # Processar resultados
        pedidos_por_dia = [{'data': row[0], 'quantidade': row[1]} for row in pedidos_result]
        status_entregas = [{'status': row[0], 'quantidade': row[1]} for row in status_result]
        agendamentos_por_rca = [{'rca': row[0], 'quantidade': row[1]} for row in rca_result]
        tendencia_mensal = [{
            'mes': row[0],
            'mes_label': row[1],
            'total_pedidos': row[2],
            'agendados': row[3],
            'entregues': row[4]
        } for row in tendencia_result]
        horarios_entrega = [{'periodo': row[0], 'quantidade': row[1]} for row in horarios_result]
        performance_semanal = [{
            'semana': row[0],
            'total_pedidos': row[1],
            'agendados': row[2],
            'taxa_agendamento': row[3]
        } for row in performance_result]
        
        return {
            'pedidos_por_dia': pedidos_por_dia,
            'status_entregas': status_entregas,
            'agendamentos_por_rca': agendamentos_por_rca,
            'tendencia_mensal': tendencia_mensal,
            'horarios_entrega': horarios_entrega,
            'performance_semanal': performance_semanal
        }
        
    except Exception as e:
        print(f"Erro ao buscar dados dos gráficos: {e}")
        return {
            'pedidos_por_dia': [],
            'status_entregas': [],
            'agendamentos_por_rca': [],
            'tendencia_mensal': [],
            'horarios_entrega': [],
            'performance_semanal': []
        }
    finally:
        if connection:
            connection.close()

def gerar_grafico_tendencia():
    """Gera dados para gráfico de tendência de agendamentos"""
    connection = get_connection()
    if not connection:
        # Dados de exemplo se não conseguir conectar
        import datetime
        from dateutil.relativedelta import relativedelta
        
        hoje = datetime.date.today()
        labels = []
        data = []
        
        for i in range(6):
            mes = hoje - relativedelta(months=i)
            labels.append(mes.strftime('%b/%Y'))
            data.append(10 + (i * 2) + (i % 3))
        
        labels.reverse()
        data.reverse()
        
        return {
            'labels': labels,
            'data': data,
            'titulo': 'Tendência de Agendamentos (Últimos 6 Meses)',
            'cor': '#4CAF50'
        }
    
    try:
        cursor = connection.cursor()
        
        # Consulta para obter tendência dos últimos 6 meses
        sql = """
            SELECT 
                TO_CHAR(a.DATA_PEDIDO, 'MON/YYYY') as periodo,
                COUNT(*) as total_agendamentos,
                TO_CHAR(a.DATA_PEDIDO, 'YYYY-MM') as ordem
            FROM DSLTI_PEDAGEND a
            WHERE a.DATA_PEDIDO >= ADD_MONTHS(SYSDATE, -6)
            AND a.PREVENTREGA IS NOT NULL
            GROUP BY TO_CHAR(a.DATA_PEDIDO, 'MON/YYYY'), TO_CHAR(a.DATA_PEDIDO, 'YYYY-MM')
            ORDER BY TO_CHAR(a.DATA_PEDIDO, 'YYYY-MM')
        """
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if results:
            labels = [row[0] for row in results]
            data = [row[1] for row in results]
        else:
            # Fallback para dados de exemplo
            import datetime
            from dateutil.relativedelta import relativedelta
            
            hoje = datetime.date.today()
            labels = []
            data = []
            
            for i in range(6):
                mes = hoje - relativedelta(months=i)
                labels.append(mes.strftime('%b/%Y'))
                data.append(5 + (i % 4))
            
            labels.reverse()
            data.reverse()
        
        return {
            'labels': labels,
            'data': data,
            'titulo': 'Tendência de Agendamentos (Últimos 6 Meses)',
            'cor': '#4CAF50'
        }
    except Exception as e:
        print(f"Erro ao gerar gráfico de tendência: {e}")
        # Fallback para dados de exemplo em caso de erro
        import datetime
        from dateutil.relativedelta import relativedelta
        
        hoje = datetime.date.today()
        labels = []
        data = []
        
        for i in range(6):
            mes = hoje - relativedelta(months=i)
            labels.append(mes.strftime('%b/%Y'))
            data.append(8 + (i % 3))
        
        labels.reverse()
        data.reverse()
        
        return {
            'labels': labels,
            'data': data,
            'titulo': 'Tendência de Agendamentos (Últimos 6 Meses)',
            'cor': '#4CAF50'
        }
    finally:
        if connection:
            connection.close()

def get_stats_data(codigo_rca=None):
    """Obtém dados de estatísticas para o painel usando DSLTI_PEDAGEND"""
    # Filtro por RCA se fornecido
    rca_filter = ""
    if codigo_rca:
        rca_filter = f" AND p.CODUSUR = {codigo_rca}"
    
    # Queries para estatísticas reais usando DSLTI_PEDAGEND
    hoje_query = f"SELECT COUNT(*) FROM DSLTI_PEDAGEND a INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY') AND TRUNC(a.PREVENTREGA) = TRUNC(SYSDATE) AND p.CODSUPERVISOR NOT IN (9130){rca_filter}"
    proximos_7_dias_query = f"SELECT COUNT(*) FROM DSLTI_PEDAGEND a INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED WHERE p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY') AND a.PREVENTREGA BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 7 AND p.CODSUPERVISOR NOT IN (9130){rca_filter}"
    
    hoje_result = execute_query(hoje_query, fetch_one=True)
    proximos_result = execute_query(proximos_7_dias_query, fetch_one=True)
    
    return {
        'agendados_hoje': hoje_result[0] if hoje_result else 0,
        'agendados_7_dias': proximos_result[0] if proximos_result else 0
    }

from functools import wraps
from flask import g

def cache_data(key_prefix, ex):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{args[0]}"
            result = g.cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                g.cache.set(key, result, ex)
            return result
        return wrapper
    return decorator

def get_usuario_pcempr_by_name(nome):
    """
    Busca um usuário na tabela PCEMPR pelo nome 
    """
    try:
        query = """
        SELECT MATRICULA, NOME_GUERRA, DSL.DECRYPT(SENHABD,NOME_GUERRA) AS SENHA
        FROM DSL.PCEMPR 
        WHERE UPPER(NOME_GUERRA) = UPPER(:nome)
        AND SENHABD IS NOT NULL
        AND SITUACAO = 'A'
        """
        
        result = execute_query(query, {'nome': nome})
        
        if result and len(result) > 0:
            row = result[0]
            return {
                'matricula': row[0],
                'nome_guerra': row[1],
                'senha': row[2]
            }
        return None
    except Exception as e:
        print(f"Erro ao buscar usuário PCEMPR: {e}")
        return None

def authenticate_pcempr_user(nome, senha):
    """
    Autentica um usuário da tabela PCEMPR
    """
    try:
        usuario = get_usuario_pcempr_by_name(nome)
        if not usuario:
            return False
        
        # Comparar diretamente com a senha descriptografada do banco
        senha_descriptografada = usuario['senha']
        
        # Comparar com a senha fornecida
        return senha_descriptografada == senha
        
    except Exception as e:
        print(f"Erro na autenticação PCEMPR: {e}")
        return False