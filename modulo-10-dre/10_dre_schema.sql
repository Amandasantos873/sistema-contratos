-- =============================================================
-- SISTEMA DE GESTÃO — Módulo 10: DRE Gerencial
-- Alimentado pelos módulos 07 (receitas) e 08 (despesas)
-- Estrutura: Receita Bruta → Líquida → Lucro Bruto → EBITDA → Resultado
-- =============================================================


-- -------------------------------------------------------------
-- VIEW: vw_dre_receitas_mensais
-- Receitas realizadas por modalidade e mês
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dre_receitas_mensais AS
SELECT
    DATE_TRUNC('month', r.data_recebimento)         AS mes,
    c.modalidade::TEXT                              AS modalidade,
    COUNT(DISTINCT co.id)                           AS qtd_faturas,
    SUM(r.valor)                                    AS receita_bruta
FROM recebimentos r
JOIN cobrancas co ON co.id = r.cobranca_id
JOIN contratos c  ON c.id  = co.contrato_id
GROUP BY 1, 2;


-- -------------------------------------------------------------
-- VIEW: vw_dre_despesas_mensais
-- Despesas pagas por categoria e mês
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dre_despesas_mensais AS
SELECT
    DATE_TRUNC('month', d.data_pagamento)           AS mes,
    cd.tipo::TEXT                                   AS tipo,
    cd.nome                                         AS categoria,
    cc.nome                                         AS centro_custo,
    SUM(COALESCE(d.valor_pago, d.valor))            AS valor_pago
FROM despesas d
JOIN categorias_despesa cd ON cd.id = d.categoria_id
JOIN centros_custo      cc ON cc.id = d.centro_custo_id
WHERE d.status IN ('PAGA','CONCILIADA')
  AND d.data_pagamento IS NOT NULL
GROUP BY 1, 2, 3, 4;


-- -------------------------------------------------------------
-- VIEW: vw_dre_mensal
-- DRE gerencial consolidado por mês
-- Estrutura completa com todas as linhas
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dre_mensal AS
WITH
-- Receita bruta por modalidade
receitas AS (
    SELECT
        mes,
        SUM(CASE WHEN modalidade = 'ASP' THEN receita_bruta ELSE 0 END) AS rec_asp,
        SUM(CASE WHEN modalidade = 'BSP' THEN receita_bruta ELSE 0 END) AS rec_bsp,
        SUM(CASE WHEN modalidade = 'BPO' THEN receita_bruta ELSE 0 END) AS rec_bpo,
        SUM(receita_bruta)                                               AS receita_bruta_total
    FROM vw_dre_receitas_mensais
    GROUP BY mes
),
-- Despesas por grupo
despesas AS (
    SELECT
        mes,
        -- Impostos sobre serviços
        SUM(CASE WHEN tipo = 'IMPOSTO' THEN valor_pago ELSE 0 END)          AS impostos_servicos,
        -- Custos operacionais diretos
        SUM(CASE WHEN tipo = 'FOLHA'   THEN valor_pago ELSE 0 END)          AS folha_pagamento,
        SUM(CASE WHEN tipo = 'BENEFICIO' THEN valor_pago ELSE 0 END)        AS beneficios,
        SUM(CASE WHEN tipo = 'FORNECEDOR' THEN valor_pago ELSE 0 END)       AS fornecedores,
        -- Despesas operacionais
        SUM(CASE WHEN tipo = 'ADMINISTRATIVA' THEN valor_pago ELSE 0 END)   AS despesas_admin,
        SUM(CASE WHEN tipo = 'COMISSAO' THEN valor_pago ELSE 0 END)         AS comissoes,
        SUM(CASE WHEN tipo = 'OUTROS'   THEN valor_pago ELSE 0 END)         AS outros,
        SUM(valor_pago)                                                      AS total_despesas
    FROM vw_dre_despesas_mensais
    GROUP BY mes
)
SELECT
    COALESCE(r.mes, d.mes)              AS mes,

    -- RECEITA BRUTA
    COALESCE(r.rec_asp, 0)              AS receita_asp,
    COALESCE(r.rec_bsp, 0)             AS receita_bsp,
    COALESCE(r.rec_bpo, 0)             AS receita_bpo,
    COALESCE(r.receita_bruta_total, 0) AS receita_bruta,

    -- DEDUÇÕES
    COALESCE(d.impostos_servicos, 0)   AS deducoes_impostos,

    -- RECEITA LÍQUIDA
    COALESCE(r.receita_bruta_total, 0)
        - COALESCE(d.impostos_servicos, 0)                  AS receita_liquida,

    -- CUSTOS OPERACIONAIS
    COALESCE(d.folha_pagamento, 0)     AS custo_folha,
    COALESCE(d.beneficios, 0)          AS custo_beneficios,
    COALESCE(d.fornecedores, 0)        AS custo_fornecedores,
    COALESCE(d.folha_pagamento, 0)
        + COALESCE(d.beneficios, 0)
        + COALESCE(d.fornecedores, 0)  AS total_custos,

    -- LUCRO BRUTO
    COALESCE(r.receita_bruta_total, 0)
        - COALESCE(d.impostos_servicos, 0)
        - COALESCE(d.folha_pagamento, 0)
        - COALESCE(d.beneficios, 0)
        - COALESCE(d.fornecedores, 0)                       AS lucro_bruto,

    -- DESPESAS OPERACIONAIS
    COALESCE(d.despesas_admin, 0)      AS desp_administrativa,
    COALESCE(d.comissoes, 0)           AS desp_comissoes,
    COALESCE(d.outros, 0)              AS desp_outros,
    COALESCE(d.despesas_admin, 0)
        + COALESCE(d.comissoes, 0)
        + COALESCE(d.outros, 0)        AS total_desp_operacionais,

    -- EBITDA
    COALESCE(r.receita_bruta_total, 0)
        - COALESCE(d.total_despesas, 0)                     AS ebitda,

    -- MARGEM EBITDA %
    CASE WHEN COALESCE(r.receita_bruta_total, 0) > 0
         THEN ROUND(
            (COALESCE(r.receita_bruta_total, 0) - COALESCE(d.total_despesas, 0))
            / COALESCE(r.receita_bruta_total, 0) * 100, 2
         )
         ELSE 0
    END                                AS margem_ebitda_pct,

    -- TOTAL DESPESAS
    COALESCE(d.total_despesas, 0)      AS total_despesas,

    -- RESULTADO LÍQUIDO (EBITDA — sem IRPJ/CSLL separado por ora)
    COALESCE(r.receita_bruta_total, 0)
        - COALESCE(d.total_despesas, 0)                     AS resultado_liquido,

    -- MARGEM LÍQUIDA %
    CASE WHEN COALESCE(r.receita_bruta_total, 0) > 0
         THEN ROUND(
            (COALESCE(r.receita_bruta_total, 0) - COALESCE(d.total_despesas, 0))
            / COALESCE(r.receita_bruta_total, 0) * 100, 2
         )
         ELSE 0
    END                                AS margem_liquida_pct

FROM receitas r
FULL OUTER JOIN despesas d ON r.mes = d.mes
ORDER BY mes;


-- -------------------------------------------------------------
-- VIEW: vw_dre_acumulado_ano
-- Acumulado de janeiro até o mês informado
-- Usado na coluna "Acumulado" do DRE completo
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dre_acumulado_ano AS
SELECT
    EXTRACT(YEAR FROM mes)::INTEGER     AS ano,
    SUM(receita_bruta)                  AS receita_bruta,
    SUM(deducoes_impostos)              AS deducoes_impostos,
    SUM(receita_liquida)                AS receita_liquida,
    SUM(total_custos)                   AS total_custos,
    SUM(lucro_bruto)                    AS lucro_bruto,
    SUM(total_desp_operacionais)        AS total_desp_operacionais,
    SUM(ebitda)                         AS ebitda,
    CASE WHEN SUM(receita_bruta) > 0
         THEN ROUND(SUM(ebitda) / SUM(receita_bruta) * 100, 2)
         ELSE 0
    END                                 AS margem_ebitda_pct,
    SUM(resultado_liquido)              AS resultado_liquido,
    CASE WHEN SUM(receita_bruta) > 0
         THEN ROUND(SUM(resultado_liquido) / SUM(receita_bruta) * 100, 2)
         ELSE 0
    END                                 AS margem_liquida_pct
FROM vw_dre_mensal
GROUP BY 1
ORDER BY 1;


-- -------------------------------------------------------------
-- VIEW: vw_dre_dashboard
-- Versão simplificada para o dashboard — últimos 6 meses
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dre_dashboard AS
SELECT
    mes,
    receita_bruta,
    total_despesas,
    ebitda,
    margem_ebitda_pct,
    resultado_liquido,
    margem_liquida_pct
FROM vw_dre_mensal
WHERE mes >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months'
ORDER BY mes;
