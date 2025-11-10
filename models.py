from database import execute_query, execute_update, execute_many
import logging

logger = logging.getLogger(__name__)

class Pedido:
    @staticmethod
    def get_estatisticas():
        """Retorna estatísticas de pedidos pendentes e agendados."""
        today_str = "TRUNC(SYSDATE)"
        
        query = f"""
            SELECT 
                (SELECT COUNT(a.NUMPED) FROM DSL.YAN_PEDAGEND a
                INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED
                WHERE a.PREVENTREGA IS NULL) AS PENDENTES,
                
                (SELECT COUNT(*) FROM DSL.YAN_PEDAGEND 
                WHERE TRUNC(PREVENTREGA) = {today_str}) AS AGENDADOS_HOJE,
                
                (SELECT COUNT(*) FROM DSL.YAN_PEDAGEND 
                WHERE TRUNC(PREVENTREGA) BETWEEN {today_str} AND {today_str} + 6) AS AGENDADOS_7_DIAS
            FROM DUAL
        """
        try:
            result = execute_query(query, fetchall=False)
            return result
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {"pendentes": 0, "agendados_hoje": 0, "agendados_7_dias": 0}

    @staticmethod
    def get_pedidos_pendentes():
        """Retorna a lista de pedidos pendentes."""
        query = """
            SELECT a.NUMPED, c.CLIENTE, p.DATA, p.NUMNOTA, p.NUMCAR, a.PREVENTREGA, a.HORAINI, a.HORAFIM,
                   p.CODUSUR, u.NOME AS NOMERCA, p.VLTOTAL, p.OBS, p.OBS2
            FROM DSL.YAN_PEDAGEND a 
            INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED 
            INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI
            INNER JOIN PCUSUARI u ON p.CODUSUR = u.CODUSUR
            WHERE a.PREVENTREGA IS NULL
            ORDER BY p.DATA DESC
        """
        try:
            pedidos = execute_query(query)
            logger.info(f"Pedidos pendentes encontrados: {len(pedidos)}")
            
            # Garantir que os pedidos tenham o formato correto para o template
            from datetime import datetime
            logger.info(f"Exemplo de pedido processado: {pedidos[0] if pedidos else 'Nenhum pedido encontrado'}")
            
            # Padronizar as chaves para maiúsculas para corresponder ao template
            formatted_pedidos = []
            for pedido in pedidos:
                formatted_pedido = {}
                for key, value in pedido.items():
                    formatted_pedido[key.upper()] = value
                
                # Converter DATA para objeto datetime se não for None
                if formatted_pedido.get('DATA') is not None and not isinstance(formatted_pedido.get('DATA'), datetime):
                    try:
                        if isinstance(formatted_pedido.get('DATA'), str):
                            formatted_pedido['DATA'] = datetime.strptime(formatted_pedido['DATA'], '%Y-%m-%d %H:%M:%S')
                        # Adicionar tratamento para outros tipos de dados
                        elif hasattr(formatted_pedido.get('DATA'), 'strftime'):
                            # Se for um tipo de data Oracle, converter para datetime
                            formatted_pedido['DATA'] = datetime.strptime(formatted_pedido.get('DATA').strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.error(f"Erro ao converter data do pedido {formatted_pedido.get('NUMPED')}: {str(e)}")
                
                formatted_pedidos.append(formatted_pedido)
            
            pedidos = formatted_pedidos
            
            logger.info(f"Exemplo de pedido processado: {pedidos[0] if pedidos else 'Nenhum'}")
            return pedidos
        except Exception as e:
            logger.error(f"Erro ao obter pedidos pendentes: {str(e)}")
            return []

    @staticmethod
    def get_agendamentos_confirmados(data_de=None, data_ate=None, numped=None):
        """Retorna a lista de agendamentos confirmados."""
        query = """
            SELECT a.NUMPED, c.CLIENTE, p.DATA, p.NUMNOTA, p.NUMCAR, 
                   a.PREVENTREGA AS DTPREV, 
                   a.HORAINI, a.HORAFIM, p.CODUSUR, u.NOME AS NOMERCA,
                   p.VLTOTAL, p.OBS, p.OBS2
            FROM DSL.YAN_PEDAGEND a 
            INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED 
            INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI
            INNER JOIN PCUSUARI u ON p.CODUSUR = u.CODUSUR
            WHERE a.PREVENTREGA IS NOT NULL
            ORDER BY a.PREVENTREGA, a.HORAINI
        """
        try:
            agendamentos = execute_query(query)
            # Garantir que os agendamentos tenham o formato correto para o template
            for agendamento in agendamentos:
                # Converter DATA para objeto datetime se for string
                if isinstance(agendamento.get('DATA'), str):
                    from datetime import datetime
                    try:
                        agendamento['DATA'] = datetime.strptime(agendamento['DATA'], '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                # Garantir que PREVENTREGA seja um objeto datetime
                if isinstance(agendamento.get('DTPREV'), str):
                    try:
                        agendamento['PREVENTREGA'] = datetime.strptime(agendamento['DTPREV'], '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                else:
                    agendamento['PREVENTREGA'] = agendamento.get('DTPREV')
            return agendamentos
        except Exception as e:
            logger.error(f"Erro ao obter agendamentos confirmados: {str(e)}")
            return []

    @staticmethod
    def get_detalhes(numped):
        """Retorna os detalhes de um pedido específico."""
        if not numped or numped <= 0:
            return None
            
        # Consulta principal do pedido
        query_pedido = """
            SELECT a.NUMPED, c.CLIENTE, p.DATA, p.NUMNOTA, p.NUMCAR, 
                   TO_CHAR(a.PREVENTREGA, 'DD/MM/YYYY') AS DTPREV, 
                   a.HORAINI, a.HORAFIM, p.CODUSUR, u.NOME AS NOMERCA,
                   p.VLTOTAL, p.OBS, p.OBS2, p.OBS3, p.OBS4, p.OBS5
            FROM YAN_PEDAGEND a 
            INNER JOIN PCPEDC p ON a.NUMPED = p.NUMPED 
            INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI
            INNER JOIN PCUSUARI u ON p.CODUSUR = u.CODUSUR
            WHERE a.NUMPED = :numped
        """
        
        try:
            pedido = execute_query(query_pedido, {'numped': numped}, fetchall=False)
            
            if not pedido:
                return None
                
            # Consulta de itens do pedido
            query_itens = """
                SELECT 
                    I.CODPROD, P.DESCRICAO, I.QT, I.PVENDA, I.PTABELA, I.VLTOTITEM
                FROM PCPEDI I
                JOIN PCPRODUT P ON I.CODPROD = P.CODPROD
                WHERE I.NUMPED = :numped
                ORDER BY I.CODPROD
            """
            
            itens = execute_query(query_itens, {'numped': numped})
            pedido['itens'] = itens
            
            return pedido
        except Exception as e:
            logger.error(f"Erro ao obter detalhes do pedido {numped}: {str(e)}")
            return None

    @staticmethod
    def atualizar_agendamento(numped, data_prev, hora_aprox, obs5):
        """Atualiza o agendamento de um pedido."""
        if not numped or numped <= 0:
            return False, "Número de pedido inválido"
            
        # Verificar se o pedido existe
        query_check = "SELECT NUMPED FROM PCPEDC WHERE NUMPED = :numped"
        pedido = execute_query(query_check, {'numped': numped}, fetchall=False)
        
        if not pedido:
            return False, f"Pedido {numped} não encontrado"
            
        # Atualizar o agendamento
        query_update = """
            UPDATE PCPEDC 
            SET DTPREVENT = TO_DATE(:data_prev, 'DD/MM/YYYY'),
                HORAAPROX = :hora_aprox,
                OBS5 = :obs5
            WHERE NUMPED = :numped
        """
        
        try:
            rows = execute_update(query_update, {
                'data_prev': data_prev,
                'hora_aprox': hora_aprox,
                'obs5': obs5,
                'numped': numped
            })
            
            if rows == 0:
                return False, f"Não foi possível atualizar o pedido {numped}"
                
            logger.info(f"Pedido {numped} agendado para {data_prev} às {hora_aprox}")
            return True, f"Pedido {numped} agendado com sucesso!"
        except Exception as e:
            logger.error(f"Erro ao atualizar agendamento do pedido {numped}: {str(e)}")
            return False, f"Erro ao atualizar: {str(e)}"

    @staticmethod
    def atualizar_agendamentos_em_massa(pedidos, data_prev, hora_aprox, obs5):
        """Atualiza o agendamento de múltiplos pedidos."""
        if not pedidos or not isinstance(pedidos, list):
            return False, "Lista de pedidos inválida"
            
        resultados = []
        
        for numped in pedidos:
            try:
                numped = int(numped)
                sucesso, mensagem = Pedido.atualizar_agendamento(numped, data_prev, hora_aprox, obs5)
                resultados.append({
                    'numped': numped,
                    'sucesso': sucesso,
                    'mensagem': mensagem
                })
            except ValueError:
                resultados.append({
                    'numped': numped,
                    'sucesso': False,
                    'mensagem': "Número de pedido inválido"
                })
                
        return True, resultados


class RCA:
    @staticmethod
    def get_rcas_ativos():
        """Retorna a lista de RCAs ativos."""
        query = """
            SELECT CODUSUR, NOME, TELEFONE1
            FROM PCUSUARI
            WHERE ATIVO = 'S'
            ORDER BY NOME
        """
        try:
            return execute_query(query)
        except Exception as e:
            logger.error(f"Erro ao obter RCAs ativos: {str(e)}")
            return []

    @staticmethod
    def atualizar_telefone(codusur, telefone):
        """Atualiza o telefone de um RCA."""
        if not codusur or codusur <= 0:
            return False, "Código de RCA inválido"
            
        # Verificar se o RCA existe
        query_check = "SELECT CODUSUR FROM PCUSUARI WHERE CODUSUR = :codusur"
        rca = execute_query(query_check, {'codusur': codusur}, fetchall=False)
        
        if not rca:
            return False, f"RCA com código {codusur} não encontrado"
            
        # Atualizar o telefone
        query_update = """
            UPDATE PCUSUARI 
            SET TELEFONE1 = :telefone 
            WHERE CODUSUR = :codusur
        """
        
        try:
            rows = execute_update(query_update, {
                'telefone': telefone,
                'codusur': codusur
            })
            
            if rows == 0:
                return False, f"Não foi possível atualizar o telefone do RCA {codusur}"
                
            logger.info(f"Telefone do RCA {codusur} atualizado com sucesso para {telefone}")
            return True, f"Telefone do RCA {codusur} atualizado com sucesso!"
        except Exception as e:
            logger.error(f"Erro ao atualizar telefone do RCA {codusur}: {str(e)}")
            return False, f"Erro ao atualizar: {str(e)}"