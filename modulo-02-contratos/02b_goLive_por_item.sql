-- =============================================================
-- CORREÇÃO MÓDULO 02 — Go-live por item
-- Aplica após os scripts dos módulos 01 a 04
-- =============================================================

-- -------------------------------------------------------------
-- ENUM: status do item dentro do contrato
-- -------------------------------------------------------------
CREATE TYPE status_contrato_item AS ENUM (
    'IMPLANTACAO',   -- ainda não foi ao ar
    'ATIVO',         -- em produção, sendo faturado
    'SUSPENSO',      -- temporariamente sem faturamento
    'CANCELADO'      -- encerrado definitivamente
);


-- -------------------------------------------------------------
-- ALTERAÇÃO: contratos_itens
-- Adiciona controle de go-live e status por item
-- -------------------------------------------------------------
ALTER TABLE contratos_itens
    ADD COLUMN IF NOT EXISTS status_item          status_contrato_item NOT NULL DEFAULT 'IMPLANTACAO',
    ADD COLUMN IF NOT EXISTS data_goLive_item     DATE,
    ADD COLUMN IF NOT EXISTS data_inicio_faturamento DATE,   -- = data_goLive_item quando confirmado
    ADD COLUMN IF NOT EXISTS goLive_confirmado_por VARCHAR(100),
    ADD COLUMN IF NOT EXISTS goLive_confirmado_em  TIMESTAMPTZ;

COMMENT ON COLUMN contratos_itens.status_item          IS 'Ciclo de vida do item: IMPLANTACAO → ATIVO → SUSPENSO/CANCELADO';
COMMENT ON COLUMN contratos_itens.data_goLive_item     IS 'Data em que este item específico entrou em produção';
COMMENT ON COLUMN contratos_itens.data_inicio_faturamento IS 'Data a partir da qual este item é incluído no faturamento mensal. Igual ao data_goLive_item.';


-- -------------------------------------------------------------
-- FUNÇÃO: registra go-live de um item individualmente
-- Atualiza status_item e data_inicio_faturamento
-- Se todos os itens do contrato tiverem go-live, atualiza
-- também o go-live do contrato (caso ainda não esteja preenchido)
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_registra_goLive_item()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_total_itens_recorr  INTEGER;
    v_itens_com_goLive    INTEGER;
BEGIN
    -- Só executa quando data_goLive_item é preenchida pela primeira vez
    IF NEW.data_goLive_item IS NOT NULL AND OLD.data_goLive_item IS NULL THEN
        NEW.status_item               := 'ATIVO';
        NEW.data_inicio_faturamento   := NEW.data_goLive_item;
        NEW.goLive_confirmado_em      := NOW();

        -- Verifica se todos os itens recorrentes do contrato já têm go-live
        SELECT
            COUNT(*) FILTER (WHERE fase = 'RECORRENCIA' AND ativo = TRUE),
            COUNT(*) FILTER (WHERE fase = 'RECORRENCIA' AND ativo = TRUE AND data_goLive_item IS NOT NULL)
        INTO v_total_itens_recorr, v_itens_com_goLive
        FROM contratos_itens
        WHERE contrato_id = NEW.contrato_id
          AND id != NEW.id;   -- exclui o item atual (ainda não persistido)

        -- +1 pelo item atual
        v_itens_com_goLive := v_itens_com_goLive + 1;

        -- Se todos os itens recorrentes têm go-live E o contrato ainda não tem,
        -- preenche o go-live do contrato com a menor data entre os itens
        IF v_itens_com_goLive >= v_total_itens_recorr THEN
            UPDATE contratos
            SET data_goLive = (
                    SELECT MIN(ci.data_goLive_item)
                    FROM contratos_itens ci
                    WHERE ci.contrato_id = NEW.contrato_id
                      AND ci.fase = 'RECORRENCIA'
                      AND ci.ativo = TRUE
                      AND (ci.id = NEW.id OR ci.data_goLive_item IS NOT NULL)
                ),
                atualizado_em = NOW()
            WHERE id = NEW.contrato_id
              AND data_goLive IS NULL;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_goLive_item
    BEFORE UPDATE ON contratos_itens
    FOR EACH ROW EXECUTE FUNCTION fn_registra_goLive_item();


-- -------------------------------------------------------------
-- ÍNDICES adicionais
-- -------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_itens_status_item     ON contratos_itens (status_item);
CREATE INDEX IF NOT EXISTS idx_itens_data_fat        ON contratos_itens (data_inicio_faturamento);
CREATE INDEX IF NOT EXISTS idx_itens_contrato_status ON contratos_itens (contrato_id, status_item);


-- -------------------------------------------------------------
-- ATUALIZAÇÃO DA VIEW vw_contratos_a_faturar
-- Agora considera o go-live por item, não só o do contrato
-- O módulo de faturamento usa esta view para saber
-- quais itens entram em cada apuração
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_itens_a_faturar AS
SELECT
    ci.id                                               AS item_id,
    ci.contrato_id,
    c.numero                                            AS contrato_numero,
    c.cliente_id,
    COALESCE(cl.razao_social, cl.nome_completo)         AS cliente_nome,
    c.modalidade,
    c.dia_faturamento,
    ci.produto_id,
    ps.nome                                             AS produto_nome,
    ps.unidade                                          AS produto_unidade,
    ci.quantidade,
    ci.valor_unitario,
    ci.desconto_pct,
    ci.valor_total,
    ci.data_inicio_faturamento,
    ci.status_item
FROM contratos_itens ci
JOIN contratos c        ON c.id  = ci.contrato_id
JOIN clientes cl        ON cl.id = c.cliente_id
JOIN produtos_servicos ps ON ps.id = ci.produto_id
WHERE ci.fase        = 'RECORRENCIA'
  AND ci.ativo       = TRUE
  AND ci.status_item = 'ATIVO'
  AND c.status       = 'ATIVO'
  AND (c.data_fim_contrato IS NULL OR c.data_fim_contrato >= CURRENT_DATE);

COMMENT ON VIEW vw_itens_a_faturar IS
    'Itens elegíveis para faturamento: somente fase RECORRENCIA, status ATIVO no item, '
    'contrato ATIVO e dentro da vigência. Filtrar por dia_faturamento e data_inicio_faturamento no serviço.';


-- -------------------------------------------------------------
-- ATUALIZAÇÃO DA VIEW vw_contratos_a_faturar (módulo 02)
-- Mantida para compatibilidade — agora usa vw_itens_a_faturar
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_contratos_a_faturar AS
SELECT DISTINCT
    c.id                AS contrato_id,
    c.numero,
    c.cliente_id,
    COALESCE(cl.razao_social, cl.nome_completo) AS cliente_nome,
    c.modalidade,
    c.dia_faturamento,
    -- Valor mensal considera apenas itens ATIVOS (go-live confirmado)
    COALESCE((
        SELECT SUM(ci2.valor_total)
        FROM contratos_itens ci2
        WHERE ci2.contrato_id = c.id
          AND ci2.fase        = 'RECORRENCIA'
          AND ci2.ativo       = TRUE
          AND ci2.status_item = 'ATIVO'
    ), 0)               AS valor_mensal_ativo,
    c.valor_mensal      AS valor_mensal_contrato,
    c.data_fim_contrato
FROM contratos c
JOIN clientes cl ON cl.id = c.cliente_id
WHERE c.status     = 'ATIVO'
  AND c.fase_atual = 'RECORRENCIA'
  AND (c.data_fim_contrato IS NULL OR c.data_fim_contrato >= CURRENT_DATE)
  AND EXISTS (
      SELECT 1 FROM contratos_itens ci
      WHERE ci.contrato_id = c.id
        AND ci.fase        = 'RECORRENCIA'
        AND ci.ativo       = TRUE
        AND ci.status_item = 'ATIVO'
  );


-- -------------------------------------------------------------
-- VIEW: vw_itens_aguardando_goLive
-- Itens ainda em implantação — para o painel de acompanhamento
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_itens_aguardando_goLive AS
SELECT
    ci.id                                               AS item_id,
    ci.contrato_id,
    c.numero                                            AS contrato_numero,
    COALESCE(cl.razao_social, cl.nome_completo)         AS cliente_nome,
    c.modalidade,
    ps.nome                                             AS produto_nome,
    ci.valor_total,
    c.data_inicio_impl,
    c.data_goLive                                       AS goLive_contrato,
    ci.data_goLive_item,
    ci.status_item,
    -- Dias desde o início da implantação
    (CURRENT_DATE - c.data_inicio_impl)                 AS dias_em_implantacao
FROM contratos_itens ci
JOIN contratos c          ON c.id  = ci.contrato_id
JOIN clientes cl          ON cl.id = c.cliente_id
JOIN produtos_servicos ps ON ps.id = ci.produto_id
WHERE ci.fase        = 'RECORRENCIA'
  AND ci.ativo       = TRUE
  AND ci.status_item = 'IMPLANTACAO'
  AND c.status       = 'ATIVO'
ORDER BY dias_em_implantacao DESC;

COMMENT ON VIEW vw_itens_aguardando_goLive IS
    'Itens recorrentes ainda em implantação, aguardando confirmação de go-live individual.';
