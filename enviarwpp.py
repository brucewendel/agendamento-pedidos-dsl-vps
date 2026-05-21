import requests
import os
import json
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

def send_message(message, numbers=None, numero_destino=None):
    """
    Envia uma mensagem de texto para vários números usando a API do WhatsApp.

    Parâmetros:
        message (str): mensagem a ser enviada
        numbers (list ou str): lista de números ou string única
        numero_destino (str): número único de destino (prioritário se fornecido)
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
            "message": message
        }
        
        # Log do payload sendo enviado
        print(f"\n[ENVIARWPP] 📤 Enviando mensagem WhatsApp")
        print(f"[ENVIARWPP] URL: {url}")
        print(f"[ENVIARWPP] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            response_data = response.json()
            
            # Log de sucesso
            print(f"[ENVIARWPP] ✅ Sucesso (Status: {response.status_code})")
            print(f"[ENVIARWPP] Resposta: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            results.append((number, True, response_data))
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout na requisição para {number}: {str(e)}"
            print(f"[ENVIARWPP] ⏱️ {error_msg}")
            results.append((number, False, error_msg))
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Erro de conexão para {number}: {str(e)}"
            print(f"[ENVIARWPP] 🔌 {error_msg}")
            results.append((number, False, error_msg))
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Erro HTTP {response.status_code} para {number}"
            response_text = response.text if hasattr(response, 'text') else str(e)
            print(f"[ENVIARWPP] ❌ {error_msg}")
            print(f"[ENVIARWPP] Resposta da API: {response_text}")
            results.append((number, False, error_msg))
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição para {number}: {str(e)}"
            print(f"[ENVIARWPP] ⚠️ {error_msg}")
            results.append((number, False, error_msg))
            
        except Exception as e:
            error_msg = f"Erro inesperado para {number}: {str(e)}"
            print(f"[ENVIARWPP] 💥 {error_msg}")
            results.append((number, False, error_msg))

    return results