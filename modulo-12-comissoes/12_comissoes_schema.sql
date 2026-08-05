-- =============================================================
-- SISTEMA DE GESTÃO — Módulo 12: Comissões
-- Comissão eventual por indicação de parceiro — valor fixo por contrato
-- Fluxo: Registrada → Aguardando Aprovação → Aprovada → Paga
-- =============================================================

CREATE TYPE status_comissao AS ENUM (
    'REGISTRADA',
    'AGUARDANDO_APROVACAO',
    'APROVADA',
    'PAGA',
    'CANCELADA',
    'REPROVADA'
);


-- -------------------------------------------------------------
-- TABELA: parceiros
-- Pessoa física ou jurídica que indicou o cliente
-- -------------------------------------------------------------
CREATE TABLE parceiros (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome            VARCHAR(200) NOT NULL,
    tipo_pessoa     VARCHAR(2)   NOT NULL DEFAULT 'PF' CHECK (tipo_pessoa IN ('PF','PJ')),
    cpf_cnpj        VARCHAR(14)  UNIQUE,
    email           VARCHAR(254),
    telefone        VARCHAR(20),
    -- Dados bancários para pagamento da comissão
    banco           VARCHAR(100),
    agencia         VARCHAR(20),
    conta           VARCHAR(30),
    pix_chave       VARCHAR(150),
    -- Contrato / acordo de parceria
    percentual_padrao NUMERIC(5,2),     -- percentual padrão de comissão (se usar %)
    valor_fixo_padrao NUMERIC(15,2),    -- valor fixo padrão (se usar fixo)
    observacoes     TEXT,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100)
);

COMMENT ON TABLE parceiros IS 'Parceiros indicadores — recebem comissão por contrato fechado via indicação.';


-- -------------------------------------------------------------
-- TABELA: comissoes
-- Uma comissão por contrato indicado
-- -------------------------------------------------------------
CREATE TABLE comissoes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero_comissao     VARCHAR(30) NOT NULL UNIQUE,    -- COM-2026-00001
    parceiro_id         UUID NOT NULL REFERENCES parceiros(id) ON DELETE RESTRICT,
    contrato_id         UUID NOT NULL REFERENCES contratos(id) ON DELETE RESTRICT,
    -- Valor
    tipo_calculo        VARCHAR(10) NOT NULL DEFAULT 'FIXO' CHECK (tipo_calculo IN ('FIXO','PERCENTUAL')),
    percentual          NUMERIC(5,2),
    valor_base          NUMERIC(15,2),          -- valor do contrato base para cálculo
    valor_comissao      NUMERIC(15,2) NOT NULL, -- valor final a pagar
    -- Fluxo
    status              status_comissao NOT NULL DEFAULT 'REGISTRADA',
    data_registro       DATE NOT NULL DEFAULT CURRENT_DATE,
    motivo              TEXT,                   -- descrição da indicação
    -- Aprovação
    aprovado_por        VARCHAR(100),
    data_aprovacao      DATE,
    motivo_reprovacao   TEXT,
    -- Pagamento
    data_pagamento      DATE,
    forma_pagamento     VARCHAR(30),
    identificador_pag   VARCHAR(100),
    -- Vínculo com contas a pagar (quando pago pelo módulo 08)
    despesa_id          UUID REFERENCES despesas(id),
    -- Controle
    observacoes         TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL,
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por      VARCHAR(100) NOT NULL,

    CONSTRAINT uq_comissao_contrato UNIQUE (contrato_id)  -- um contrato, uma comissão
);

COMMENT ON TABLE  comissoes             IS 'Comissões por indicação de parceiros. Uma por contrato.';
COMMENT ON COLUMN comissoes.despesa_id  IS 'Quando pago, vincula à despesa gerada no módulo 08 para conciliação.';

CREATE INDEX idx_comissoes_parceiro_id  ON comissoes (parceiro_id);
CREATE INDEX idx_comissoes_contrato_id  ON comissoes (contrato_id);
CREATE INDEX idx_comissoes_status       ON comissoes (status);


-- -------------------------------------------------------------
-- SEQUÊNCIA: número da comissão
-- -------------------------------------------------------------
CREATE SEQUENCE seq_comissao_numero START 1;

CREATE OR REPLACE FUNCTION fn_gera_numero_comissao()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.numero_comissao IS NULL OR NEW.numero_comissao = '' THEN
        NEW.numero_comissao := 'COM-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
                               LPAD(NEXTVAL('seq_comissao_numero')::TEXT, 5, '0');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_numero_comissao
    BEFORE INSERT ON comissoes
    FOR EACH ROW EXECUTE FUNCTION fn_gera_numero_comissao();


-- -------------------------------------------------------------
-- VIEW: vw_comissoes_resumo
-- Painel principal com dados do parceiro e contrato
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_comissoes_resumo AS
SELECT
    c.id,
    c.numero_comissao,
    p.nome                                          AS parceiro_nome,
    p.cpf_cnpj                                      AS parceiro_documento,
    p.pix_chave,
    ct.numero                                       AS contrato_numero,
    COALESCE(cl.razao_social, cl.nome_completo)     AS cliente_nome,
    ct.modalidade,
    ct.data_assinatura,
    c.tipo_calculo,
    c.percentual,
    c.valor_base,
    c.valor_comissao,
    c.status,
    c.data_registro,
    c.motivo,
    c.aprovado_por,
    c.data_aprovacao,
    c.data_pagamento,
    c.forma_pagamento,
    c.criado_em
FROM comissoes c
JOIN parceiros p  ON p.id  = c.parceiro_id
JOIN contratos ct ON ct.id = c.contrato_id
JOIN clientes  cl ON cl.id = ct.cliente_id
ORDER BY c.data_registro DESC;
