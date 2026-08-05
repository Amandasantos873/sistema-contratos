-- =============================================================
-- SISTEMA DE GESTÃO — Módulo 09: Fluxo de Caixa
-- Alimentado automaticamente pelos módulos 07 e 08
-- Não requer lançamentos manuais
-- =============================================================


-- -------------------------------------------------------------
-- VIEW: vw_entradas_projetadas
-- Cobranças em aberto — o que está previsto para entrar
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_entradas_projetadas AS
SELECT
    co.data_vencimento                              AS data_prevista,
    DATE_TRUNC('month', co.data_vencimento)         AS mes,
    co.id                                           AS origem_id,
    'COBRANCA'                                      AS origem_tipo,
    co.numero_cobranca                              AS origem_numero,
    COALESCE(cl.razao_social, cl.nome_completo)     AS descricao,
    c.modalidade::TEXT                              AS categoria,
    'RECEITA_SERVICOS'                              AS tipo_fluxo,
    co.valor_saldo                                  AS valor_projetado,
    0::NUMERIC                                      AS valor_realizado
FROM cobrancas co
JOIN contratos c  ON c.id  = co.contrato_id
JOIN clientes  cl ON cl.id = co.cliente_id
WHERE co.status NOT IN ('RECEBIDA','CANCELADA')
  AND co.valor_saldo > 0;


-- -------------------------------------------------------------
-- VIEW: vw_entradas_realizadas
-- Recebimentos confirmados — o que de fato entrou
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_entradas_realizadas AS
SELECT
    r.data_recebimento                              AS data_realizada,
    DATE_TRUNC('month', r.data_recebimento)         AS mes,
    r.id                                            AS origem_id,
    'RECEBIMENTO'                                   AS origem_tipo,
    co.numero_cobranca                              AS origem_numero,
    COALESCE(cl.razao_social, cl.nome_completo)     AS descricao,
    c.modalidade::TEXT                              AS categoria,
    'RECEITA_SERVICOS'                              AS tipo_fluxo,
    0::NUMERIC                                      AS valor_projetado,
    r.valor                                         AS valor_realizado
FROM recebimentos r
JOIN cobrancas co ON co.id = r.cobranca_id
JOIN contratos c  ON c.id  = co.contrato_id
JOIN clientes  cl ON cl.id = co.cliente_id;


-- -------------------------------------------------------------
-- VIEW: vw_saidas_projetadas
-- Despesas aprovadas não pagas — o que está previsto para sair
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_saidas_projetadas AS
SELECT
    d.data_vencimento                               AS data_prevista,
    DATE_TRUNC('month', d.data_vencimento)          AS mes,
    d.id                                            AS origem_id,
    'DESPESA'                                       AS origem_tipo,
    d.numero_despesa                                AS origem_numero,
    d.descricao,
    cd.tipo::TEXT                                   AS categoria,
    'DESPESA_OPERACIONAL'                           AS tipo_fluxo,
    d.valor                                         AS valor_projetado,
    0::NUMERIC                                      AS valor_realizado
FROM despesas d
JOIN categorias_despesa cd ON cd.id = d.categoria_id
WHERE d.status IN ('APROVADA','AGUARDANDO_APROVACAO','LANCADA')
  AND d.data_vencimento >= CURRENT_DATE;


-- -------------------------------------------------------------
-- VIEW: vw_saidas_realizadas
-- Despesas pagas — o que de fato saiu
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_saidas_realizadas AS
SELECT
    d.data_pagamento                                AS data_realizada,
    DATE_TRUNC('month', d.data_pagamento)           AS mes,
    d.id                                            AS origem_id,
    'DESPESA_PAGA'                                  AS origem_tipo,
    d.numero_despesa                                AS origem_numero,
    d.descricao,
    cd.tipo::TEXT                                   AS categoria,
    'DESPESA_OPERACIONAL'                           AS tipo_fluxo,
    0::NUMERIC                                      AS valor_projetado,
    COALESCE(d.valor_pago, d.valor)                 AS valor_realizado
FROM despesas d
JOIN categorias_despesa cd ON cd.id = d.categoria_id
WHERE d.status IN ('PAGA','CONCILIADA')
  AND d.data_pagamento IS NOT NULL;


-- -------------------------------------------------------------
-- VIEW: vw_fluxo_caixa_mensal
-- Consolidado mensal projetado x realizado
-- Base do painel principal
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_fluxo_caixa_mensal AS
WITH entradas AS (
    -- Realizadas
    SELECT mes, SUM(valor_realizado) AS realizado, 0::NUMERIC AS projetado
    FROM vw_entradas_realizadas GROUP BY mes
    UNION ALL
    -- Projetadas
    SELECT mes, 0::NUMERIC AS realizado, SUM(valor_projetado) AS projetado
    FROM vw_entradas_projetadas GROUP BY mes
),
saidas AS (
    -- Realizadas
    SELECT mes, SUM(valor_realizado) AS realizado, 0::NUMERIC AS projetado
    FROM vw_saidas_realizadas GROUP BY mes
    UNION ALL
    -- Projetadas
    SELECT mes, 0::NUMERIC AS realizado, SUM(valor_projetado) AS projetado
    FROM vw_saidas_projetadas GROUP BY mes
)
SELECT
    COALESCE(e.mes, s.mes)              AS mes,
    COALESCE(SUM(e.realizado),  0)      AS entradas_realizadas,
    COALESCE(SUM(e.projetado),  0)      AS entradas_projetadas,
    COALESCE(SUM(s.realizado),  0)      AS saidas_realizadas,
    COALESCE(SUM(s.projetado),  0)      AS saidas_projetadas,
    -- Saldos
    COALESCE(SUM(e.realizado),0) - COALESCE(SUM(s.realizado),0)   AS saldo_realizado,
    COALESCE(SUM(e.projetado),0) - COALESCE(SUM(s.projetado),0)   AS saldo_projetado,
    -- Desvio: realizado vs projetado de entradas
    COALESCE(SUM(e.realizado),0) - COALESCE(SUM(e.projetado),0)   AS desvio_entradas,
    -- Desvio: realizado vs projetado de saídas
    COALESCE(SUM(s.realizado),0) - COALESCE(SUM(s.projetado),0)   AS desvio_saidas
FROM entradas e
FULL OUTER JOIN saidas s ON e.mes = s.mes
GROUP BY COALESCE(e.mes, s.mes)
ORDER BY mes;


-- -------------------------------------------------------------
-- VIEW: vw_fluxo_caixa_diario
-- Drill-down diário — ativado ao clicar em um mês
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_fluxo_caixa_diario AS
-- Entradas realizadas
SELECT
    data_realizada                      AS data,
    'ENTRADA'                           AS sentido,
    'REALIZADO'                         AS natureza,
    descricao,
    categoria,
    origem_tipo,
    origem_numero,
    valor_realizado                     AS valor
FROM vw_entradas_realizadas
WHERE data_realizada IS NOT NULL

UNION ALL

-- Entradas projetadas
SELECT
    data_prevista                       AS data,
    'ENTRADA'                           AS sentido,
    'PROJETADO'                         AS natureza,
    descricao,
    categoria,
    origem_tipo,
    origem_numero,
    valor_projetado                     AS valor
FROM vw_entradas_projetadas

UNION ALL

-- Saídas realizadas
SELECT
    data_realizada                      AS data,
    'SAIDA'                             AS sentido,
    'REALIZADO'                         AS natureza,
    descricao,
    categoria,
    origem_tipo,
    origem_numero,
    valor_realizado                     AS valor
FROM vw_saidas_realizadas
WHERE data_realizada IS NOT NULL

UNION ALL

-- Saídas projetadas
SELECT
    data_prevista                       AS data,
    'SAIDA'                             AS sentido,
    'PROJETADO'                         AS natureza,
    descricao,
    categoria,
    origem_tipo,
    origem_numero,
    valor_projetado                     AS valor
FROM vw_saidas_projetadas

ORDER BY data, sentido;


-- -------------------------------------------------------------
-- VIEW: vw_saldo_acumulado
-- Saldo acumulado mês a mês para o gráfico de linha
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_saldo_acumulado AS
SELECT
    mes,
    saldo_realizado,
    saldo_projetado,
    SUM(saldo_realizado) OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING) AS saldo_acumulado_realizado,
    SUM(saldo_projetado) OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING) AS saldo_acumulado_projetado
FROM vw_fluxo_caixa_mensal
ORDER BY mes;
