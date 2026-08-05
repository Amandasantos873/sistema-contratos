-- =============================================================
-- SISTEMA DE GESTÃO DE CONTRATOS E FATURAMENTO
-- Módulo 02 — Contratos
-- Banco: PostgreSQL 14+
-- Depende do Módulo 01 (clientes)
-- =============================================================

-- -------------------------------------------------------------
-- TIPOS ENUMERADOS
-- -------------------------------------------------------------
CREATE TYPE modalidade_contrato  AS ENUM ('ASP', 'BSP', 'BPO');
CREATE TYPE status_contrato      AS ENUM ('PROPOSTA', 'ATIVO', 'SUSPENSO', 'ENCERRADO', 'CANCELADO');
CREATE TYPE fase_contrato        AS ENUM ('IMPLANTACAO', 'RECORRENCIA');
CREATE TYPE dia_faturamento      AS ENUM ('DIA_01', 'DIA_15', 'DIA_25');
CREATE TYPE status_parcela_impl  AS ENUM ('PENDENTE', 'FATURADA', 'PAGA', 'CANCELADA');


-- -------------------------------------------------------------
-- TABELA: produtos_servicos
-- Catálogo de itens disponíveis por modalidade
-- -------------------------------------------------------------
CREATE TABLE produtos_servicos (
    id              SERIAL PRIMARY KEY,
    modalidade      modalidade_contrato NOT NULL,
    codigo          VARCHAR(30) NOT NULL,
    nome            VARCHAR(200) NOT NULL,
    descricao       TEXT,
    unidade         VARCHAR(30) NOT NULL DEFAULT 'MÊS',  -- MÊS, HORA, USUÁRIO, TRANSAÇÃO...
    preco_tabela    NUMERIC(15,2),                        -- preço de tabela (referência)
    permite_impl    BOOLEAN NOT NULL DEFAULT FALSE,       -- pode ser cobrado na implantação
    permite_recorr  BOOLEAN NOT NULL DEFAULT TRUE,        -- pode ser cobrado na recorrência
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_produto_codigo UNIQUE (modalidade, codigo)
);

COMMENT ON TABLE  produtos_servicos              IS 'Catálogo de produtos/serviços disponíveis por modalidade';
COMMENT ON COLUMN produtos_servicos.preco_tabela IS 'Preço de tabela usado como referência; o valor efetivo é negociado no contrato';


-- -------------------------------------------------------------
-- TABELA: contratos
-- Cabeçalho do contrato
-- -------------------------------------------------------------
CREATE TABLE contratos (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero                  VARCHAR(30) NOT NULL UNIQUE,  -- ex: CTR-2025-0001
    cliente_id              UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    modalidade              modalidade_contrato NOT NULL,

    -- Vigência
    data_assinatura         DATE NOT NULL,
    data_inicio_impl        DATE NOT NULL,              -- início da implantação
    data_goLive             DATE,                       -- preenchido quando equipe libera
    data_inicio_recorrencia DATE,                       -- calculado a partir do go-live
    prazo_meses             INTEGER NOT NULL CHECK (prazo_meses > 0),
    data_fim_contrato       DATE,                       -- calculado: inicio_recorrencia + prazo
    data_renovacao          DATE,                       -- preenchido na renovação

    -- Faturamento
    dia_faturamento         dia_faturamento NOT NULL,
    fase_atual              fase_contrato NOT NULL DEFAULT 'IMPLANTACAO',
    status                  status_contrato NOT NULL DEFAULT 'PROPOSTA',

    -- Valores consolidados (calculados a partir dos itens)
    valor_total_impl        NUMERIC(15,2) NOT NULL DEFAULT 0,
    valor_mensal            NUMERIC(15,2) NOT NULL DEFAULT 0,

    -- Responsáveis
    responsavel_comercial   VARCHAR(100),
    responsavel_implantacao VARCHAR(100),

    -- Documentos
    numero_proposta         VARCHAR(50),
    observacoes             TEXT,

    -- Auditoria
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por              VARCHAR(100) NOT NULL,
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por          VARCHAR(100) NOT NULL,

    CONSTRAINT chk_goLive_apos_impl CHECK (
        data_goLive IS NULL OR data_goLive >= data_inicio_impl
    ),
    CONSTRAINT chk_recorrencia_apos_goLive CHECK (
        data_inicio_recorrencia IS NULL OR data_goLive IS NOT NULL
    )
);

COMMENT ON TABLE  contratos                       IS 'Cabeçalho do contrato. Um cliente pode ter múltiplos contratos.';
COMMENT ON COLUMN contratos.numero                IS 'Número sequencial gerado pelo sistema. Ex: CTR-2025-0001';
COMMENT ON COLUMN contratos.dia_faturamento       IS 'Data de apuração/faturamento mensal definida pelo comercial: 1º dia útil, dia 15 ou dia 25';
COMMENT ON COLUMN contratos.fase_atual            IS 'IMPLANTACAO: cobrando parcelas de implantação | RECORRENCIA: cobrando mensalidade';
COMMENT ON COLUMN contratos.valor_total_impl      IS 'Soma das parcelas de implantação. Atualizado automaticamente via trigger.';
COMMENT ON COLUMN contratos.valor_mensal          IS 'Soma dos itens recorrentes. Atualizado automaticamente via trigger.';


-- -------------------------------------------------------------
-- TABELA: contratos_itens
-- Itens contratados (produtos/serviços com valores negociados)
-- -------------------------------------------------------------
CREATE TABLE contratos_itens (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_id         UUID NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    produto_id          INTEGER NOT NULL REFERENCES produtos_servicos(id) ON DELETE RESTRICT,

    -- Valores negociados
    quantidade          NUMERIC(10,3) NOT NULL DEFAULT 1,
    valor_unitario      NUMERIC(15,2) NOT NULL,
    desconto_pct        NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (desconto_pct BETWEEN 0 AND 100),
    valor_total         NUMERIC(15,2) GENERATED ALWAYS AS (
                            ROUND(quantidade * valor_unitario * (1 - desconto_pct / 100), 2)
                        ) STORED,

    -- Qual fase este item pertence
    fase                fase_contrato NOT NULL,

    -- Controle
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes         TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  contratos_itens           IS 'Itens contratados com valores negociados. Um item pode ser de implantação ou recorrência.';
COMMENT ON COLUMN contratos_itens.fase      IS 'IMPLANTACAO: cobrado nas parcelas de impl | RECORRENCIA: cobrado mensalmente';
COMMENT ON COLUMN contratos_itens.valor_total IS 'Calculado: qtd × valor_unitario × (1 - desconto%). Coluna gerada (STORED).';


-- -------------------------------------------------------------
-- TABELA: contratos_parcelas_implantacao
-- Parcelas da fase de implantação (quantidade e valores livres)
-- -------------------------------------------------------------
CREATE TABLE contratos_parcelas_implantacao (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_id     UUID NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    numero_parcela  INTEGER NOT NULL,
    valor           NUMERIC(15,2) NOT NULL CHECK (valor > 0),
    data_vencimento DATE NOT NULL,
    status          status_parcela_impl NOT NULL DEFAULT 'PENDENTE',
    data_faturamento DATE,
    data_pagamento   DATE,
    observacoes      TEXT,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_parcela_contrato UNIQUE (contrato_id, numero_parcela),
    CONSTRAINT chk_pagamento_apos_faturamento CHECK (
        data_pagamento IS NULL OR data_faturamento IS NOT NULL
    )
);

COMMENT ON TABLE  contratos_parcelas_implantacao IS 'Parcelas de implantação. Quantidade e valores definidos na negociação.';


-- -------------------------------------------------------------
-- TABELA: contratos_aditivos
-- Registro de aditivos contratuais (preparado para Módulo 04)
-- -------------------------------------------------------------
CREATE TABLE contratos_aditivos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_id     UUID NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    numero_aditivo  INTEGER NOT NULL,
    tipo            VARCHAR(50) NOT NULL,   -- REAJUSTE, PRAZO, VALOR, ESCOPO, RESCISAO
    descricao       TEXT NOT NULL,
    data_aditivo    DATE NOT NULL,
    data_vigencia   DATE NOT NULL,
    valor_anterior  NUMERIC(15,2),
    valor_novo      NUMERIC(15,2),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100) NOT NULL,

    CONSTRAINT uq_aditivo_contrato UNIQUE (contrato_id, numero_aditivo)
);

COMMENT ON TABLE contratos_aditivos IS 'Aditivos contratuais. Detalhado no Módulo 04 (Reajustes e Aditivos).';


-- -------------------------------------------------------------
-- TABELA: contratos_historico
-- Auditoria de alterações no contrato
-- -------------------------------------------------------------
CREATE TABLE contratos_historico (
    id              BIGSERIAL PRIMARY KEY,
    contrato_id     UUID NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    operacao        CHAR(1) NOT NULL CHECK (operacao IN ('I','U','D')),
    campo_alterado  VARCHAR(100),
    valor_anterior  TEXT,
    valor_novo      TEXT,
    alterado_por    VARCHAR(100) NOT NULL,
    alterado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    motivo          TEXT
);


-- -------------------------------------------------------------
-- ÍNDICES
-- -------------------------------------------------------------
CREATE INDEX idx_contratos_cliente_id   ON contratos (cliente_id);
CREATE INDEX idx_contratos_status       ON contratos (status);
CREATE INDEX idx_contratos_modalidade   ON contratos (modalidade);
CREATE INDEX idx_contratos_fase_atual   ON contratos (fase_atual);
CREATE INDEX idx_contratos_dia_fat      ON contratos (dia_faturamento);
CREATE INDEX idx_contratos_goLive       ON contratos (data_goLive);
CREATE INDEX idx_contratos_fim          ON contratos (data_fim_contrato);
CREATE INDEX idx_itens_contrato_id      ON contratos_itens (contrato_id);
CREATE INDEX idx_parcelas_contrato_id   ON contratos_parcelas_implantacao (contrato_id);
CREATE INDEX idx_parcelas_vencimento    ON contratos_parcelas_implantacao (data_vencimento);
CREATE INDEX idx_parcelas_status        ON contratos_parcelas_implantacao (status);
CREATE INDEX idx_produtos_modalidade    ON produtos_servicos (modalidade);


-- -------------------------------------------------------------
-- FUNÇÃO: atualiza timestamp
-- -------------------------------------------------------------
CREATE TRIGGER trg_contratos_timestamp
    BEFORE UPDATE ON contratos
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE TRIGGER trg_itens_timestamp
    BEFORE UPDATE ON contratos_itens
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE TRIGGER trg_parcelas_timestamp
    BEFORE UPDATE ON contratos_parcelas_implantacao
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();


-- -------------------------------------------------------------
-- FUNÇÃO: recalcula valores consolidados no cabeçalho do contrato
-- Executada sempre que um item é inserido, atualizado ou removido
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_recalcula_valores_contrato()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_contrato_id UUID;
BEGIN
    v_contrato_id := COALESCE(NEW.contrato_id, OLD.contrato_id);

    UPDATE contratos SET
        valor_total_impl = (
            SELECT COALESCE(SUM(ci.valor_total), 0)
            FROM contratos_itens ci
            WHERE ci.contrato_id = v_contrato_id
              AND ci.fase = 'IMPLANTACAO'
              AND ci.ativo = TRUE
        ),
        valor_mensal = (
            SELECT COALESCE(SUM(ci.valor_total), 0)
            FROM contratos_itens ci
            WHERE ci.contrato_id = v_contrato_id
              AND ci.fase = 'RECORRENCIA'
              AND ci.ativo = TRUE
        ),
        atualizado_em = NOW()
    WHERE id = v_contrato_id;

    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_recalcula_valores
    AFTER INSERT OR UPDATE OR DELETE ON contratos_itens
    FOR EACH ROW EXECUTE FUNCTION fn_recalcula_valores_contrato();


-- -------------------------------------------------------------
-- FUNÇÃO: ao registrar go-live, calcula datas de recorrência
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_processa_goLive()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Só executa quando data_goLive é preenchida pela primeira vez
    IF NEW.data_goLive IS NOT NULL AND OLD.data_goLive IS NULL THEN
        NEW.data_inicio_recorrencia := NEW.data_goLive;
        NEW.data_fim_contrato       := NEW.data_goLive + (NEW.prazo_meses * INTERVAL '1 month');
        NEW.fase_atual              := 'RECORRENCIA';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_processa_goLive
    BEFORE UPDATE ON contratos
    FOR EACH ROW EXECUTE FUNCTION fn_processa_goLive();


-- -------------------------------------------------------------
-- FUNÇÃO: gera número sequencial do contrato
-- Formato: CTR-YYYY-NNNN
-- -------------------------------------------------------------
CREATE SEQUENCE seq_contrato_numero START 1;

CREATE OR REPLACE FUNCTION fn_gera_numero_contrato()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.numero IS NULL OR NEW.numero = '' THEN
        NEW.numero := 'CTR-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
                      LPAD(NEXTVAL('seq_contrato_numero')::TEXT, 4, '0');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_numero_contrato
    BEFORE INSERT ON contratos
    FOR EACH ROW EXECUTE FUNCTION fn_gera_numero_contrato();


-- -------------------------------------------------------------
-- FUNÇÃO: impede inativação de cliente com contrato ativo
-- (complementa a trigger do Módulo 01)
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_valida_inativacao_cliente_v2()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IN ('INATIVO', 'BLOQUEADO') AND OLD.status = 'ATIVO' THEN
        IF EXISTS (
            SELECT 1 FROM contratos
            WHERE cliente_id = NEW.id
              AND status IN ('PROPOSTA', 'ATIVO', 'SUSPENSO')
        ) THEN
            RAISE EXCEPTION 'Não é possível inativar o cliente: existem contratos ativos ou em proposta.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

-- Substitui a trigger stub do Módulo 01
DROP TRIGGER IF EXISTS trg_valida_inativacao ON clientes;
CREATE TRIGGER trg_valida_inativacao
    BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION fn_valida_inativacao_cliente_v2();


-- -------------------------------------------------------------
-- VIEW: contratos_resumo
-- Visão consolidada para listagens
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_contratos_resumo AS
SELECT
    c.id,
    c.numero,
    cl.id                                               AS cliente_id,
    COALESCE(cl.razao_social, cl.nome_completo)         AS cliente_nome,
    c.modalidade,
    c.status,
    c.fase_atual,
    c.dia_faturamento,
    c.data_assinatura,
    c.data_inicio_impl,
    c.data_goLive,
    c.data_inicio_recorrencia,
    c.data_fim_contrato,
    c.prazo_meses,
    c.valor_total_impl,
    c.valor_mensal,
    c.responsavel_comercial,
    -- Parcelas de implantação
    (SELECT COUNT(*) FROM contratos_parcelas_implantacao p
     WHERE p.contrato_id = c.id)                        AS qtd_parcelas_impl,
    (SELECT COUNT(*) FROM contratos_parcelas_implantacao p
     WHERE p.contrato_id = c.id AND p.status = 'PAGA')  AS qtd_parcelas_pagas,
    -- Dias até o fim do contrato
    CASE WHEN c.data_fim_contrato IS NOT NULL
         THEN (c.data_fim_contrato - CURRENT_DATE)
         ELSE NULL
    END                                                  AS dias_ate_fim,
    c.criado_em
FROM contratos c
JOIN clientes cl ON cl.id = c.cliente_id;

COMMENT ON VIEW vw_contratos_resumo IS 'Visão consolidada de contratos com dados do cliente e progresso das parcelas.';


-- -------------------------------------------------------------
-- VIEW: contratos_a_faturar
-- Contratos em recorrência agrupados por data de faturamento
-- Usada pelo motor de faturamento (Módulo 05)
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_contratos_a_faturar AS
SELECT
    c.id                AS contrato_id,
    c.numero,
    c.cliente_id,
    COALESCE(cl.razao_social, cl.nome_completo) AS cliente_nome,
    c.modalidade,
    c.dia_faturamento,
    c.valor_mensal,
    c.data_fim_contrato
FROM contratos c
JOIN clientes cl ON cl.id = c.cliente_id
WHERE c.status    = 'ATIVO'
  AND c.fase_atual = 'RECORRENCIA'
  AND (c.data_fim_contrato IS NULL OR c.data_fim_contrato >= CURRENT_DATE);

COMMENT ON VIEW vw_contratos_a_faturar IS 'Contratos elegíveis para faturamento mensal recorrente. Filtrado por dia_faturamento no serviço.';


-- -------------------------------------------------------------
-- DADOS INICIAIS: catálogo de produtos/serviços por modalidade
-- -------------------------------------------------------------
INSERT INTO produtos_servicos (modalidade, codigo, nome, unidade, preco_tabela, permite_impl, permite_recorr) VALUES
    -- ASP
    ('ASP', 'ASP-IMPL-SETUP',   'Setup e configuração do ambiente',    'PROJETO', NULL,    TRUE,  FALSE),
    ('ASP', 'ASP-IMPL-TREINO',  'Treinamento de usuários',             'HORA',    NULL,    TRUE,  FALSE),
    ('ASP', 'ASP-LIC-USUARIO',  'Licença por usuário',                 'USUÁRIO', NULL,    FALSE, TRUE),
    ('ASP', 'ASP-LIC-BASE',     'Licença base do sistema',             'MÊS',     NULL,    FALSE, TRUE),
    ('ASP', 'ASP-SUPORTE',      'Suporte técnico',                     'MÊS',     NULL,    FALSE, TRUE),
    -- BSP
    ('BSP', 'BSP-IMPL-SETUP',   'Setup e parametrização BSP',          'PROJETO', NULL,    TRUE,  FALSE),
    ('BSP', 'BSP-IMPL-INTEG',   'Integração com sistemas legados',     'PROJETO', NULL,    TRUE,  FALSE),
    ('BSP', 'BSP-OPER-MENSAL',  'Fee de operação mensal',              'MÊS',     NULL,    FALSE, TRUE),
    ('BSP', 'BSP-TRANSACAO',    'Taxa por transação processada',       'TRANSAÇÃO',NULL,   FALSE, TRUE),
    ('BSP', 'BSP-SUPORTE',      'Suporte e monitoramento',             'MÊS',     NULL,    FALSE, TRUE),
    -- BPO
    ('BPO', 'BPO-IMPL-PROC',    'Mapeamento e implantação de processo', 'PROJETO', NULL,   TRUE,  FALSE),
    ('BPO', 'BPO-IMPL-TREINO',  'Capacitação da equipe',               'HORA',    NULL,    TRUE,  FALSE),
    ('BPO', 'BPO-GESTAO-MENSAL','Gestão do processo terceirizado',     'MÊS',     NULL,    FALSE, TRUE),
    ('BPO', 'BPO-HORA-TECNICA', 'Hora técnica especialista',           'HORA',    NULL,    FALSE, TRUE),
    ('BPO', 'BPO-RELATORIO',    'Relatórios e dashboards gerenciais',  'MÊS',     NULL,    FALSE, TRUE);
