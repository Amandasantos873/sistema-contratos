-- =============================================================
-- SISTEMA DE GESTÃO — Módulo 07: Contas a Receber
-- Depende do Módulo 05 (faturas)
-- =============================================================

CREATE TYPE forma_recebimento   AS ENUM ('BOLETO','PIX','TED','DOC','DEPOSITO','CARTAO','OUTROS');
CREATE TYPE status_cobranca     AS ENUM ('ABERTA','RECEBIDA','PARCIAL','VENCIDA','NEGOCIADA','CANCELADA','INADIMPLENTE');
CREATE TYPE status_negociacao   AS ENUM ('EM_NEGOCIACAO','APROVADA','REPROVADA','EFETIVADA');


-- -------------------------------------------------------------
-- TABELA: cobrancas
-- Uma cobrança por fatura — criada automaticamente na emissão
-- -------------------------------------------------------------
CREATE TABLE cobrancas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fatura_id           UUID NOT NULL REFERENCES faturas(id) ON DELETE RESTRICT,
    contrato_id         UUID NOT NULL REFERENCES contratos(id) ON DELETE RESTRICT,
    cliente_id          UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    numero_cobranca     VARCHAR(30) NOT NULL UNIQUE,    -- COB-2026-00001
    competencia         DATE NOT NULL,
    data_emissao        DATE NOT NULL DEFAULT CURRENT_DATE,
    data_vencimento     DATE NOT NULL,
    valor_original      NUMERIC(15,2) NOT NULL,
    valor_juros         NUMERIC(15,2) NOT NULL DEFAULT 0,
    valor_multa         NUMERIC(15,2) NOT NULL DEFAULT 0,
    valor_desconto      NUMERIC(15,2) NOT NULL DEFAULT 0,
    valor_recebido      NUMERIC(15,2) NOT NULL DEFAULT 0,
    valor_saldo         NUMERIC(15,2) GENERATED ALWAYS AS (
                            valor_original + valor_juros + valor_multa
                            - valor_desconto - valor_recebido
                        ) STORED,
    status              status_cobranca NOT NULL DEFAULT 'ABERTA',
    dias_atraso         INTEGER GENERATED ALWAYS AS (
                            CASE WHEN CURRENT_DATE > data_vencimento
                                 THEN (CURRENT_DATE - data_vencimento)
                                 ELSE 0 END
                        ) STORED,
    -- Referência ERP (número do boleto ou NF gerado externamente)
    numero_erp          VARCHAR(50),
    numero_nf           VARCHAR(30),
    observacoes         TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL,
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por      VARCHAR(100) NOT NULL
);

COMMENT ON TABLE  cobrancas              IS 'Cobrança gerada automaticamente a partir de cada fatura emitida.';
COMMENT ON COLUMN cobrancas.numero_erp   IS 'Número do boleto ou lançamento no ERP externo — para rastreabilidade.';
COMMENT ON COLUMN cobrancas.valor_saldo  IS 'Saldo devedor = original + juros + multa - desconto - recebido.';

CREATE UNIQUE INDEX uq_cobranca_fatura ON cobrancas (fatura_id);
CREATE INDEX idx_cobrancas_cliente_id   ON cobrancas (cliente_id);
CREATE INDEX idx_cobrancas_status       ON cobrancas (status);
CREATE INDEX idx_cobrancas_vencimento   ON cobrancas (data_vencimento);
CREATE INDEX idx_cobrancas_competencia  ON cobrancas (competencia);


-- -------------------------------------------------------------
-- TABELA: recebimentos
-- Cada baixa (parcial ou total) registrada na cobrança
-- -------------------------------------------------------------
CREATE TABLE recebimentos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cobranca_id         UUID NOT NULL REFERENCES cobrancas(id) ON DELETE CASCADE,
    data_recebimento    DATE NOT NULL,
    valor               NUMERIC(15,2) NOT NULL CHECK (valor > 0),
    forma               forma_recebimento NOT NULL,
    banco               VARCHAR(100),           -- banco onde foi recebido
    agencia             VARCHAR(20),
    conta               VARCHAR(30),
    identificador       VARCHAR(100),           -- código de transação, NSU, etc.
    observacoes         TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL
);

COMMENT ON TABLE recebimentos IS 'Baixas de pagamento de uma cobrança. Suporta pagamentos parciais.';
CREATE INDEX idx_recebimentos_cobranca ON recebimentos (cobranca_id);
CREATE INDEX idx_recebimentos_data     ON recebimentos (data_recebimento);


-- -------------------------------------------------------------
-- TABELA: negociacoes
-- Acordos de parcelamento ou desconto para inadimplentes
-- -------------------------------------------------------------
CREATE TABLE negociacoes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cobranca_id         UUID NOT NULL REFERENCES cobrancas(id) ON DELETE RESTRICT,
    status              status_negociacao NOT NULL DEFAULT 'EM_NEGOCIACAO',
    valor_original      NUMERIC(15,2) NOT NULL,
    valor_negociado     NUMERIC(15,2) NOT NULL,
    desconto_concedido  NUMERIC(15,2) GENERATED ALWAYS AS (valor_original - valor_negociado) STORED,
    motivo              TEXT NOT NULL,
    condicoes           TEXT,                   -- detalhes do acordo
    num_parcelas        INTEGER NOT NULL DEFAULT 1,
    data_negociacao     DATE NOT NULL DEFAULT CURRENT_DATE,
    data_aprovacao      DATE,
    aprovado_por        VARCHAR(100),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL
);

COMMENT ON TABLE negociacoes IS 'Acordos de renegociação para cobranças inadimplentes.';
CREATE INDEX idx_negociacoes_cobranca ON negociacoes (cobranca_id);


-- -------------------------------------------------------------
-- SEQUÊNCIA: número da cobrança
-- -------------------------------------------------------------
CREATE SEQUENCE seq_cobranca_numero START 1;

CREATE OR REPLACE FUNCTION fn_gera_numero_cobranca()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.numero_cobranca IS NULL OR NEW.numero_cobranca = '' THEN
        NEW.numero_cobranca := 'COB-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
                               LPAD(NEXTVAL('seq_cobranca_numero')::TEXT, 5, '0');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_numero_cobranca
    BEFORE INSERT ON cobrancas
    FOR EACH ROW EXECUTE FUNCTION fn_gera_numero_cobranca();


-- -------------------------------------------------------------
-- TRIGGER: atualiza status e valor_recebido após cada baixa
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_atualiza_cobranca_apos_recebimento()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_cobranca_id UUID;
    v_total_recebido NUMERIC(15,2);
    v_valor_original NUMERIC(15,2);
    v_novo_status status_cobranca;
BEGIN
    v_cobranca_id := COALESCE(NEW.cobranca_id, OLD.cobranca_id);

    SELECT COALESCE(SUM(r.valor), 0), c.valor_original + c.valor_juros + c.valor_multa - c.valor_desconto
    INTO v_total_recebido, v_valor_original
    FROM recebimentos r
    JOIN cobrancas c ON c.id = r.cobranca_id
    WHERE r.cobranca_id = v_cobranca_id
    GROUP BY c.valor_original, c.valor_juros, c.valor_multa, c.valor_desconto;

    IF v_total_recebido >= v_valor_original THEN
        v_novo_status := 'RECEBIDA';
    ELSIF v_total_recebido > 0 THEN
        v_novo_status := 'PARCIAL';
    ELSE
        v_novo_status := 'ABERTA';
    END IF;

    UPDATE cobrancas SET
        valor_recebido = v_total_recebido,
        status         = v_novo_status,
        atualizado_em  = NOW()
    WHERE id = v_cobranca_id;

    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_recebimento_atualiza_cobranca
    AFTER INSERT OR UPDATE OR DELETE ON recebimentos
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_cobranca_apos_recebimento();


-- -------------------------------------------------------------
-- TRIGGER: cria cobrança automaticamente ao emitir fatura
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_cria_cobranca_na_emissao()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Só cria se mudou para EMITIDA e ainda não tem cobrança
    IF NEW.status = 'EMITIDA' AND OLD.status != 'EMITIDA' THEN
        IF NOT EXISTS (SELECT 1 FROM cobrancas WHERE fatura_id = NEW.id) THEN
            INSERT INTO cobrancas (
                fatura_id, contrato_id, cliente_id,
                competencia, data_emissao, data_vencimento,
                valor_original, numero_nf,
                criado_por, atualizado_por
            )
            SELECT
                NEW.id,
                NEW.contrato_id,
                c.cliente_id,
                NEW.competencia,
                CURRENT_DATE,
                NEW.data_vencimento,
                NEW.valor_total,
                NEW.numero_nf,
                NEW.atualizado_por,
                NEW.atualizado_por
            FROM contratos c WHERE c.id = NEW.contrato_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_fatura_cria_cobranca
    AFTER UPDATE OF status ON faturas
    FOR EACH ROW EXECUTE FUNCTION fn_cria_cobranca_na_emissao();


-- -------------------------------------------------------------
-- VIEW: vw_aging — relatório de aging (vencimento em faixas)
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_aging AS
SELECT
    co.id,
    co.numero_cobranca,
    COALESCE(cl.razao_social, cl.nome_completo) AS cliente_nome,
    c.numero    AS contrato_numero,
    c.modalidade,
    co.competencia,
    co.data_vencimento,
    co.valor_original,
    co.valor_recebido,
    co.valor_saldo,
    co.dias_atraso,
    co.status,
    CASE
        WHEN co.status = 'RECEBIDA'      THEN 'RECEBIDA'
        WHEN co.dias_atraso = 0          THEN 'A_VENCER'
        WHEN co.dias_atraso BETWEEN 1  AND 30  THEN '1_A_30'
        WHEN co.dias_atraso BETWEEN 31 AND 60  THEN '31_A_60'
        WHEN co.dias_atraso BETWEEN 61 AND 90  THEN '61_A_90'
        ELSE 'ACIMA_90'
    END AS faixa_aging
FROM cobrancas co
JOIN contratos c  ON c.id  = co.contrato_id
JOIN clientes  cl ON cl.id = co.cliente_id
WHERE co.status NOT IN ('CANCELADA');

COMMENT ON VIEW vw_aging IS 'Aging de cobranças por faixa de vencimento para análise de inadimplência.';


-- -------------------------------------------------------------
-- VIEW: vw_contas_receber_resumo — painel principal
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_contas_receber_resumo AS
SELECT
    status,
    COUNT(*)            AS quantidade,
    SUM(valor_original) AS total_original,
    SUM(valor_recebido) AS total_recebido,
    SUM(valor_saldo)    AS total_saldo
FROM cobrancas
WHERE status != 'CANCELADA'
GROUP BY status;
