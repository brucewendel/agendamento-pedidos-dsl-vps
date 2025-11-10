import os
import oracledb
from dotenv import load_dotenv
from flask import Flask, render_template, request, flash, redirect, url_for
from datetime import datetime, timedelta

# Inicializa o modo "Thick"
oracledb.init_oracle_client()
load_dotenv()

# --- Configuração da Aplicação e Conexão ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")


# --- Rotas de Visualização ---
@app.route('/')
def index():
    return redirect(url_for('listar_pedidos'))

@app.route('/pedidos')
def listar_pedidos():
    connection = None
    pedidos = []
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()
        numped_filtro = request.args.get('numped')
        data_filtro = request.args.get('data_pedido')

        # Query com prefixo de schema DSL.
        sql_select = """
            SELECT
                a.NUMPED, c.CLIENTE, p.DATA, a.PREVENTREGA, a.HORAINI, a.HORAFIM
            FROM DSL.YAN_PEDAGEND a
            INNER JOIN DSL.PCPEDC p ON a.NUMPED = p.NUMPED
            INNER JOIN DSL.PCCLIENT c ON p.CODCLI = c.CODCLI
            WHERE
                a.PREVENTREGA IS NULL
        """
        params = {}
        if numped_filtro:
            sql_select += " AND a.NUMPED = :numped"
            params['numped'] = int(numped_filtro)
        if data_filtro:
            sql_select += " AND TRUNC(p.DATA) = TO_DATE(:data_p, 'YYYY-MM-DD')"
            params['data_p'] = data_filtro
        sql_select += " ORDER BY p.DATA DESC, a.NUMPED DESC"
        
        cursor.execute(sql_select, params)
        columns = [col[0] for col in cursor.description]
        pedidos = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    except oracledb.DatabaseError as e:
        error, = e.args
        flash(f"Erro de banco de dados ao buscar pedidos: {error.message}", 'error')
    finally:
        if connection:
            connection.close()
    return render_template('pedidos.html', pedidos=pedidos)

@app.route('/agendamentos')
def listar_agendamentos():
    connection = None
    agendamentos = []
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()
        numped_filtro = request.args.get('numped')
        data_de = request.args.get('data_de')
        data_ate = request.args.get('data_ate')

        # Query com prefixo de schema DSL.
        sql_select = """
            SELECT
                a.NUMPED, c.CLIENTE, p.DATA, a.PREVENTREGA, a.HORAINI, a.HORAFIM
            FROM DSL.YAN_PEDAGEND a
            INNER JOIN DSL.PCPEDC p ON a.NUMPED = p.NUMPED
            INNER JOIN DSL.PCCLIENT c ON p.CODCLI = c.CODCLI
            WHERE a.PREVENTREGA IS NOT NULL
        """
        params = {}
        if numped_filtro:
            sql_select += " AND a.NUMPED = :numped"
            params['numped'] = int(numped_filtro)
        if data_de and data_ate:
            sql_select += " AND a.PREVENTREGA BETWEEN TO_DATE(:data_de, 'YYYY-MM-DD') AND TO_DATE(:data_ate, 'YYYY-MM-DD')"
            params.update({'data_de': data_de, 'data_ate': data_ate})
        elif data_de:
            sql_select += " AND a.PREVENTREGA >= TO_DATE(:data_de, 'YYYY-MM-DD')"
            params['data_de'] = data_de
        elif data_ate:
            sql_select += " AND a.PREVENTREGA <= TO_DATE(:data_ate, 'YYYY-MM-DD')"
            params['data_ate'] = data_ate
            
        sql_select += " ORDER BY a.PREVENTREGA DESC, a.NUMPED DESC"
        
        cursor.execute(sql_select, params)
        columns = [col[0] for col in cursor.description]
        agendamentos = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    except oracledb.DatabaseError as e:
        error, = e.args
        flash(f"Erro de banco de dados ao buscar relatório: {error.message}", 'error')
    finally:
        if connection:
            connection.close()
    return render_template('agendamentos.html', agendamentos=agendamentos)


# --- Rotas de Atualização ---
@app.route('/atualizar', methods=['POST'])
def atualizar_agendamento():
    numped = request.form.get('numped')
    preventrega_str = request.form.get('preventrega')
    horaini_str = request.form.get('horaini')
    horafim_str = request.form.get('horafim')
    
    connection = None
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()
        # Query com prefixo de schema DSL.
        cursor.execute("SELECT DATA FROM DSL.PCPEDC WHERE NUMPED = :1", [numped])
        result = cursor.fetchone()
        if not result:
            flash(f"Erro: Pedido {numped} não encontrado na PCPEDC.", 'error')
            return redirect(url_for('listar_pedidos'))
        
        data_pedido = result[0]
        preventrega_date = datetime.strptime(preventrega_str, '%Y-%m-%d').date()
        data_pedido_date = data_pedido.date()

        if preventrega_date < data_pedido_date + timedelta(days=1):
            flash(f"Erro no pedido {numped}: A previsão de entrega não pode ser menos de 24h após a data do pedido ({data_pedido_date.strftime('%d/%m/%Y')}).", 'error')
            return redirect(url_for('listar_pedidos'))
        if preventrega_date > data_pedido_date + timedelta(days=6):
            flash(f"Erro no pedido {numped}: A previsão de entrega não pode exceder 6 dias da data do pedido ({data_pedido_date.strftime('%d/%m/%Y')}).", 'error')
            return redirect(url_for('listar_pedidos'))

        # Query com prefixo de schema DSL.
        sql_update = "UPDATE DSL.YAN_PEDAGEND SET PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'), HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'), HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI') WHERE NUMPED = :numped"
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        
        cursor.execute(sql_update, {'prev': preventrega_str, 'h_ini': horaini_datetime, 'h_fim': horafim_datetime, 'numped': numped})
        connection.commit()
        flash(f"Pedido {numped} agendado com sucesso!", 'success')
    except oracledb.DatabaseError as e:
        error, = e.args
        flash(f"Erro de banco de dados ao atualizar: {error.message}", 'error')
    finally:
        if connection:
            connection.close()
    return redirect(url_for('listar_pedidos'))

@app.route('/atualizar-massa', methods=['POST'])
def atualizar_agendamento_massa():
    numpeds_selecionados = request.form.get('numpeds_selecionados')
    preventrega_str = request.form.get('preventrega')
    horaini_str = request.form.get('horaini')
    horafim_str = request.form.get('horafim')
    if not numpeds_selecionados:
        flash("Nenhum pedido foi selecionado.", 'error')
        return redirect(url_for('listar_pedidos'))
    numped_list = [int(n) for n in numpeds_selecionados.split(',')]
    
    connection = None
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
        cursor = connection.cursor()
        
        # Query com prefixo de schema DSL.
        placeholders_dates = ','.join([':{}'.format(i+1) for i in range(len(numped_list))])
        sql_fetch_dates = f"SELECT NUMPED, DATA FROM DSL.PCPEDC WHERE NUMPED IN ({placeholders_dates})"
        cursor.execute(sql_fetch_dates, numped_list)
        pedidos_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        preventrega_date = datetime.strptime(preventrega_str, '%Y-%m-%d').date()
        for numped in numped_list:
            data_pedido = pedidos_data.get(numped)
            if not data_pedido:
                flash(f"Erro: Pedido {numped} não encontrado na PCPEDC para validação.", 'error')
                return redirect(url_for('listar_pedidos'))
            data_pedido_date = data_pedido.date()
            if preventrega_date < data_pedido_date + timedelta(days=1):
                flash(f"Erro no pedido {numped}: A previsão de entrega não pode ser menos de 24h após a data do pedido ({data_pedido_date.strftime('%d/%m/%Y')}). O lote não foi agendado.", 'error')
                return redirect(url_for('listar_pedidos'))
            if preventrega_date > data_pedido_date + timedelta(days=6):
                flash(f"Erro no pedido {numped}: A previsão de entrega não pode exceder 6 dias da data do pedido ({data_pedido_date.strftime('%d/%m/%Y')}). O lote não foi agendado.", 'error')
                return redirect(url_for('listar_pedidos'))
        
        # Query com prefixo de schema DSL.
        placeholders_update = ','.join([':{}'.format(i+1) for i in range(len(numped_list))])
        sql_update = f"UPDATE DSL.YAN_PEDAGEND SET PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'), HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'), HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI') WHERE NUMPED IN ({placeholders_update})"
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        params = [preventrega_str, horaini_datetime, horafim_datetime] + numped_list
        cursor.execute(sql_update, params)
        
        connection.commit()
        flash(f"{cursor.rowcount} pedido(s) agendado(s) com sucesso!", 'success')
    except oracledb.DatabaseError as e:
        error, = e.args
        flash(f"Erro de banco de dados ao atualizar em massa: {error.message}", 'error')
    finally:
        if connection:
            connection.close()
    return redirect(url_for('listar_pedidos'))

# Inicia a aplicação web.
if __name__ == '__main__':
    app.run(debug=True)