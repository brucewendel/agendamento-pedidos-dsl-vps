import os
import oracledb
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, date, timedelta

# Inicializa o modo "Thick" para compatibilidade com bancos Oracle mais antigos
oracledb.init_oracle_client()

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# --- Configuração da Aplicação Flask ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- Configurações de Conexão com o Banco Oracle (lidas do .env) ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")

# Função auxiliar para converter dados do Oracle em dicionários aninháveis em JSON
def make_dicts(cursor, description):
    columns = [col[0].lower() for col in description]
    return [
        {col: val.isoformat() if isinstance(val, (datetime, date)) else val for col, val in zip(columns, row)}
        for row in cursor.fetchall()
    ]

@app.route('/')
def index():
    return redirect(url_for('listar_painel'))

@app.route('/painel')
def listar_painel():
    connection = None
    pedidos_pendentes = []
    agendamentos_confirmados = []
    
    active_tab = request.args.get('active_tab', 'pendentes')

    today_str = date.today().strftime('%Y-%m-%d')
    month_ago = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    dash_de = request.args.get('dash_de', month_ago)
    dash_ate = request.args.get('dash_ate', today_str)

    stats = { 'pendentes': 0, 'agendados_hoje': 0, 'agendados_7_dias': 0 }

    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()

        # --- LÓGICA DE ESTATÍSTICAS ---
        sql_stat_pendentes = """
            SELECT COUNT(a.NUMPED) FROM YAN_PEDAGEND a
            INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED
            WHERE a.PREVENTREGA IS NULL AND TRUNC(p.DATA) BETWEEN TO_DATE(:1, 'YYYY-MM-DD') AND TO_DATE(:2, 'YYYY-MM-DD')
        """
        cursor.execute(sql_stat_pendentes, [dash_de, dash_ate])
        stats['pendentes'] = cursor.fetchone()[0]

        sql_stat_hoje = "SELECT COUNT(*) FROM YAN_PEDAGEND WHERE TRUNC(PREVENTREGA) = TRUNC(SYSDATE)"
        cursor.execute(sql_stat_hoje)
        stats['agendados_hoje'] = cursor.fetchone()[0]
        
        sql_stat_7d = "SELECT COUNT(*) FROM YAN_PEDAGEND WHERE TRUNC(PREVENTREGA) BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 6"
        cursor.execute(sql_stat_7d)
        stats['agendados_7_dias'] = cursor.fetchone()[0]
        
        # --- BUSCA DE PEDIDOS PENDENTES ---
        sql_pendentes = """
            SELECT a.NUMPED, c.CLIENTE, p.DATA, p.NUMNOTA, p.NUMCAR, a.PREVENTREGA, a.HORAINI, a.HORAFIM 
            FROM YAN_PEDAGEND a 
            INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED 
            INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI 
            WHERE a.PREVENTREGA IS NULL
        """
        params_pendentes = {}
        if active_tab == 'pendentes':
            numped_filtro = request.args.get('numped')
            data_filtro = request.args.get('data_pedido')
            if numped_filtro:
                sql_pendentes += " AND a.NUMPED = :numped"
                params_pendentes['numped'] = int(numped_filtro)
            if data_filtro:
                sql_pendentes += " AND TRUNC(p.DATA) = TO_DATE(:data_p, 'YYYY-MM-DD')"
                params_pendentes['data_p'] = data_filtro
        sql_pendentes += " ORDER BY p.DATA DESC, a.NUMPED DESC"
        cursor.execute(sql_pendentes, params_pendentes)
        columns_pendentes = [col[0] for col in cursor.description]
        pedidos_pendentes = [dict(zip(columns_pendentes, row)) for row in cursor.fetchall()]

        # --- BUSCA DE AGENDAMENTOS CONFIRMADOS ---
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
                YAN_PEDAGEND a
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
        if active_tab == 'confirmados':
            numped_filtro = request.args.get('numped')
            data_de = request.args.get('data_de')
            data_ate = request.args.get('data_ate')
            if numped_filtro:
                sql_confirmados += " AND a.NUMPED = :numped"
                params_confirmados['numped'] = int(numped_filtro)
            if data_de:
                sql_confirmados += " AND a.PREVENTREGA >= TO_DATE(:data_de, 'YYYY-MM-DD')"
                params_confirmados['data_de'] = data_de
            if data_ate:
                sql_confirmados += " AND a.PREVENTREGA <= TO_DATE(:data_ate, 'YYYY-MM-DD')"
                params_confirmados['data_ate'] = data_ate
        
        sql_confirmados += " ORDER BY a.PREVENTREGA DESC, a.NUMPED DESC"
        cursor.execute(sql_confirmados, params_confirmados)
        columns_confirmados = [col[0] for col in cursor.description]
        agendamentos_confirmados = [dict(zip(columns_confirmados, row)) for row in cursor.fetchall()]

    except oracledb.DatabaseError as e:
        error, = e.args
        flash(f"Erro de banco de dados: {error.message}", 'error')
    finally:
        if connection:
            connection.close()
            
    return render_template('painel.html', 
                           pedidos_pendentes=pedidos_pendentes, 
                           agendamentos_confirmados=agendamentos_confirmados,
                           stats=stats,
                           active_tab=active_tab,
                           dash_de=dash_de,
                           dash_ate=dash_ate)

@app.route('/pedido_detalhes/<int:numped>')
def get_pedido_detalhes(numped):
    connection = None
    data = {}
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        
        cursor_geral = connection.cursor()
        sql_geral = """SELECT p.NUMPED, p.POSICAO, p.CONDVENDA, p.DATA, p.VLTOTAL, p.VLATEND, c.CLIENTE, u.NOME AS RCA, 
                              p.OBS, p.OBS1, p.OBS2, p.NUMCAR, p.NUMTRANSVENDA
                       FROM PCPEDC p
                       JOIN PCCLIENT c ON p.CODCLI = c.CODCLI
                       JOIN PCUSUARI u ON p.CODUSUR = u.CODUSUR
                       WHERE p.NUMPED = :1"""
        cursor_geral.execute(sql_geral, [numped])
        geral_data = make_dicts(cursor_geral, cursor_geral.description)
        data['geral'] = geral_data[0] if geral_data else {}
        num_trans_venda = data.get('geral', {}).get('numtransvenda', 0)

        cursor_itens = connection.cursor()
        sql_itens = """SELECT i.NUMSEQ, i.CODPROD, p.DESCRICAO, p.EMBALAGEM, i.QT, i.PVENDA, (i.QT * i.PVENDA) AS SUBTOTAL, NVL(i.BONIFIC, 'N') AS BONIFIC
                       FROM PCPEDI i JOIN PCPRODUT p ON i.CODPROD = p.CODPROD
                       WHERE i.NUMPED = :1 ORDER BY i.NUMSEQ"""
        cursor_itens.execute(sql_itens, [numped])
        data['itens'] = make_dicts(cursor_itens, cursor_itens.description)

        cursor_cortes = connection.cursor()
        sql_cortes = """SELECT i.CODPROD, p.DESCRICAO, p.EMBALAGEM, i.QTCORTADA, i.PVENDA, (i.QTCORTADA * i.PVENDA) AS VL_TOTAL
                        FROM PCCORTEI i JOIN PCPRODUT p ON i.CODPROD = p.CODPROD
                        WHERE i.NUMPED = :1 AND i.QTCORTADA > 0 ORDER BY i.CODPROD"""
        cursor_cortes.execute(sql_cortes, [numped])
        data['cortes'] = make_dicts(cursor_cortes, cursor_cortes.description)

        cursor_cancelados = connection.cursor()
        sql_cancelados = """SELECT c.CODPROD, p.DESCRICAO, c.QT, c.PVENDA, c.HORACANC
                            FROM PCNFCANITEM c JOIN PCPRODUT p ON c.CODPROD = p.CODPROD
                            WHERE c.NUMPED = :1 AND c.NUMTRANSVENDA IS NULL ORDER BY c.CODPROD ASC"""
        cursor_cancelados.execute(sql_cancelados, [numped])
        data['cancelados'] = make_dicts(cursor_cancelados, cursor_cancelados.description)

        cursor_faltas = connection.cursor()
        sql_faltas = """SELECT i.NUMSEQ, i.CODPROD, p.DESCRICAO, p.EMBALAGEM, i.QT, i.PVENDA, (i.QT * i.PVENDA) AS SUBTOTAL
                        FROM PCFALTA i JOIN PCPRODUT p ON i.CODPROD = p.CODPROD
                        WHERE i.NUMPED = :1"""
        cursor_faltas.execute(sql_faltas, [numped])
        data['faltas'] = make_dicts(cursor_faltas, cursor_faltas.description)

        cursor_timeline = connection.cursor()
        sql_timeline = """SELECT p.NUMPED, p.POSICAO, p.DATA AS DATAPEDIDO, p.DTINICIALSEP, p.DTFINALSEP,
                                 DECODE(p.DTINICIALCHECKOUT,NULL,car.DTINICIOCHECKOUT,p.DTINICIALCHECKOUT) AS DTINICIALCHECKOUT,
                                 DECODE(p.DTFINALCHECKOUT,NULL,car.DTFIMCHECKOUT,p.DTFINALCHECKOUT) AS DTFINALCHECKOUT,
                                 p.DTFAT, car.DTSAIDAVEICULO, car.DTRETORNO, p.DTCANCEL
                          FROM PCPEDC p
                          LEFT JOIN PCCARREG car ON p.NUMCAR = car.NUMCAR
                          WHERE p.NUMPED = :1"""
        cursor_timeline.execute(sql_timeline, [numped])
        timeline_data = make_dicts(cursor_timeline, cursor_timeline.description)
        data['timeline'] = timeline_data[0] if timeline_data else {}
        
        if num_trans_venda:
            cursor_nf_cancelada = connection.cursor()
            sql_nf_cancelada = """SELECT DATACANC, VLTOTAL, MOTIVO, CODROTINA FROM PCNFCAN WHERE NUMTRANSVENDA = :1 AND NUMTRANSVENDA > 0"""
            cursor_nf_cancelada.execute(sql_nf_cancelada, [num_trans_venda])
            nf_cancelada_data = make_dicts(cursor_nf_cancelada, cursor_nf_cancelada.description)
            data['nf_cancelada'] = nf_cancelada_data[0] if nf_cancelada_data else {}

    except oracledb.DatabaseError as e:
        error, = e.args
        return jsonify({'error': f"Erro de banco de dados: {error.message}"}), 500
    except Exception as e:
        return jsonify({'error': f"Erro inesperado: {str(e)}"}), 500
    finally:
        if connection:
            connection.close()
    return jsonify(data)


@app.route('/atualizar', methods=['POST'])
def atualizar_agendamento():
    numped = request.form.get('numped')
    preventrega_str = request.form.get('preventrega')
    horaini_str = request.form.get('horaini')
    horafim_str = request.form.get('horafim')
    observacao = request.form.get('observacao')
    
    connection = None
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()
        
        cursor.execute("SELECT DATA FROM PCPEDC WHERE NUMPED = :1", [numped])
        result = cursor.fetchone()
        if not result: return jsonify({'status': 'error', 'message': f"Erro: Pedido {numped} não encontrado na PCPEDC."}), 400
        
        data_pedido = result[0]
        preventrega_date = datetime.strptime(preventrega_str, '%Y-%m-%d').date()
        data_pedido_date = data_pedido.date()

        if preventrega_date < data_pedido_date + timedelta(days=1):
            msg = f"Erro no pedido {numped}: A entrega não pode ser menos de 24h após a data do pedido ({data_pedido_date.strftime('%d/%m/%Y')})."
            return jsonify({'status': 'error', 'message': msg}), 400
        if preventrega_date > data_pedido_date + timedelta(days=6):
            msg = f"Erro no pedido {numped}: A entrega não pode exceder 6 dias da data do pedido ({data_pedido_date.strftime('%d/%m/%Y')})."
            return jsonify({'status': 'error', 'message': msg}), 400

        sql_update = """
            UPDATE YAN_PEDAGEND SET PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'),
                HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'),
                HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI'),
                OBSERVACAO = :obs
            WHERE NUMPED = :numped
        """
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        
        cursor.execute(sql_update, {'prev': preventrega_str, 'h_ini': horaini_datetime, 'h_fim': horafim_datetime, 'obs': observacao, 'numped': numped})
        connection.commit()
        return jsonify({'status': 'success', 'message': f"Pedido {numped} agendado com sucesso!"})
            
    except oracledb.DatabaseError as e:
        error, = e.args
        return jsonify({'status': 'error', 'message': f"Erro de banco de dados: {error.message}"}), 500
    finally:
        if connection: connection.close()

@app.route('/atualizar-massa', methods=['POST'])
def atualizar_agendamento_massa():
    numpeds_selecionados = request.form.get('numpeds_selecionados')
    preventrega_str = request.form.get('preventrega')
    horaini_str = request.form.get('horaini')
    horafim_str = request.form.get('horafim')
    observacao = request.form.get('observacao')

    if not numpeds_selecionados: return jsonify({'status': 'error', 'message': 'Nenhum pedido foi selecionado.'}), 400
    numped_list = [int(n) for n in numpeds_selecionados.split(',')]
    
    connection = None
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()

        placeholders_dates = ','.join([':{}'.format(i+1) for i in range(len(numped_list))])
        sql_fetch_dates = f"SELECT NUMPED, DATA FROM PCPEDC WHERE NUMPED IN ({placeholders_dates})"
        cursor.execute(sql_fetch_dates, numped_list)
        pedidos_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        preventrega_date = datetime.strptime(preventrega_str, '%Y-%m-%d').date()
        for numped in numped_list:
            data_pedido = pedidos_data.get(numped)
            if not data_pedido: return jsonify({'status': 'error', 'message': f"Erro: Pedido {numped} não encontrado para validação."}), 400
            data_pedido_date = data_pedido.date()
            if preventrega_date < data_pedido_date + timedelta(days=1):
                msg = f"Erro no pedido {numped}: A entrega deve ser no mínimo 24h após a data do pedido ({data_pedido_date.strftime('%d/%m/%Y')})."
                return jsonify({'status': 'error', 'message': msg}), 400
            if preventrega_date > data_pedido_date + timedelta(days=6):
                msg = f"Erro no pedido {numped}: A entrega não pode exceder 6 dias da data do pedido ({data_pedido_date.strftime('%d/%m/%Y')})."
                return jsonify({'status': 'error', 'message': msg}), 400
        
        placeholders_update = ','.join([':{}'.format(i+1) for i in range(len(numped_list))])
        sql_update = f"""
            UPDATE YAN_PEDAGEND SET PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'),
                HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'),
                HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI'),
                OBSERVACAO = :obs
            WHERE NUMPED IN ({placeholders_update})
        """
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        params = [preventrega_str, horaini_datetime, horafim_datetime, observacao] + numped_list
        cursor.execute(sql_update, params)
        
        connection.commit()
        return jsonify({'status': 'success', 'message': f"{cursor.rowcount} pedido(s) agendado(s) com sucesso!"})
            
    except oracledb.DatabaseError as e:
        error, = e.args
        return jsonify({'status': 'error', 'message': f"Erro de banco de dados: {error.message}"}), 500
    finally:
        if connection: connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)