-- ============================================
-- CREDENCIAIS DE SENHA PARA LOGIN DE RCA
-- Sistema: DSL Agendamento
-- Data: 16/10/2026
-- ============================================
-- Guarda SOMENTE o hash da senha (nunca a senha em texto). O hash deve ser
-- gerado na aplicação (werkzeug.security.generate_password_hash, scrypt/pbkdf2,
-- com salt embutido). O app nunca grava/lê senha pura.
--
-- Tabela separada (e não coluna em PCUSUARI) porque PCUSUARI é tabela do ERP
-- Winthor: alterar a estrutura dela pode quebrar atualizações do ERP e exige
-- privilégios de DDL no objeto do ERP.
--
-- Escopo: apenas logins de origem RCA (PCUSUARI.CODUSUR). Usuários PCEMPR
-- continuam autenticando como já fazem hoje.
--
-- Execute conectado como DSL (ou usuário com CREATE TABLE no schema DSL).

CREATE TABLE DSL.DSLTI_RCA_AUTH (
    CODUSUR            NUMBER(6)      NOT NULL,
    SENHA_HASH         VARCHAR2(255)  NULL,      -- NULL = RCA ainda sem senha definida (primeiro acesso)
    SENHA_ATUALIZADA_EM DATE          NULL,
    TENTATIVAS_FALHAS  NUMBER(3)      DEFAULT 0 NOT NULL,
    BLOQUEADO_ATE      DATE           NULL,      -- bloqueio temporário após N falhas
    ULTIMO_LOGIN_EM    DATE           NULL,
    CRIADO_EM          DATE           DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_DSLTI_RCA_AUTH PRIMARY KEY (CODUSUR)
);

-- Garante que só existam credenciais para RCAs que existem no ERP.
-- (Comente esta linha se DSL não tiver PK/UK em PCUSUARI.CODUSUR para referenciar.)
ALTER TABLE DSL.DSLTI_RCA_AUTH
    ADD CONSTRAINT FK_RCA_AUTH_PCUSUARI
    FOREIGN KEY (CODUSUR) REFERENCES DSL.PCUSUARI (CODUSUR);

COMMENT ON TABLE  DSL.DSLTI_RCA_AUTH IS 'Credenciais de senha dos RCAs (login do sistema de agendamento)';
COMMENT ON COLUMN DSL.DSLTI_RCA_AUTH.SENHA_HASH IS 'Hash da senha (werkzeug, com salt). Nunca texto puro.';

-- ============================================
-- VERIFICAÇÃO
-- ============================================
-- SELECT column_name, data_type, data_length, nullable
--   FROM all_tab_columns
--  WHERE owner = 'DSL' AND table_name = 'DSLTI_RCA_AUTH'
--  ORDER BY column_id;

-- ============================================
-- ROLLBACK (se necessário)
-- ============================================
-- DROP TABLE DSL.DSLTI_RCA_AUTH PURGE;
