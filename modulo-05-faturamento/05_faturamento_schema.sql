-- =============================================================
-- SISTEMA DE GESTÃO DE CONTRATOS E FATURAMENTO
-- Módulo 05 — Faturamento
-- Banco: PostgreSQL 14+
-- Depende dos Módulos 01 a 04
-- =============================================================

-- -------------------------------------------------------------
-- TIPOS ENUMERADOS
-- -------------------------------------------------------------
CREATE TYPE status_fatura       AS ENUM ('RASCUNHO','APURADA','EMITIDA','ENVIADA','PAGA','CANCELADA','INADIMPLENTE');
CREATE TYPE tipo_documento_fat  AS ENUM ('RPS','NFS_E','BOLETO','BOLETIM_MEDICAO','DESCRITIVO');
CREATE TYPE status_documento    AS ENUM ('PENDENTE','EMITIDO','ENVIADO','CANCELADO','ERRO');
CREATE TYPE tipo_vinculo_folha  AS ENUM ('CLT','AUTONOMO','ESTAGIARIO','SOCIO','DIRETOR','COOPERADO','OUTROS');


-- -------------------------------------------------------------
-- TABELA: faixas_volumetria
-- Preço por faixa de quantidade de vínculos
-- Cada item do catálogo pode ter faixas diferentes
-- -------------------------------------------------------------
CREATE TABLE faixas_volumetria (
    id              SERIAL PRIMARY KEY,
    produto_id      INTEGER NOT NULL REFERENCES produtos_servicos(id) ON DELETE CASCADE,
    tipo_vinculo    tipo_vinculo_folha NOT NULL,
    faixa_de        INTEGER NOT NULL CHECK (faixa_de >= 0),
    faixa_ate       INTEGER,                    -- NULL = sem limite superior
    valor_unitario  NUMERIC(15,4) NOT NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim    DATE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100),

    CONSTRAINT chk_faixa_intervalo CHECK (faixa_ate IS NULL OR faixa_ate > faixa_de)
);

COMMENT ON TABLE  faixas_volumetria           IS 'Tabela de preços por faixa de volumetria para itens de folha de pagamento (BPO/BSP)';
COMMENT ON COLUMN faixas_volumetria.faixa_de  IS 'Quantidade mínima (inclusive) para aplicar este preço';
COMMENT ON COLUMN faixas_volumetria.faixa_ate IS 'Quantidade máxima (inclusive). NULL = sem limite';


-- -------------------------------------------------------------
-- TABELA: faturas
-- Cabeçalho da fatura mensal por contrato
-- -------------------------------------------------------------
CREATE TABLE faturas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_id         UUID NOT NULL REFERENCES contratos(id) ON DELETE RESTRICT,
    numero_fatura       VARCHAR(30) NOT NULL UNIQUE,    -- ex: FAT-2026-00001
    competencia         DATE NOT NULL,                  -- sempre 1º dia do mês
    dia_apuracao        dia_faturamento NOT NULL,
    data_apuracao       DATE NOT NULL,                  -- data real da apuração (1º útil, 15 ou 25)
    data_vencimento     DATE NOT NULL,
    status              status_fatura NOT NULL DEFAULT 'RASCUNHO',

    -- Valores
    valor_servicos      NUMERIC(15,2) NOT NULL DEFAULT 0,
    valor_volumetria    NUMERIC(15,2) NOT NULL DEFAULT 0,
    valor_total         NUMERIC(15,2) GENERATED ALWAYS AS (valor_servicos + valor_volumetria) STORED,
    valor_pago          NUMERIC(15,2),
    data_pagamento      DATE,

    -- NFS-e / K2
    descricao_nf        TEXT,                           -- "Prestação de Serviços Conforme Contrato..."
    numero_nf           VARCHAR(30),
    serie_nf            VARCHAR(10),
    codigo_verificacao  VARCHAR(50),
    data_emissao_nf     DATE,

    -- Controle
    observacoes         TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL,
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por      VARCHAR(100) NOT NULL,

    CONSTRAINT chk_competencia_dia1 CHECK (EXTRACT(DAY FROM competencia) = 1)
);

COMMENT ON TABLE  faturas                  IS 'Fatura mensal por contrato. Uma fatura por competência por contrato.';
COMMENT ON COLUMN faturas.competencia      IS 'Mês de referência do serviço. Sempre o 1º dia do mês.';
COMMENT ON COLUMN faturas.descricao_nf     IS 'Texto padrão enviado ao K2 para emissão da NFS-e.';

CREATE UNIQUE INDEX uq_fatura_contrato_competencia ON faturas (contrato_id, competencia);


-- -------------------------------------------------------------
-- TABELA: faturas_itens
-- Detalhamento dos itens cobrados em cada fatura
-- -------------------------------------------------------------
CREATE TABLE faturas_itens (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fatura_id           UUID NOT NULL REFERENCES faturas(id) ON DELETE CASCADE,
    contrato_item_id    UUID NOT NULL REFERENCES contratos_itens(id) ON DELETE RESTRICT,
    produto_id          INTEGER NOT NULL REFERENCES produtos_servicos(id),
    descricao           VARCHAR(300) NOT NULL,
    quantidade          NUMERIC(10,3) NOT NULL DEFAULT 1,
    valor_unitario      NUMERIC(15,4) NOT NULL,
    desconto_pct        NUMERIC(5,2) NOT NULL DEFAULT 0,
    valor_total         NUMERIC(15,2) GENERATED ALWAYS AS (
                            ROUND(quantidade * valor_unitario * (1 - desconto_pct / 100), 2)
                        ) STORED,
    eh_volumetria       BOOLEAN NOT NULL DEFAULT FALSE,
    observacoes         TEXT
);

COMMENT ON TABLE  faturas_itens             IS 'Itens detalhados da fatura. Base para o descritivo e boletim de medição.';
COMMENT ON COLUMN faturas_itens.eh_volumetria IS 'TRUE = linha de volumetria (vínculo × quantidade). FALSE = item contratual padrão.';


-- -------------------------------------------------------------
-- TABELA: faturas_volumetrias
-- Detalhe das volumetrias de folha recebidas via integração
-- -------------------------------------------------------------
CREATE TABLE faturas_volumetrias (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fatura_id       UUID NOT NULL REFERENCES faturas(id) ON DELETE CASCADE,
    contrato_item_id UUID NOT NULL REFERENCES contratos_itens(id),
    tipo_vinculo    tipo_vinculo_folha NOT NULL,
    quantidade      INTEGER NOT NULL CHECK (quantidade >= 0),
    valor_unitario  NUMERIC(15,4) NOT NULL,
    valor_total     NUMERIC(15,2) GENERATED ALWAYS AS (
                        ROUND(quantidade * valor_unitario, 2)
                    ) STORED,
    fonte           VARCHAR(100) DEFAULT 'INTEGRACAO_FOLHA',
    competencia_folha DATE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE faturas_volumetrias IS 'Volumetrias de folha de pagamento recebidas via integração. Base para o boletim de medição.';


-- -------------------------------------------------------------
-- TABELA: faturas_documentos
-- Rastreamento dos documentos emitidos para cada fatura
-- (RPS, NFS-e, boleto, boletim de medição, descritivo)
-- -------------------------------------------------------------
CREATE TABLE faturas_documentos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fatura_id       UUID NOT NULL REFERENCES faturas(id) ON DELETE CASCADE,
    tipo            tipo_documento_fat NOT NULL,
    status          status_documento NOT NULL DEFAULT 'PENDENTE',
    numero          VARCHAR(50),                -- número do documento no sistema externo
    url             VARCHAR(500),               -- link para download
    payload_envio   JSONB,                      -- dados enviados ao K2 / banco
    payload_retorno JSONB,                      -- resposta recebida
    mensagem_erro   TEXT,
    emitido_em      TIMESTAMPTZ,
    emitido_por     VARCHAR(100),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  faturas_documentos              IS 'Documentos emitidos por fatura: RPS, NFS-e, boleto, descritivo e boletim.';
COMMENT ON COLUMN faturas_documentos.payload_envio IS 'JSON completo enviado ao sistema externo (K2, banco). Auditoria.';


-- -------------------------------------------------------------
-- SEQUÊNCIA: número da fatura
-- -------------------------------------------------------------
CREATE SEQUENCE seq_fatura_numero START 1;

CREATE OR REPLACE FUNCTION fn_gera_numero_fatura()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.numero_fatura IS NULL OR NEW.numero_fatura = '' THEN
        NEW.numero_fatura := 'FAT-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
                             LPAD(NEXTVAL('seq_fatura_numero')::TEXT, 5, '0');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_numero_fatura
    BEFORE INSERT ON faturas
    FOR EACH ROW EXECUTE FUNCTION fn_gera_numero_fatura();


-- -------------------------------------------------------------
-- TRIGGER: recalcula totais da fatura quando itens mudam
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_recalcula_totais_fatura()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE v_fatura_id UUID;
BEGIN
    v_fatura_id := COALESCE(NEW.fatura_id, OLD.fatura_id);
    UPDATE faturas SET
        valor_servicos   = (SELECT COALESCE(SUM(valor_total),0) FROM faturas_itens WHERE fatura_id = v_fatura_id AND eh_volumetria = FALSE),
        valor_volumetria = (SELECT COALESCE(SUM(valor_total),0) FROM faturas_itens WHERE fatura_id = v_fatura_id AND eh_volumetria = TRUE),
        atualizado_em    = NOW()
    WHERE id = v_fatura_id;
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_recalcula_fatura_itens
    AFTER INSERT OR UPDATE OR DELETE ON faturas_itens
    FOR EACH ROW EXECUTE FUNCTION fn_recalcula_totais_fatura();

CREATE TRIGGER trg_recalcula_fatura_vol
    AFTER INSERT OR UPDATE OR DELETE ON faturas_volumetrias
    FOR EACH ROW EXECUTE FUNCTION fn_recalcula_totais_fatura();

CREATE TRIGGER trg_faturas_timestamp
    BEFORE UPDATE ON faturas
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();


-- -------------------------------------------------------------
-- FUNÇÃO: gera descrição padrão da NF para o K2
-- Formato: "Prestação de Serviços Conforme Contrato [MOD] competência MM/AAAA — Valor Total R$ X"
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_gera_descricao_nf(
    p_modalidade    TEXT,
    p_competencia   DATE,
    p_valor_total   NUMERIC
)
RETURNS TEXT LANGUAGE plpgsql AS $$
BEGIN
    RETURN 'Prestação de Serviços Conforme Contrato ' || p_modalidade ||
           ' competência ' || TO_CHAR(p_competencia, 'MM/YYYY') ||
           ' — Valor Total ' ||
           'R$ ' || REPLACE(TO_CHAR(p_valor_total, 'FM999G999G990D00'), '.', ',');
END;
$$;


-- -------------------------------------------------------------
-- ÍNDICES
-- -------------------------------------------------------------
CREATE INDEX idx_faturas_contrato_id    ON faturas (contrato_id);
CREATE INDEX idx_faturas_competencia    ON faturas (competencia);
CREATE INDEX idx_faturas_status         ON faturas (status);
CREATE INDEX idx_faturas_dia_apuracao   ON faturas (dia_apuracao);
CREATE INDEX idx_faturas_vencimento     ON faturas (data_vencimento);
CREATE INDEX idx_faturas_itens_fatura   ON faturas_itens (fatura_id);
CREATE INDEX idx_faturas_vol_fatura     ON faturas_volumetrias (fatura_id);
CREATE INDEX idx_fat_docs_fatura        ON faturas_documentos (fatura_id);
CREATE INDEX idx_faixas_produto         ON faixas_volumetria (produto_id, tipo_vinculo);


-- -------------------------------------------------------------
-- VIEW: vw_faturas_resumo
-- Visão consolidada para listagem de faturas
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_faturas_resumo AS
SELECT
    f.id,
    f.numero_fatura,
    f.contrato_id,
    c.numero                                            AS contrato_numero,
    COALESCE(cl.razao_social, cl.nome_completo)         AS cliente_nome,
    c.modalidade,
    f.competencia,
    f.dia_apuracao,
    f.data_apuracao,
    f.data_vencimento,
    f.status,
    f.valor_servicos,
    f.valor_volumetria,
    f.valor_total,
    f.valor_pago,
    f.numero_nf,
    f.data_emissao_nf,
    -- Documentos emitidos
    (SELECT COUNT(*) FROM faturas_documentos fd WHERE fd.fatura_id = f.id AND fd.status = 'EMITIDO') AS docs_emitidos,
    -- Dias em atraso (para inadimplência)
    CASE WHEN f.status NOT IN ('PAGA','CANCELADA') AND f.data_vencimento < CURRENT_DATE
         THEN (CURRENT_DATE - f.data_vencimento) ELSE 0 END                                          AS dias_atraso,
    f.criado_em
FROM faturas f
JOIN contratos c  ON c.id  = f.contrato_id
JOIN clientes cl  ON cl.id = c.cliente_id;

COMMENT ON VIEW vw_faturas_resumo IS 'Visão consolidada de faturas com dados do cliente, contrato e indicadores de inadimplência.';


-- -------------------------------------------------------------
-- VIEW: vw_apuracao_mensal
-- Mostra o que será faturado em cada data de apuração do mês
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_apuracao_mensal AS
SELECT
    c.dia_faturamento,
    COUNT(DISTINCT c.id)            AS contratos,
    COUNT(DISTINCT ci.id)           AS itens,
    SUM(ci.valor_total)             AS valor_previsto,
    -- Já faturado neste mês
    COUNT(DISTINCT f.id)            AS faturas_emitidas,
    SUM(f.valor_total)              AS valor_faturado
FROM contratos c
JOIN contratos_itens ci ON ci.contrato_id = c.id AND ci.fase = 'RECORRENCIA' AND ci.ativo = TRUE AND ci.status_item = 'ATIVO'
LEFT JOIN faturas f ON f.contrato_id = c.id AND DATE_TRUNC('month', f.competencia) = DATE_TRUNC('month', CURRENT_DATE)
WHERE c.status = 'ATIVO'
GROUP BY c.dia_faturamento;
