-- ============================================
-- SCRIPT DE CRIAÇÃO DE ÍNDICES PARA PERFORMANCE
-- Sistema: DSL Agendamento
-- Data: 23/01/2026
-- ============================================

-- IMPORTANTE: Execute este script conectado como DBA ou usuário com privilégio CREATE INDEX
-- Recomendação: Execute em horário de baixo uso do sistema

-- ============================================
-- ÍNDICES PARA TABELA DSLTI_PEDAGEND
-- ============================================

-- Índice principal para consultas por NUMPED (chave de junção mais frequente)
CREATE INDEX IDX_PEDAGEND_NUMPED ON DSLTI_PEDAGEND(NUMPED);

-- Índice para filtros por data de previsão de entrega
CREATE INDEX IDX_PEDAGEND_PREVENTREGA ON DSLTI_PEDAGEND(PREVENTREGA);

-- Índice para filtros por status
CREATE INDEX IDX_PEDAGEND_STATUS ON DSLTI_PEDAGEND(STATUS);

-- Índice composto para consultas frequentes (status + data)
CREATE INDEX IDX_PEDAGEND_STATUS_PREVENTREGA ON DSLTI_PEDAGEND(STATUS, PREVENTREGA);

-- ============================================
-- ÍNDICES PARA TABELA PCPEDC (se não existirem)
-- ============================================

-- Índice para filtro por data (consultas mais frequentes)
CREATE INDEX IDX_PCPEDC_DATA ON PCPEDC(DATA);

-- Índice para filtro por código do usuário/RCA
CREATE INDEX IDX_PCPEDC_CODUSUR ON PCPEDC(CODUSUR);

-- Índice para filtro por supervisor
CREATE INDEX IDX_PCPEDC_CODSUPERVISOR ON PCPEDC(CODSUPERVISOR);

-- Índice composto para consultas frequentes (data + supervisor)
CREATE INDEX IDX_PCPEDC_DATA_SUPERVISOR ON PCPEDC(DATA, CODSUPERVISOR);

-- Índice composto para consultas com RCA (data + codusur)
CREATE INDEX IDX_PCPEDC_DATA_CODUSUR ON PCPEDC(DATA, CODUSUR);

-- ============================================
-- ÍNDICES PARA TABELA PCUSUARI (se não existirem)
-- ============================================

-- Índice para filtro por código do usuário
CREATE INDEX IDX_PCUSUARI_CODUSUR ON DSL.PCUSUARI(CODUSUR);

-- Índice para filtro por data de término (usuários ativos)
CREATE INDEX IDX_PCUSUARI_DTTERMINO ON DSL.PCUSUARI(DTTERMINO);

-- ============================================
-- ÍNDICES PARA TABELA PCCLIENT (se não existirem)
-- ============================================

-- Índice para código do cliente (chave de junção)
CREATE INDEX IDX_PCCLIENT_CODCLI ON PCCLIENT(CODCLI);

-- ============================================
-- ÍNDICES PARA TABELA DE EVENTOS (FUSIONT)
-- Verificar se você tem acesso a este schema
-- ============================================

-- Índice composto para consultas de eventos por pedido e carga
-- NOTA: Execute apenas se tiver privilégios no schema FUSIONT
-- CREATE INDEX IDX_EVENTOS_PEDIDO_CARGA ON FUSIONT.FUSIONTRAK_INT_EVENTOS(seq_pedido_erp, carga_formada_erp);

-- Índice para ordenação por data de registro
-- CREATE INDEX IDX_EVENTOS_DATA_REGISTRO ON FUSIONT.FUSIONTRAK_INT_EVENTOS(DATA_REGISTRO DESC);

-- ============================================
-- ANÁLISE DE ESTATÍSTICAS
-- Execute após criar os índices para o otimizador
-- ============================================

-- Atualizar estatísticas das tabelas principais
BEGIN
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname => 'DSL',
        tabname => 'DSLTI_PEDAGEND',
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt => 'FOR ALL COLUMNS SIZE AUTO',
        cascade => TRUE
    );
END;
/

BEGIN
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname => 'DSL',
        tabname => 'PCPEDC',
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt => 'FOR ALL COLUMNS SIZE AUTO',
        cascade => TRUE
    );
END;
/

BEGIN
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname => 'DSL',
        tabname => 'PCUSUARI',
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt => 'FOR ALL COLUMNS SIZE AUTO',
        cascade => TRUE
    );
END;
/

-- ============================================
-- VERIFICAÇÃO DOS ÍNDICES CRIADOS
-- ============================================

SELECT 
    index_name,
    table_name,
    uniqueness,
    status
FROM 
    user_indexes
WHERE 
    table_name IN ('DSLTI_PEDAGEND', 'PCPEDC', 'PCUSUARI', 'PCCLIENT')
ORDER BY 
    table_name, index_name;

-- ============================================
-- SCRIPT PARA VERIFICAR SE ÍNDICES JÁ EXISTEM
-- Execute antes de criar para evitar erros
-- ============================================

/*
SELECT 
    index_name,
    table_name,
    column_name,
    column_position
FROM 
    user_ind_columns
WHERE 
    table_name IN ('DSLTI_PEDAGEND', 'PCPEDC', 'PCUSUARI', 'PCCLIENT')
ORDER BY 
    table_name, index_name, column_position;
*/
