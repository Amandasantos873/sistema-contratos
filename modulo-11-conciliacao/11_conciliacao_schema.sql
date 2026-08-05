-- =============================================================
-- SISTEMA DE GESTÃO — Módulo 11: Conciliação Bancária
-- Uma conta bancária, lançamento manual, sugestão automática
-- =============================================================

CREATE TYPE tipo_lancamento_banco  AS ENUM ('CREDITO','DEBITO');
CREATE TYPE status_conciliacao     AS ENUM ('PENDENTE','CONCILIADO','IGNORADO','DIVERGENTE');
CREATE TYPE origem_lancamento      AS ENUM ('RECEBIMENTO','DESPESA','TRANSFERENCIA','OUTROS');


-- -------------------------------------------------------------
-- TABELA: contas_bancarias
-- Uma conta por enquanto — estrutura preparada para crescer
-- -------------------------------------------------------------
CREATE TABLE contas_bancarias (
    id          SERIAL PRIMARY KEY,
    banco       VARCHAR(100) NOT NULL,
    agencia     VARCHAR(20)  NOT NULL,
    conta       VARCHAR(30)  NOT NULL,
    descricao   VARCHAR(150),
    saldo_atual NUMERIC(15,2) NOT NULL DEFAULT 0,
    ativa       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por  VARCHAR(100)
);

-- Conta padrão — atualizar com os dados reais
INSERT INTO contas_bancarias (banco, agencia, conta, descricao, criado_por)
VALUES ('A definir', '0000', '00000-0', 'Conta principal', 'setup');


-- -------------------------------------------------------------
-- TABELA: extratos_bancarios
-- Cada linha do extrato digitada manualmente
-- -------------------------------------------------------------
CREATE TABLE extratos_bancarios (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conta_id            INTEGER NOT NULL REFERENCES contas_bancarias(id),
    data_lancamento     DATE NOT NULL,
    data_compensacao    DATE,
    tipo                tipo_lancamento_banco NOT NULL,
    valor               NUMERIC(15,2) NOT NULL CHECK (valor > 0),
    descricao           VARCHAR(300) NOT NULL,
    documento           VARCHAR(100),       -- número do documento no banco
    saldo_apos          NUMERIC(15,2),      -- saldo após o lançamento
    status_conciliacao  status_conciliacao NOT NULL DEFAULT 'PENDENTE',
    -- Vínculo com lançamento do sistema (após conciliação)
    origem              origem_lancamento,
    origem_id           UUID,               -- ID do recebimento ou despesa
    origem_numero       VARCHAR(50),        -- número amigável para exibição
    conciliado_em       TIMESTAMPTZ,
    conciliado_por      VARCHAR(100),
    observacoes         TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL,
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_extrato_conta_id     ON extratos_bancarios (conta_id);
CREATE INDEX idx_extrato_data         ON extratos_bancarios (data_lancamento);
CREATE INDEX idx_extrato_status       ON extratos_bancarios (status_conciliacao);
CREATE INDEX idx_extrato_tipo         ON extratos_bancarios (tipo);


-- -------------------------------------------------------------
-- FUNÇÃO: sugestões automáticas de conciliação
-- Busca lançamentos do sistema com valor ± tolerância e data ± dias
-- Retorna candidatos ordenados por proximidade
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_sugestoes_conciliacao(
    p_extrato_id        UUID,
    p_tolerancia_valor  NUMERIC  DEFAULT 0.10,   -- 10 centavos de tolerância
    p_tolerancia_dias   INTEGER  DEFAULT 3        -- 3 dias de tolerância
)
RETURNS TABLE (
    origem              TEXT,
    origem_id           UUID,
    origem_numero       TEXT,
    descricao           TEXT,
    valor               NUMERIC,
    data_ref            DATE,
    score               INTEGER   -- quanto menor, melhor o match
) LANGUAGE plpgsql AS $$
DECLARE
    v_valor     NUMERIC;
    v_data      DATE;
    v_tipo      tipo_lancamento_banco;
BEGIN
    SELECT e.valor, e.data_lancamento, e.tipo
    INTO v_valor, v_data, v_tipo
    FROM extratos_bancarios e WHERE e.id = p_extrato_id;

    -- CRÉDITO → busca em recebimentos
    IF v_tipo = 'CREDITO' THEN
        RETURN QUERY
        SELECT
            'RECEBIMENTO'::TEXT,
            r.id,
            co.numero_cobranca::TEXT,
            COALESCE(cl.razao_social, cl.nome_completo)::TEXT,
            r.valor,
            r.data_recebimento,
            ABS(r.valor - v_valor)::INTEGER * 100
                + ABS(r.data_recebimento - v_data) AS score
        FROM recebimentos r
        JOIN cobrancas co ON co.id = r.cobranca_id
        JOIN contratos ct ON ct.id = co.contrato_id
        JOIN clientes cl  ON cl.id = co.cliente_id
        WHERE ABS(r.valor - v_valor) <= p_tolerancia_valor
          AND ABS(r.data_recebimento - v_data) <= p_tolerancia_dias
          -- Não já conciliado
          AND NOT EXISTS (
            SELECT 1 FROM extratos_bancarios e2
            WHERE e2.origem_id = r.id AND e2.status_conciliacao = 'CONCILIADO'
          )
        ORDER BY score
        LIMIT 5;

    -- DÉBITO → busca em despesas pagas
    ELSE
        RETURN QUERY
        SELECT
            'DESPESA'::TEXT,
            d.id,
            d.numero_despesa::TEXT,
            d.descricao::TEXT,
            COALESCE(d.valor_pago, d.valor),
            d.data_pagamento,
            ABS(COALESCE(d.valor_pago, d.valor) - v_valor)::INTEGER * 100
                + ABS(d.data_pagamento - v_data) AS score
        FROM despesas d
        WHERE d.status IN ('PAGA','CONCILIADA')
          AND d.data_pagamento IS NOT NULL
          AND ABS(COALESCE(d.valor_pago, d.valor) - v_valor) <= p_tolerancia_valor
          AND ABS(d.data_pagamento - v_data) <= p_tolerancia_dias
          AND NOT EXISTS (
            SELECT 1 FROM extratos_bancarios e2
            WHERE e2.origem_id = d.id AND e2.status_conciliacao = 'CONCILIADO'
          )
        ORDER BY score
        LIMIT 5;
    END IF;
END;
$$;


-- -------------------------------------------------------------
-- TRIGGER: atualiza saldo da conta após cada lançamento
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_atualiza_saldo_conta()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE contas_bancarias SET
        saldo_atual = (
            SELECT COALESCE(SUM(CASE WHEN tipo='CREDITO' THEN valor ELSE -valor END), 0)
            FROM extratos_bancarios
            WHERE conta_id = COALESCE(NEW.conta_id, OLD.conta_id)
              AND status_conciliacao != 'IGNORADO'
        )
    WHERE id = COALESCE(NEW.conta_id, OLD.conta_id);
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_saldo_extrato
    AFTER INSERT OR UPDATE OR DELETE ON extratos_bancarios
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_saldo_conta();


-- -------------------------------------------------------------
-- VIEW: vw_conciliacao_pendente
-- Lançamentos do extrato ainda não conciliados com sugestão do sistema
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_conciliacao_resumo AS
SELECT
    e.id,
    e.data_lancamento,
    e.tipo,
    e.valor,
    e.descricao,
    e.documento,
    e.status_conciliacao,
    e.origem,
    e.origem_numero,
    e.conciliado_em,
    e.conciliado_por,
    cb.banco,
    cb.conta
FROM extratos_bancarios e
JOIN contas_bancarias cb ON cb.id = e.conta_id
ORDER BY e.data_lancamento DESC, e.tipo;


-- -------------------------------------------------------------
-- VIEW: vw_posicao_bancaria
-- Resumo da conta: saldo, pendentes, conciliados
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_posicao_bancaria AS
SELECT
    cb.id,
    cb.banco,
    cb.agencia,
    cb.conta,
    cb.descricao,
    cb.saldo_atual,
    COUNT(e.id)                                                         AS total_lancamentos,
    COUNT(CASE WHEN e.status_conciliacao = 'PENDENTE'    THEN 1 END)   AS pendentes,
    COUNT(CASE WHEN e.status_conciliacao = 'CONCILIADO'  THEN 1 END)   AS conciliados,
    COUNT(CASE WHEN e.status_conciliacao = 'DIVERGENTE'  THEN 1 END)   AS divergentes,
    SUM(CASE WHEN e.tipo='CREDITO' AND e.status_conciliacao='PENDENTE' THEN e.valor ELSE 0 END) AS creditos_pendentes,
    SUM(CASE WHEN e.tipo='DEBITO'  AND e.status_conciliacao='PENDENTE' THEN e.valor ELSE 0 END) AS debitos_pendentes
FROM contas_bancarias cb
LEFT JOIN extratos_bancarios e ON e.conta_id = cb.id
WHERE cb.ativa = TRUE
GROUP BY cb.id, cb.banco, cb.agencia, cb.conta, cb.descricao, cb.saldo_atual;
