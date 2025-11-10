import requests
import os
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Pegar variáveis do ambiente
url = os.getenv("API_URL")
token = os.getenv("API_TOKEN")
NUMERO_ADMIN = os.getenv("NUMBER").split()


# Cabeçalhos
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def send_message(body, numbers=None, numero_destino=None, user_id=19, queue_id="", send_signature=True, close_ticket=True):
    """
    Envia uma mensagem de texto para vários números usando a API do WhatsApp.

    Parâmetros:
        body (str): mensagem a ser enviada
        numbers (list ou str): lista de números ou string única
        numero_destino (str): número único de destino (prioritário se fornecido)
        user_id (int): ID do usuário (default=19)
        queue_id (str): fila do ticket
        send_signature (bool): envia assinatura
        close_ticket (bool): fecha ticket
    """
    results = []

    # Se numero_destino foi passado, usa ele
    if numero_destino:
        numbers = [numero_destino]
    elif numbers is None:
        raise ValueError("É necessário informar pelo menos um número.")

    # Se numbers for string única, transforma em lista
    if isinstance(numbers, str):
        numbers = [numbers]

    for number in numbers:
        payload = {
            "number": number,
            "body": body,
            "userId": user_id,
            "queueId": queue_id,
            "sendSignature": send_signature,
            "closeTicket": close_ticket
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            results.append((number, True, response.json()))
        except requests.exceptions.RequestException as e:
            results.append((number, False, str(e)))

    return results