# 🚀 Plano de Melhoria de Performance - DSL Agendamento

**Data:** 23/01/2026  
**Análise por:** Especialista DBA Oracle e Back-end  
**Aplicação:** Sistema de Agendamento de Pedidos  
**Status:** ✅ IMPLEMENTADO

---

## 📋 Resumo Executivo

A aplicação **DSL Agendamento** é um sistema Flask/Python que se conecta a um banco Oracle para gerenciar pedidos e agendamentos. A aplicação roda bem localmente mas apresenta lentidão na VPS (internet). Após análise completa do código, foram identificados **problemas críticos de performance** que explicam a diferença de comportamento.

---

## 🔍 Arquitetura Atual

| Componente | Tecnologia |
|------------|------------|
| Back-end | Python/Flask 2.3.3 |
| Banco de Dados | Oracle (cx_Oracle 8.3.0) |
| Cache | Redis 5.0.1 |
| Rate Limiting | Flask-Limiter 4.1.1 |
| Servidor WSGI | Gunicorn 21.2.0 |

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. **SEM CONNECTION POOL ORACLE** ⚠️ CRÍTICO

**Arquivo:** `database.py` (linhas 58-86)

**Problema:**
```python
def get_connection(app_user=None):
    connection = cx_Oracle.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN
    )
```

**Impacto:** Cada requisição abre uma NOVA conexão com o banco Oracle. Isso é extremamente lento em ambientes remotos (VPS) devido à latência de rede. O handshake TCP/Oracle pode levar 100-500ms por conexão.

**Na VPS:** Se a latência para o Oracle é 50ms, cada conexão pode levar 150-300ms só para abrir. Com múltiplas queries por página (vide problema #2), isso se multiplica.

---

### 2. **MÚLTIPLAS CONEXÕES POR REQUISIÇÃO** ⚠️ CRÍTICO

**Arquivo:** `database.py`

**Problema:** Cada função abre e fecha sua própria conexão:

| Função | Conexões |
|--------|----------|
| `get_pedidos_pendentes()` | 1 |
| `get_agendamentos_confirmados()` | 1 |
| `get_kpis_data()` | 4 (uma por KPI!) |
| `get_graficos_data()` | 6 (uma por gráfico!) |
| `calcular_kpis_avancados()` | 3 |
| `get_stats_data()` | 2 |

**Exemplo em `get_kpis_data()`** (linhas 608-632):
```python
for key, query in queries.items():
    result = execute_query(query, fetch_one=True)  # ABRE/FECHA CONEXÃO A CADA LOOP!
```

**Impacto:** Uma única página de dashboard pode abrir **12-15 conexões** com o banco!

---

### 3. **QUERIES SEM ÍNDICES OTIMIZADOS** ⚠️ ALTO

**Arquivo:** `database.py`

**Queries problemáticas identificadas:**

#### Query 1 - Pedidos Pendentes (linhas 171-196):
```sql
SELECT COUNT(*) FROM PCPEDC p
INNER JOIN PCCLIENT c ON p.CODCLI = c.CODCLI 
WHERE NOT EXISTS (
    SELECT 1 FROM DSLTI_PEDAGEND a WHERE a.NUMPED = p.NUMPED
)
AND p.CODSUPERVISOR NOT IN (9130)
AND p.DATA >= TO_DATE('01/01/2026', 'DD/MM/YYYY')
```

**Problemas:**
- `NOT EXISTS` com subquery correlacionada pode ser lento
- Filtro por data com `TO_DATE()` constante impede uso de índice
- Ausência provável de índice em `DSLTI_PEDAGEND.NUMPED`

#### Query 2 - Agendamentos Confirmados (linhas 331-356):
```sql
WITH UltimoEvento AS (
    SELECT e.carga_formada_erp, e.seq_pedido_erp, e.DESCRICAO,
    ROW_NUMBER() OVER (PARTITION BY...) as rn
    FROM FUSIONT.FUSIONTRAK_INT_EVENTOS e
)
SELECT ...
LEFT JOIN UltimoEvento ue ON ue.seq_pedido_erp = TO_CHAR(p.NUMPED)...
```

**Problemas:**
- CTE com `ROW_NUMBER()` sobre tabela possivelmente grande
- JOIN com `TO_CHAR()` impede uso de índices (conversão implícita)
- Tabela externa `FUSIONT.FUSIONTRAK_INT_EVENTOS` pode ter latência adicional

#### Query 3 - Gráficos (linhas 762-868):
- **6 queries separadas** executadas sequencialmente
- Cada uma abre/fecha conexão
- Algumas fazem `GROUP BY` sem índices apropriados

---

### 4. **CACHE REDIS PARCIALMENTE IMPLEMENTADO** ⚠️ MÉDIO

**Arquivo:** `database.py`

**Problema:** O decorator `@cache_data` existe mas:

1. **Está duplicado** (linhas 31-56 e 1054-1065) - segunda versão usa `g.cache` que não existe
2. **Só é usado em `get_kpis_data()`** - outras funções pesadas não têm cache
3. **TTL de 5 minutos** pode ser muito curto para dados agregados

**Funções SEM cache que deveriam ter:**
- `get_graficos_data()` - dados de gráficos (pesado)
- `get_stats_data()` - estatísticas
- `calcular_kpis_avancados()` - KPIs avançados
- `get_usuarios()` - lista de usuários

---

### 5. **SERIALIZAÇÃO JSON REDUNDANTE** ⚠️ BAIXO

**Arquivo:** `charts.py`

**Problema:** A função `generate_all_charts()` gera dados Plotly.js completos no servidor, incluindo configurações de layout que poderiam ser definidas no cliente.

---

### 6. **QUERIES N+1 POTENCIAIS** ⚠️ MÉDIO

**Arquivo:** `routes.py` (linhas 767-792)

**Problema em `atualizar_massa()`:**
```python
for numped in numped_list:
    result = atualizar_agendamento(numped, ...)  # CADA PEDIDO = NOVA CONEXÃO
```

Cada atualização individual abre sua própria conexão, quando deveria ser uma única transação batch.

---

### 7. **AUSÊNCIA DE PREPARED STATEMENTS REUTILIZÁVEIS** ⚠️ MÉDIO

**Problema:** Cada execução de query cria um novo cursor e statement. O Oracle precisa fazer parse de cada SQL toda vez.

---

## 📊 IMPACTO ESTIMADO POR PROBLEMA

| Problema | Impacto Local | Impacto VPS | Prioridade |
|----------|--------------|-------------|------------|
| Sem Connection Pool | +50ms | +500-2000ms | 🔴 P0 |
| Múltiplas Conexões | +100ms | +1000-5000ms | 🔴 P0 |
| Queries sem índice | +200ms | +500-1500ms | 🟠 P1 |
| Cache incompleto | +100ms | +300-800ms | 🟠 P1 |
| N+1 em massa | +50ms | +200-500ms | 🟡 P2 |
| JSON redundante | +10ms | +30ms | 🟢 P3 |

---

## ✅ PLANO DE AÇÃO - MELHORIAS

### FASE 1 - CRÍTICO (Implementar Imediatamente)

#### 1.1 Implementar Connection Pool Oracle

**Arquivo:** `database.py`

```python
# SUBSTITUIR get_connection() por:
import cx_Oracle

# Configuração do Pool (no início do arquivo)
pool = None

def init_pool():
    global pool
    if pool is None:
        pool = cx_Oracle.SessionPool(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            min=2,           # Mínimo de conexões
            max=10,          # Máximo de conexões
            increment=1,     # Incremento
            threaded=True,   # Suporte a threads
            getmode=cx_Oracle.SPOOL_ATTRVAL_WAIT,
            encoding="UTF-8"
        )
    return pool

def get_connection(app_user=None):
    """Obtém conexão do pool"""
    global pool
    if pool is None:
        init_pool()
    
    connection = pool.acquire()
    
    if app_user and connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                "BEGIN DBMS_SESSION.SET_IDENTIFIER(:app_user); END;",
                {'app_user': app_user}
            )
            cursor.close()
        except Exception as e:
            print(f"Aviso: Não foi possível definir CLIENT_IDENTIFIER: {e}")
    
    return connection

def release_connection(connection):
    """Devolve conexão ao pool"""
    global pool
    if pool and connection:
        pool.release(connection)
```

**Benefício esperado:** Redução de 70-80% no tempo de conexão em ambiente remoto.

---

#### 1.2 Reutilizar Conexão em Funções Múltiplas

**Arquivo:** `database.py`

Criar context manager para conexões:

```python
from contextlib import contextmanager

@contextmanager
def get_db_connection(app_user=None):
    """Context manager para conexão com auto-release"""
    connection = get_connection(app_user)
    try:
        yield connection
    finally:
        release_connection(connection)

# USO:
def get_kpis_data(codigo_rca=None):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        # Executar TODAS as queries com o mesmo cursor/conexão
        for key, query in queries.items():
            cursor.execute(query)
            result = cursor.fetchone()
            kpis[key] = result[0] if result else 0
        cursor.close()
    return kpis
```

---

### FASE 2 - ALTO (Próxima Sprint)

#### 2.1 Criar Índices no Oracle

**Executar no banco Oracle:**

```sql
-- Índice para DSLTI_PEDAGEND
CREATE INDEX IDX_PEDAGEND_NUMPED ON DSLTI_PEDAGEND(NUMPED);
CREATE INDEX IDX_PEDAGEND_PREVENTREGA ON DSLTI_PEDAGEND(PREVENTREGA);
CREATE INDEX IDX_PEDAGEND_STATUS ON DSLTI_PEDAGEND(STATUS);

-- Índice para PCPEDC (se não existir)
CREATE INDEX IDX_PCPEDC_DATA ON PCPEDC(DATA);
CREATE INDEX IDX_PCPEDC_CODUSUR ON PCPEDC(CODUSUR);
CREATE INDEX IDX_PCPEDC_CODSUPERVISOR ON PCPEDC(CODSUPERVISOR);

-- Índice composto para consultas frequentes
CREATE INDEX IDX_PCPEDC_DATA_SUPERVISOR ON PCPEDC(DATA, CODSUPERVISOR);

-- Índice para eventos (se tiver acesso)
CREATE INDEX IDX_EVENTOS_PEDIDO_CARGA ON FUSIONT.FUSIONTRAK_INT_EVENTOS(seq_pedido_erp, carga_formada_erp);
```

---

#### 2.2 Expandir Cache Redis

**Arquivo:** `database.py`

```python
# Remover o decorator duplicado (linhas 1054-1065)

# Aplicar cache em funções pesadas:
@cache_data("graficos_data", ex=300)  # 5 minutos
def get_graficos_data(codigo_rca=None):
    ...

@cache_data("stats_data", ex=120)  # 2 minutos
def get_stats_data(codigo_rca=None):
    ...

@cache_data("usuarios_list", ex=600)  # 10 minutos
def get_usuarios(filtro_rca=None, filtro_supervisor=None):
    ...
```

---

#### 2.3 Otimizar Query de Pedidos Pendentes

**Substituir NOT EXISTS por LEFT JOIN:**

```sql
-- DE:
SELECT COUNT(*) FROM PCPEDC p
WHERE NOT EXISTS (SELECT 1 FROM DSLTI_PEDAGEND a WHERE a.NUMPED = p.NUMPED)

-- PARA:
SELECT COUNT(*) FROM PCPEDC p
LEFT JOIN DSLTI_PEDAGEND a ON a.NUMPED = p.NUMPED
WHERE a.NUMPED IS NULL
AND p.CODSUPERVISOR NOT IN (9130)
AND p.DATA >= DATE '2026-01-01'  -- Usar literal DATE em vez de TO_DATE
```

---

### FASE 3 - MÉDIO (Melhorias Contínuas)

#### 3.1 Batch para Atualização em Massa

**Arquivo:** `database.py`

```python
def atualizar_agendamento_massa(numpeds_list, preventrega_str, horaini_str, horafim_str, observacao):
    """Versão otimizada com batch insert"""
    with get_db_connection() as connection:
        cursor = connection.cursor()
        
        # Validações em batch
        # ...
        
        # INSERT em batch usando executemany (já existe, mas precisa usar pool)
        cursor.executemany(sql_insert, dados_insert)
        connection.commit()
```

---

#### 3.2 Consolidar Queries de Gráficos

**Criar uma única query que retorna todos os dados:**

```python
def get_all_dashboard_data(codigo_rca=None):
    """Busca todos os dados do dashboard em uma única conexão"""
    with get_db_connection() as connection:
        cursor = connection.cursor()
        
        # KPIs
        cursor.execute(kpis_query)
        kpis = cursor.fetchall()
        
        # Gráficos
        cursor.execute(graficos_query)
        graficos = cursor.fetchall()
        
        # Stats
        cursor.execute(stats_query)
        stats = cursor.fetchall()
        
        return {'kpis': kpis, 'graficos': graficos, 'stats': stats}
```

---

## 🔧 CONFIGURAÇÕES RECOMENDADAS

### Oracle (sqlnet.ora / tnsnames.ora)

```
# Otimizações de rede
SQLNET.RECV_TIMEOUT=60
SQLNET.SEND_TIMEOUT=60
SDU=32767
TDU=32767
```

### Gunicorn (produção)

```bash
gunicorn app:app \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --timeout 120 \
    --keep-alive 5 \
    --bind 0.0.0.0:5100
```

### Redis

```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

---

## 📈 MÉTRICAS DE SUCESSO

| Métrica | Atual (estimado) | Meta |
|---------|------------------|------|
| Tempo carregamento Dashboard | 3-8 segundos | < 1 segundo |
| Conexões Oracle por requisição | 10-15 | 1-2 |
| Hit rate do cache | ~20% | > 80% |
| Tempo médio de query | 200-500ms | < 100ms |

---

## 🗓️ CRONOGRAMA SUGERIDO

| Fase | Atividade | Prazo | Impacto |
|------|-----------|-------|---------|
| 1.1 | Connection Pool | 1-2 dias | Alto |
| 1.2 | Reutilização de conexão | 1 dia | Alto |
| 2.1 | Criação de índices | 1 dia | Médio-Alto |
| 2.2 | Expandir cache | 1 dia | Médio |
| 2.3 | Otimizar queries | 2-3 dias | Médio |
| 3.x | Melhorias contínuas | Ongoing | Baixo-Médio |

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

1. **Teste em ambiente de homologação** antes de aplicar em produção
2. **Monitore o Oracle** com AWR/ASH reports antes e depois das mudanças
3. **Índices consomem espaço** - valide com DBA a estratégia de indexação
4. **Connection Pool** requer ajuste fino dos parâmetros min/max baseado na carga

---

## ✅ IMPLEMENTAÇÕES REALIZADAS (23/01/2026)

### Fase 1 - Crítico ✅ CONCLUÍDO

| Item | Status | Arquivo |
|------|--------|---------|
| Connection Pool Oracle | ✅ Implementado | `database.py` |
| Context Manager `get_db_connection()` | ✅ Implementado | `database.py` |
| Refatoração para `release_connection()` | ✅ Implementado | `database.py` |

### Fase 2 - Alto ✅ CONCLUÍDO

| Item | Status | Arquivo |
|------|--------|---------|
| Script SQL para índices | ✅ Criado | `scripts/indices_oracle.sql` |
| Cache em `get_graficos_data()` | ✅ Implementado | `database.py` |
| Cache em `get_stats_data()` | ✅ Implementado | `database.py` |
| Query otimizada (LEFT JOIN) | ✅ Implementado | `database.py` |

### Fase 3 - Manutenção ✅ CONCLUÍDO

| Item | Status | Arquivo |
|------|--------|---------|
| Remoção de código duplicado | ✅ Implementado | `database.py` |
| `functools.wraps` no decorator | ✅ Implementado | `database.py` |

---

## 📞 PRÓXIMOS PASSOS

1. ✅ ~~Implementar connection pool (maior impacto imediato)~~ FEITO
2. ✅ ~~Aplicar cache nas funções identificadas~~ FEITO
3. ⏳ **Executar script de índices no Oracle** (`scripts/indices_oracle.sql`)
4. ⏳ Monitorar tempos de resposta após deploy
5. ⏳ Ajustar parâmetros do pool (min/max) conforme carga real

---

*Documento gerado e atualizado como parte da análise de performance do sistema DSL Agendamento*
