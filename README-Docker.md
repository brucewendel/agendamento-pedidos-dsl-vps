# 🐳 Sistema de Agendamento - Docker

Este documento explica como executar o Sistema de Agendamento usando Docker.

## 📋 Pré-requisitos

- Docker instalado
- Docker Compose instalado
- Arquivo `.env` configurado com as variáveis de ambiente

## 🚀 Como executar

### 1. Configurar variáveis de ambiente

Certifique-se de que o arquivo `.env` está configurado com:

```env
# Banco de dados Oracle
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_DSN=seu_dsn

# Flask
FLASK_SECRET_KEY=sua_chave_secreta_aqui

# WhatsApp API (opcional)
API_URL=sua_api_url
API_TOKEN=seu_token
NUMERO_ADMIN=seu_numero
```

### 2. Executar com Docker Compose

```bash
# Construir e iniciar o container
docker-compose up --build

# Executar em background
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Parar o container
docker-compose down
```

### 3. Executar apenas com Docker

```bash
# Construir a imagem
docker build -t agendamento-sistema .

# Executar o container
docker run -p 6000:6000 --env-file .env agendamento-sistema
```

## 🔧 Comandos úteis

### Gerenciamento de containers

```bash
# Listar containers em execução
docker ps

# Parar container específico
docker stop agendamento-sistema

# Remover container
docker rm agendamento-sistema

# Ver logs do container
docker logs agendamento-sistema
```

### Gerenciamento de imagens

```bash
# Listar imagens
docker images

# Remover imagem
docker rmi agendamento-sistema

# Limpar imagens não utilizadas
docker image prune
```

## 📁 Estrutura de volumes

O container monta o diretório `./backups` para persistir backups:

```
./backups -> /app/backups (dentro do container)
```

## 🌐 Acesso à aplicação

Após iniciar o container, acesse:

- **URL:** http://localhost:6000
- **Login:** admin
- **Senha:** admin

## 🔒 Segurança

O container executa com usuário não-root (`appuser`) para maior segurança.

## 🐛 Troubleshooting

### Problema: Container não inicia

1. Verifique se o arquivo `.env` existe e está configurado
2. Verifique se as portas não estão em uso:
   ```bash
   netstat -an | grep 6000
   ```

### Problema: Erro de conexão com banco

1. Verifique as credenciais no arquivo `.env`
2. Certifique-se de que o banco Oracle está acessível
3. Verifique os logs do container:
   ```bash
   docker logs agendamento-sistema
   ```

### Problema: Permissões de arquivo

Se houver problemas de permissão com backups:

```bash
# Ajustar permissões do diretório de backups
chmod 755 ./backups
```

## 📊 Monitoramento

Para monitorar o container:

```bash
# Estatísticas de uso
docker stats agendamento-sistema

# Informações detalhadas
docker inspect agendamento-sistema
```

## 🔄 Atualizações

Para atualizar a aplicação:

```bash
# Parar container atual
docker-compose down

# Reconstruir com mudanças
docker-compose up --build -d
```