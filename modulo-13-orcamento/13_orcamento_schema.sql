-- =============================================================
-- SISTEMA DE GESTÃO — Módulo 13: Orçamento x Realizado
-- Meta anual distribuída em 12 meses
-- Realizado vem automaticamente dos módulos 07 e 08
-- =============================================================


-- -------------------------------------------------------------
-- TABELA: orcamentos
-- Cabeçalho do orçamento anual
-- -------------------------------------------------------------
CREATE TABLE orcamentos (
    id              SERIAL PRIMARY KEY,
    ano             INTEGER NOT NULL UNIQUE,
    descricao       VARCHAR(200),
    status          VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO'
                    CHECK (status IN ('RASCUNHO','ATIVO','ENCERRADO')),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100) NOT NULL,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por  VARCHAR(100) NOT NULL
);

COMMENT ON TABLE orcamentos IS 'Cabeçalho do orçamento anual. Um por ano.';


-- -------------------------------------------------------------
-- TABELA: orcamento_receitas
-- Meta de receita por modalidade e mês
-- -------------------------------------------------------------
CREATE TABLE orcamento_receitas (
    id              SERIAL PRIMARY KEY,
    orcamento_id    INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    modalidade      VARCHAR(10) NOT NULL CHECK (modalidade IN ('ASP','BSP','BPO','TOTAL')),
    mes             DATE NOT NULL,          -- sempre 1º dia do mês
    valor_orcado    NUMERIC(15,2) NOT NULL CHECK (valor_orcado >= 0),
    observacoes     TEXT,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por  VARCHAR(100) NOT NULL,
    UNIQUE (orcamento_id, modalidade, mes)
);

COMMENT ON TABLE orcamento_receitas IS 'Meta mensal de receita por modalidade.';


-- -------------------------------------------------------------
-- TABELA: orcamento_despesas
-- Meta de despesa por categoria e centro de custo por mês
-- -------------------------------------------------------------
CREATE TABLE orcamento_despesas (
    id              SERIAL PRIMARY KEY,
    orcamento_id    INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    categoria_id    INTEGER NOT NULL REFERENCES categorias_despesa(id),
    centro_custo_id INTEGER NOT NULL REFERENCES centros_custo(id),
    mes             DATE NOT NULL,
    valor_orcado    NUMERIC(15,2) NOT NULL CHECK (valor_orcado >= 0),
    observacoes     TEXT,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por  VARCHAR(100) NOT NULL,
    UNIQUE (orcamento_id, categoria_id, centro_custo_id, mes)
);

COMMENT ON TABLE orcamento_despesas IS 'Meta mensal de despesa por categoria e centro de custo.';

CREATE INDEX idx_orc_rec_orcamento  ON orcamento_receitas (orcamento_id, mes);
CREATE INDEX idx_orc_desp_orcamento ON orcamento_despesas (orcamento_id, mes);


-- -------------------------------------------------------------
-- FUNÇÃO: distribui meta anual em 12 meses iguais
-- Chamada ao criar o orçamento — pode ser ajustada depois
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_distribuir_meta_receita(
    p_orcamento_id  INTEGER,
    p_modalidade    VARCHAR,
    p_valor_anual   NUMERIC,
    p_ano           INTEGER,
    p_usuario       VARCHAR
)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    v_valor_mensal NUMERIC := ROUND(p_valor_anual / 12, 2);
    v_ajuste       NUMERIC := p_valor_anual - (v_valor_mensal * 12);
    v_mes          DATE;
    i              INTEGER;
BEGIN
    FOR i IN 1..12 LOOP
        v_mes := MAKE_DATE(p_ano, i, 1);
        INSERT INTO orcamento_receitas
            (orcamento_id, modalidade, mes, valor_orcado, atualizado_por)
        VALUES
            (p_orcamento_id, p_modalidade, v_mes,
             -- Adiciona o centavo de ajuste no último mês para fechar o anual
             CASE WHEN i = 12 THEN v_valor_mensal + v_ajuste ELSE v_valor_mensal END,
             p_usuario)
        ON CONFLICT (orcamento_id, modalidade, mes)
        DO UPDATE SET valor_orcado = EXCLUDED.valor_orcado, atualizado_em = NOW();
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION fn_distribuir_meta_despesa(
    p_orcamento_id  INTEGER,
    p_categoria_id  INTEGER,
    p_centro_id     INTEGER,
    p_valor_anual   NUMERIC,
    p_ano           INTEGER,
    p_usuario       VARCHAR
)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    v_valor_mensal NUMERIC := ROUND(p_valor_anual / 12, 2);
    v_ajuste       NUMERIC := p_valor_anual - (v_valor_mensal * 12);
    v_mes          DATE;
    i              INTEGER;
BEGIN
    FOR i IN 1..12 LOOP
        v_mes := MAKE_DATE(p_ano, i, 1);
        INSERT INTO orcamento_despesas
            (orcamento_id, categoria_id, centro_custo_id, mes, valor_orcado, atualizado_por)
        VALUES
            (p_orcamento_id, p_categoria_id, p_centro_id, v_mes,
             CASE WHEN i = 12 THEN v_valor_mensal + v_ajuste ELSE v_valor_mensal END,
             p_usuario)
        ON CONFLICT (orcamento_id, categoria_id, centro_custo_id, mes)
        DO UPDATE SET valor_orcado = EXCLUDED.valor_orcado, atualizado_em = NOW();
    END LOOP;
END;
$$;


-- -------------------------------------------------------------
-- VIEW: vw_orcado_vs_realizado_receita
-- Orçado × Realizado de receita por mês e modalidade
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_orcado_vs_realizado_receita AS
SELECT
    o.ano,
    orec.mes,
    orec.modalidade,
    orec.valor_orcado,
    COALESCE(real.receita_bruta, 0)                             AS valor_realizado,
    COALESCE(real.receita_bruta, 0) - orec.valor_orcado         AS desvio,
    CASE WHEN orec.valor_orcado > 0
         THEN ROUND((COALESCE(real.receita_bruta, 0) / orec.valor_orcado) * 100, 1)
         ELSE 0
    END                                                         AS atingimento_pct
FROM orcamento_receitas orec
JOIN orcamentos o         ON o.id = orec.orcamento_id
LEFT JOIN vw_dre_receitas_mensais real
    ON DATE_TRUNC('month', real.mes) = DATE_TRUNC('month', orec.mes)
    AND (real.modalidade = orec.modalidade OR orec.modalidade = 'TOTAL')
ORDER BY orec.mes, orec.modalidade;


-- -------------------------------------------------------------
-- VIEW: vw_orcado_vs_realizado_despesa
-- Orçado × Realizado de despesa por mês e categoria
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_orcado_vs_realizado_despesa AS
SELECT
    o.ano,
    odesp.mes,
    cd.tipo                                                     AS categoria_tipo,
    cd.nome                                                     AS categoria_nome,
    cc.nome                                                     AS centro_custo_nome,
    odesp.valor_orcado,
    COALESCE(real.valor_pago, 0)                                AS valor_realizado,
    COALESCE(real.valor_pago, 0) - odesp.valor_orcado           AS desvio,
    CASE WHEN odesp.valor_orcado > 0
         THEN ROUND((COALESCE(real.valor_pago, 0) / odesp.valor_orcado) * 100, 1)
         ELSE 0
    END                                                         AS atingimento_pct
FROM orcamento_despesas odesp
JOIN orcamentos o           ON o.id  = odesp.orcamento_id
JOIN categorias_despesa cd  ON cd.id = odesp.categoria_id
JOIN centros_custo      cc  ON cc.id = odesp.centro_custo_id
LEFT JOIN vw_dre_despesas_mensais real
    ON DATE_TRUNC('month', real.mes) = DATE_TRUNC('month', odesp.mes)
    AND real.tipo     = cd.tipo::TEXT
    AND real.categoria = cd.nome
ORDER BY odesp.mes, cd.tipo, cd.nome;


-- -------------------------------------------------------------
-- VIEW: vw_resumo_anual_orcamento
-- Resumo consolidado do ano — para o painel principal
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_resumo_anual_orcamento AS
SELECT
    o.ano,
    -- Receita
    SUM(orec.valor_orcado)                                          AS receita_orcada,
    COALESCE(SUM(real_rec.receita_bruta), 0)                        AS receita_realizada,
    COALESCE(SUM(real_rec.receita_bruta), 0)
        - SUM(orec.valor_orcado)                                    AS desvio_receita,
    -- Despesa
    SUM(odesp.valor_orcado)                                         AS despesa_orcada,
    COALESCE(SUM(real_desp.valor_pago), 0)                          AS despesa_realizada,
    COALESCE(SUM(real_desp.valor_pago), 0)
        - SUM(odesp.valor_orcado)                                   AS desvio_despesa,
    -- Resultado
    SUM(orec.valor_orcado) - SUM(odesp.valor_orcado)                AS resultado_orcado,
    COALESCE(SUM(real_rec.receita_bruta), 0)
        - COALESCE(SUM(real_desp.valor_pago), 0)                    AS resultado_realizado
FROM orcamentos o
LEFT JOIN orcamento_receitas orec
    ON orec.orcamento_id = o.id AND orec.modalidade = 'TOTAL'
LEFT JOIN orcamento_despesas odesp
    ON odesp.orcamento_id = o.id
LEFT JOIN vw_dre_receitas_mensais real_rec
    ON EXTRACT(YEAR FROM real_rec.mes) = o.ano
LEFT JOIN vw_dre_despesas_mensais real_desp
    ON EXTRACT(YEAR FROM real_desp.mes) = o.ano
GROUP BY o.ano
ORDER BY o.ano DESC;
