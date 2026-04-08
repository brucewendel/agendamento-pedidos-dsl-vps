"""
Funções para editar agendamentos existentes
"""
from datetime import datetime, timedelta
from flask import session

def editar_agendamento(numped, preventrega_str, horaini_str, horafim_str, observacao, connection_func, release_func, get_user_func, is_admin=False):
    """Edita um agendamento existente na tabela DSLTI_PEDAGEND com validações de data"""
    
    # Obter nome do usuário da aplicação para auditoria
    app_user = get_user_func()
    
    connection = connection_func(app_user=app_user)
    if not connection:
        return {'status': 'error', 'message': 'Erro de conexão com o banco de dados'}
    
    try:
        cursor = connection.cursor()
        
        # Verificar se o agendamento existe
        cursor.execute("SELECT NUMPED FROM DSLTI_PEDAGEND WHERE NUMPED = :1", [numped])
        if not cursor.fetchone():
            return {'status': 'error', 'message': f'Agendamento do pedido {numped} não encontrado'}
        
        # Verificar se o pedido existe na PCPEDC
        cursor.execute("SELECT DATA FROM PCPEDC WHERE NUMPED = :1", [numped])
        result = cursor.fetchone()
        if not result:
            return {'status': 'error', 'message': 'Pedido não encontrado'}
        
        data_pedido = result[0]
        preventrega_date = datetime.strptime(preventrega_str, '%Y-%m-%d').date()
        data_pedido_date = data_pedido.date()
        
        if not is_admin:
            # Validação: entrega deve ser pelo menos 24h após a data do pedido
            if preventrega_date < data_pedido_date + timedelta(days=1):
                return {'status': 'error', 'message': 'Pedidos não podem ser agendados com menos de 24 horas da data do pedido'}
            
            # Validação: entrega não pode exceder 6 dias da data do pedido
            if preventrega_date > data_pedido_date + timedelta(days=6):
                return {'status': 'error', 'message': 'Pedidos não podem ser agendados superior a 6 dias da data do pedido'}
        
        # Atualizar agendamento
        sql_update = """
            UPDATE DSLTI_PEDAGEND SET
                PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'),
                HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'),
                HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI'),
                OBSERVACAO = :obs
            WHERE NUMPED = :numped
        """
        
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        
        cursor.execute(sql_update, {
            'numped': numped,
            'prev': preventrega_str,
            'h_ini': horaini_datetime,
            'h_fim': horafim_datetime,
            'obs': observacao
        })
        
        connection.commit()
        return {'status': 'success', 'message': f'Agendamento do pedido {numped} atualizado com sucesso!'}
        
    except Exception as e:
        return {'status': 'error', 'message': f'Erro interno: {str(e)}'}
    finally:
        if connection:
            release_func(connection)


def editar_agendamento_massa(numpeds_list, preventrega_str, horaini_str, horafim_str, observacao, connection_func, release_func, get_user_func, is_admin=False):
    """Edita múltiplos agendamentos na tabela DSLTI_PEDAGEND com validações de data"""
    
    if not numpeds_list:
        return {'status': 'error', 'message': 'Nenhum agendamento foi selecionado.'}
    
    # Obter nome do usuário da aplicação para auditoria
    app_user = get_user_func()
    
    connection = connection_func(app_user=app_user)
    if not connection:
        return {'status': 'error', 'message': 'Erro de conexão com o banco de dados'}
    
    try:
        cursor = connection.cursor()
        
        # Verificar se os agendamentos existem
        placeholders_check = ','.join([f':{i+1}' for i in range(len(numpeds_list))])
        sql_check = f"SELECT NUMPED FROM DSLTI_PEDAGEND WHERE NUMPED IN ({placeholders_check})"
        cursor.execute(sql_check, numpeds_list)
        agendamentos_existentes = {row[0] for row in cursor.fetchall()}
        
        # Verificar se todos os pedidos selecionados têm agendamento
        numpeds_set = set(numpeds_list)
        numpeds_sem_agendamento = numpeds_set - agendamentos_existentes
        
        if numpeds_sem_agendamento:
            return {
                'status': 'error', 
                'message': f'Os seguintes pedidos não possuem agendamento: {", ".join(map(str, numpeds_sem_agendamento))}'
            }
        
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
            
            if not is_admin:
                data_pedido_date = data_pedido.date()
                
                # Validação: entrega deve ser pelo menos 24h após a data do pedido
                if preventrega_date < data_pedido_date + timedelta(days=1):
                    msg = f'Pedidos não podem ser agendados com menos de 24 horas da data do pedido ({data_pedido_date.strftime("%d/%m/%Y")}).'
                    return {'status': 'error', 'message': msg}
                
                # Validação: entrega não pode exceder 6 dias da data do pedido
                if preventrega_date > data_pedido_date + timedelta(days=6):
                    msg = f'Erro no pedido {numped}: Pedidos não podem ser agendados superior a 6 dias da data do pedido ({data_pedido_date.strftime("%d/%m/%Y")}).'
                    return {'status': 'error', 'message': msg}
        
        # Atualizar agendamentos em massa
        sql_update = """
            UPDATE DSLTI_PEDAGEND SET
                PREVENTREGA = TO_DATE(:prev, 'YYYY-MM-DD'),
                HORAINI = TO_DATE(:h_ini, 'YYYY-MM-DD HH24:MI'),
                HORAFIM = TO_DATE(:h_fim, 'YYYY-MM-DD HH24:MI'),
                OBSERVACAO = :obs
            WHERE NUMPED = :numped
        """
        
        horaini_datetime = f"{preventrega_str} {horaini_str}"
        horafim_datetime = f"{preventrega_str} {horafim_str}"
        
        # Preparar dados para atualização em lote
        dados_update = []
        for numped in numpeds_list:
            dados_update.append({
                'numped': numped,
                'prev': preventrega_str,
                'h_ini': horaini_datetime,
                'h_fim': horafim_datetime,
                'obs': observacao
            })
        
        # Executar atualizações
        cursor.executemany(sql_update, dados_update)
        connection.commit()
        
        return {'status': 'success', 'message': f'{len(numpeds_list)} agendamento(s) atualizado(s) com sucesso!'}
        
    except Exception as e:
        return {'status': 'error', 'message': f'Erro: {str(e)}'}
    finally:
        if connection:
            release_func(connection)
