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

# URL do novo endpoint CTA
URL_CTA = "https://mx2tech.myzappi.com.br/api/messages/send-cta"

# Cabeçalhos
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Cabeçalhos para CTA
headers_cta = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def send_message(message, numbers=None, numero_destino=None,):
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
            "message": message,
            "createTicket": False
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


def send_cta_message(number, header, text, footer, button_value, button_label="copiar texto", button_type="copy", create_ticket=False):
    """
    Envia uma mensagem CTA (Call To Action) com botão interativo via WhatsApp.
    
    Parâmetros:
        number (str): número do WhatsApp (com código do país)
        header (str): cabeçalho da mensagem
        text (str): texto principal da mensagem
        footer (str): rodapé da mensagem
        button_value (str): valor do botão (ex: código de acesso)
        button_label (str): rótulo do botão (padrão: "copiar texto")
        button_type (str): tipo de botão (padrão: "copy")
        create_ticket (bool): criar ticket na API (padrão: False)
    
    Retorno:
        tuple: (number, success, response_data)
    """
    
    # Construir payload conforme especificação do endpoint CTA
    payload = {
        "number": number,
        "header": header,
        "text": text,
        "footer": footer,
        "createTicket": str(create_ticket).lower(),
        "buttons": {
            "type": button_type,
            "label": button_label,
            "value": button_value
        }
    }
    
    # Log do payload sendo enviado
    print(f"\n[ENVIARWPP] 📤 Enviando mensagem CTA WhatsApp")
    print(f"[ENVIARWPP] URL: {URL_CTA}")
    print(f"[ENVIARWPP] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(URL_CTA, headers=headers_cta, json=payload, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        # Log de sucesso
        print(f"[ENVIARWPP] ✅ Sucesso (Status: {response.status_code})")
        print(f"[ENVIARWPP] Resposta: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
        return (number, True, response_data)
        
    except requests.exceptions.Timeout as e:
        error_msg = f"Timeout na requisição CTA para {number}: {str(e)}"
        print(f"[ENVIARWPP] ⏱️ {error_msg}")
        return (number, False, error_msg)
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Erro de conexão CTA para {number}: {str(e)}"
        print(f"[ENVIARWPP] 🔌 {error_msg}")
        return (number, False, error_msg)
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"Erro HTTP {response.status_code} na requisição CTA para {number}"
        response_text = response.text if hasattr(response, 'text') else str(e)
        print(f"[ENVIARWPP] ❌ {error_msg}")
        print(f"[ENVIARWPP] Resposta da API: {response_text}")
        return (number, False, error_msg)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro na requisição CTA para {number}: {str(e)}"
        print(f"[ENVIARWPP] ⚠️ {error_msg}")
        return (number, False, error_msg)
        
    except Exception as e:
        error_msg = f"Erro inesperado na requisição CTA para {number}: {str(e)}"
        print(f"[ENVIARWPP] 💥 {error_msg}")
        return (number, False, error_msg)