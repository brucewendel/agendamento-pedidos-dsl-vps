import os
import oracledb
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, date, timedelta

oracledb.init_oracle_client()
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")


@app.route('/')
def index():
    return redirect(url_for('listar_painel'))


# No seu app.py, substitua a função listar_painel

@app.route('/painel')
def listar_painel():
    connection = None
    pedidos_pendentes = []
    agendamentos_confirmados = []
    
    active_tab = request.args.get('active_tab', 'pendentes')

    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        
        # --- BUSCA DE PEDIDOS PENDENTES (SEM ALTERAÇÃO) ---
        cursor_pendentes = connection.cursor()
        # ... (código da busca de pendentes continua o mesmo)
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
        cursor_pendentes.execute(sql_pendentes, params_pendentes)
        columns_pendentes = [col[0] for col in cursor_pendentes.description]
        pedidos_pendentes = [dict(zip(columns_pendentes, row)) for row in cursor_pendentes.fetchall()]
        cursor_pendentes.close()

        # --- BUSCA DE AGENDAMENTOS CONFIRMADOS (COM A NOVA LÓGICA) ---
        cursor_confirmados = connection.cursor()
        sql_confirmados = """
            SELECT
                a.NUMPED, c.CLIENTE, p.DATA, p.NUMNOTA, p.NUMCAR,
                a.PREVENTREGA,
                TO_CHAR(a.HORAINI, 'HH24:MI') || 'h' AS HORAINI,
                TO_CHAR(a.HORAFIM, 'HH24:MI') || 'h' AS HORAFIM,
                e.DESCRICAO AS STATUS_ENTREGA  -- << NOVA COLUNA AQUI
            FROM
                YAN_PEDAGEND a
            INNER JOIN
                PCPEDC p ON a.NUMPED = p.NUMPED
            INNER JOIN
                PCCLIENT c ON p.CODCLI = c.CODCLI
            LEFT JOIN -- << NOVO JOIN AQUI
                FUSIONT.FUSIONTRAK_INT_EVENTOS e ON e.seq_pedido_erp = TO_CHAR(p.NUMPED) AND e.carga_formada_erp = TO_CHAR(p.NUMCAR)
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
        cursor_confirmados.execute(sql_confirmados, params_confirmados)
        columns_confirmados = [col[0] for col in cursor_confirmados.description]
        agendamentos_confirmados = [dict(zip(columns_confirmados, row)) for row in cursor_confirmados.fetchall()]
        cursor_confirmados.close()

    except oracledb.DatabaseError as e:
        error, = e.args
        flash(f"Erro de banco de dados: {error.message}", 'error')
    finally:
        if connection:
            connection.close()

    # --- CÁLCULO DAS ESTATÍSTICAS (SEM ALTERAÇÃO) ---
    stats = { 'pendentes': len(pedidos_pendentes), 'agendados_hoje': 0, 'agendados_7_dias': 0 }
    hoje = date.today()
    proximos_7_dias = hoje + timedelta(days=7)
    for agendamento in agendamentos_confirmados:
        if agendamento['PREVENTREGA'] and agendamento['PREVENTREGA'].date() == hoje:
            stats['agendados_hoje'] += 1
        if agendamento['PREVENTREGA'] and hoje <= agendamento['PREVENTREGA'].date() < proximos_7_dias:
            stats['agendados_7_dias'] += 1
            
    return render_template('painel.html', 
                           pedidos_pendentes=pedidos_pendentes, 
                           agendamentos_confirmados=agendamentos_confirmados,
                           stats=stats,
                           active_tab=active_tab)

# --- ROTAS DE ATUALIZAÇÃO (sem alterações) ---
@app.route('/atualizar', methods=['POST'])
def atualizar_agendamento():
    # ... (código desta função permanece o mesmo)
    numped = request.form.get('numped')
    preventrega_str = request.form.get('preventrega')
    horaini_str = request.form.get('horaini')
    horafim_str = request.form.get('horafim')
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
        sql_update = "UPDATE YAN_PEDAGEND SET PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'), HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'), HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI') WHERE NUMPED = :numped"
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        cursor.execute(sql_update, {'prev': preventrega_str, 'h_ini': horaini_datetime, 'h_fim': horafim_datetime, 'numped': numped})
        connection.commit()
        return jsonify({'status': 'success', 'message': f"Pedido {numped} agendado com sucesso!"})
    except oracledb.DatabaseError as e:
        error, = e.args
        return jsonify({'status': 'error', 'message': f"Erro de banco de dados: {error.message}"}), 500
    finally:
        if connection: connection.close()

@app.route('/atualizar-massa', methods=['POST'])
def atualizar_agendamento_massa():
    # ... (código desta função permanece o mesmo)
    numpeds_selecionados = request.form.get('numpeds_selecionados')
    preventrega_str = request.form.get('preventrega')
    horaini_str = request.form.get('horaini')
    horafim_str = request.form.get('horafim')
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
        sql_update = f"UPDATE YAN_PEDAGEND SET PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'), HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'), HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI') WHERE NUMPED IN ({placeholders_update})"
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        params = [preventrega_str, horaini_datetime, horafim_datetime] + numped_list
        cursor.execute(sql_update, params)
        connection.commit()
        return jsonify({'status': 'success', 'message': f"{cursor.rowcount} pedido(s) agendado(s) com sucesso!"})
    except oracledb.DatabaseError as e:
        error, = e.args
        return jsonify({'status': 'error', 'message': f"Erro de banco de dados: {error.message}"}), 500
    finally:
        if connection: connection.close()


if __name__ == '__main__':
    app.run(debug=True)