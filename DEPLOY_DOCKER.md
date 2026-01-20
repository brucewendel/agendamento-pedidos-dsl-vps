# 🐳 GUIA DE DEPLOY - DSL AGENDAMENTO COM DOCKER

## 📋 Pré-requisitos

- Docker instalado no VPS
- Docker Compose instalado
- Acesso SSH ao VPS
- Portas liberadas: 6000 (aplicação), 6379 (Redis)

---

## 🚀 DEPLOY NO VPS

### 1. **Preparar o Ambiente**

```bash
# Conectar ao VPS via SSH
ssh usuario@seu-vps-ip

# Criar diretório para o projeto
mkdir -p /opt/agendamento
cd /opt/agendamento
```

### 2. **Transferir Arquivos**

```bash
# No seu computador local, comprimir o projeto
cd h:\agendamento
tar -czf agendamento.tar.gz --exclude=bkp --exclude=__pycache__ --exclude=*.pyc .

# Transferir para o VPS
scp agendamento.tar.gz usuario@seu-vps-ip:/opt/agendamento/

# No VPS, extrair os arquivos
cd /opt/agendamento
tar -xzf agendamento.tar.gz
rm agendamento.tar.gz
```

### 3. **Configurar Variáveis de Ambiente**

```bash
# Editar o arquivo .env no VPS
nano .env
```

**Configurações importantes para produção:**

```env
# Banco de Dados Oracle
DB_USER=DSL
DB_PASSWORD=dsl2155wt100
DB_DSN=192.168.0.11:1521/DSL

# Flask
FLASK_SECRET_KEY=f8f5cd46482d4c668081bf2d4526f2495b7c9a16d97c60cd
FLASK_HOST=0.0.0.0
FLASK_PORT=6000
FLASK_DEBUG=False

# Redis (usar nome do container)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# WhatsApp API
API_URL=https://api.mxzap.net/api/messages/send
API_TOKEN=hdRx8ctP574QM37s4kJC85ShQwD54y
NUMBER=558586903517
```

### 4. **Build e Iniciar Containers**

```bash
# Build da imagem
docker-compose build

# Iniciar os containers
docker-compose up -d

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f agendamento-app
```

---

## 🔧 COMANDOS ÚTEIS

### **Gerenciamento de Containers**

```bash
# Parar containers
docker-compose down

# Reiniciar containers
docker-compose restart

# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f agendamento-app
docker-compose logs -f redis

# Acessar shell do container
docker exec -it agendamento-sistema bash

# Verificar uso de recursos
docker stats
```

### **Atualização da Aplicação**

```bash
# 1. Parar containers
docker-compose down

# 2. Fazer backup do .env
cp .env .env.backup

# 3. Atualizar código (via git ou scp)
git pull origin main
# ou
scp agendamento.tar.gz usuario@vps:/opt/agendamento/

# 4. Rebuild da imagem
docker-compose build --no-cache

# 5. Iniciar novamente
docker-compose up -d

# 6. Verificar logs
docker-compose logs -f agendamento-app
```

### **Backup e Restore**

```bash
# Backup do Redis (se necessário)
docker exec agendamento-redis redis-cli SAVE
docker cp agendamento-redis:/data/dump.rdb ./backup-redis-$(date +%Y%m%d).rdb

# Backup dos arquivos
tar -czf backup-agendamento-$(date +%Y%m%d).tar.gz .
```

---

## 🌐 NGINX REVERSE PROXY (Opcional)

Se estiver usando Nginx Proxy Manager ou Nginx:

### **Configuração Nginx**

```nginx
server {
    listen 80;
    server_name agendamento.seudominio.com;

    location / {
        proxy_pass http://localhost:6000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### **Com SSL (Let's Encrypt)**

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d agendamento.seudominio.com

# Renovação automática já está configurada
```

---

## 📊 MONITORAMENTO

### **Verificar Saúde da Aplicação**

```bash
# Testar endpoint
curl http://localhost:6000/login-modern

# Verificar Redis
docker exec agendamento-redis redis-cli ping

# Verificar conexão com banco Oracle
docker exec -it agendamento-sistema python -c "from database import test_connection; test_connection()"
```

### **Logs e Debug**

```bash
# Logs do Gunicorn
docker-compose logs -f agendamento-app | grep gunicorn

# Logs de erro
docker-compose logs -f agendamento-app | grep ERROR

# Últimas 100 linhas
docker-compose logs --tail=100 agendamento-app
```

---

## 🔒 SEGURANÇA

### **Firewall**

```bash
# Permitir apenas portas necessárias
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Porta 6000 não precisa estar aberta se usar Nginx
```

### **Atualizar Senha do Redis (Recomendado)**

```yaml
# Em docker-compose.yml
redis:
  image: redis:latest
  command: redis-server --requirepass SUA_SENHA_FORTE
```

```env
# Em .env
REDIS_PASSWORD=SUA_SENHA_FORTE
```

---

## 🐛 TROUBLESHOOTING

### **Container não inicia**

```bash
# Ver logs detalhados
docker-compose logs agendamento-app

# Verificar configuração
docker-compose config

# Rebuild sem cache
docker-compose build --no-cache
```

### **Erro de conexão com Oracle**

```bash
# Verificar se o VPS consegue acessar o banco
telnet 192.168.0.11 1521

# Verificar variáveis de ambiente
docker exec agendamento-sistema env | grep DB_
```

### **Redis não conecta**

```bash
# Verificar se Redis está rodando
docker-compose ps redis

# Testar conexão
docker exec agendamento-redis redis-cli ping

# Ver logs do Redis
docker-compose logs redis
```

### **Aplicação lenta**

```bash
# Aumentar workers do Gunicorn
# Editar Dockerfile, linha CMD:
CMD ["gunicorn", "--bind", "0.0.0.0:6000", "--workers", "8", "app:app"]

# Rebuild
docker-compose build
docker-compose up -d
```

---

## 📈 PERFORMANCE

### **Otimizações Recomendadas**

1. **Gunicorn Workers**: `(2 x CPU cores) + 1`
2. **Redis MaxMemory**: Configurar limite de memória
3. **Nginx Caching**: Habilitar cache para assets estáticos
4. **Gzip**: Habilitar compressão no Nginx

### **Configuração Gunicorn Otimizada**

```dockerfile
# No Dockerfile
CMD ["gunicorn", \
     "--bind", "0.0.0.0:6000", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
```

---

## 📞 SUPORTE

**Portas Utilizadas:**
- 6000: Aplicação Flask
- 6379: Redis

**Containers:**
- `agendamento-sistema`: Aplicação principal
- `agendamento-redis`: Cache Redis

**Rede:**
- `agendamento-network`: Rede interna
- `npm-nginx_default`: Rede do Nginx Proxy Manager (se usar)

---

**Desenvolvido para DSL - 2026**
