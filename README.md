# Sistema de Agendamento de Entregas

Sistema web desenvolvido em Flask para gerenciamento e agendamento de entregas, com autenticação de usuários administrativos e RCAs (Representantes Comerciais Autônomos).

## 📋 Funcionalidades

### Para Administradores
- **Dashboard**: Visualização de KPIs e gráficos de desempenho
- **Painel de Ações**: Gerenciamento de pedidos pendentes e confirmados
- **Relatórios**: Análise de dados e métricas
- **Usuários**: Cadastro e gerenciamento de RCAs
- **Agendamento**: Funcionalidades completas de agendamento

### Para RCAs
- **Painel de Ações**: Visualização e agendamento de seus próprios pedidos
- **Relatórios**: Acesso aos relatórios de suas entregas
- **Agendamento**: Capacidade de agendar entregas

## 🏗️ Estrutura do Projeto

```
agendamento/
├── app.py                 # Aplicação principal Flask
├── enviarwpp.py          # Módulo para envio de mensagens WhatsApp
├── .env                  # Variáveis de ambiente (não versionado)
├── Iniciar.bat          # Script para iniciar a aplicação
├── backup.bat           # Script para backup automático
├── bkp/                 # Pasta de backups
├── templates/           # Templates HTML
│   ├── login.html       # Página de login administrativo
│   ├── login_rca.html   # Página de login para RCAs
│   ├── painel.html      # Painel principal com KPIs
│   # usuarios.html removido - funcionalidade integrada no painel.html
└── __pycache__/         # Cache Python
```

## 🚀 Como Executar

### Pré-requisitos
- Python 3.8+
- Oracle Client (para conexão com banco Oracle)
- Dependências Python (instalar via pip)

### Instalação
1. Clone o repositório
2. Configure as variáveis de ambiente no arquivo `.env`:
   ```
   FLASK_SECRET_KEY=sua_chave_secreta
   DB_USER=usuario_banco
   DB_PASSWORD=senha_banco
   DB_DSN=dsn_oracle
   API_URL=url_api_whatsapp
   API_TOKEN=token_api_whatsapp
   NUMERO_ADMIN=numero_admin_whatsapp
   ```

### Execução
- **Windows**: Execute `Iniciar.bat`
- **Manual**: `python app.py`

A aplicação estará disponível em `http://localhost:6000`

## 🔐 Autenticação

### Usuários Administrativos
- Login via formulário web com usuário e senha
- Permissões configuráveis por usuário

### RCAs
- Autenticação via token WhatsApp
- Acesso restrito aos próprios pedidos

## 🛠️ Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Banco de Dados**: Oracle Database
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Gráficos**: Plotly.js
- **Notificações**: SweetAlert2
- **Comunicação**: WhatsApp API

## 📊 Funcionalidades Técnicas

- Sistema de permissões granular
- Autenticação multi-fator para RCAs
- Geração de gráficos e KPIs em tempo real
- Interface responsiva
- Tema claro/escuro
- Backup automático
- Logs de autenticação

## 🔧 Manutenção

- Backups são gerados automaticamente via `backup.bat`
- Logs de autenticação são mantidos em memória
- Sistema de fallback com dados de exemplo quando banco não disponível

## 📝 Notas de Desenvolvimento

- O sistema utiliza dados de exemplo quando não há conexão com banco
- Tokens de autenticação têm validade limitada
- Interface otimizada para uso em dispositivos móveis
- Suporte a temas claro e escuro com persistência local