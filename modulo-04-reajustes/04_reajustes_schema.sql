-- =============================================================
-- SISTEMA DE GESTÃO DE CONTRATOS E FATURAMENTO
-- Módulo 04 — Reajustes e Aditivos
-- Banco: PostgreSQL 14+
-- Depende dos Módulos 01, 02 e 03
-- =============================================================

-- -------------------------------------------------------------
-- TIPOS ENUMERADOS
-- -------------------------------------------------------------
CREATE TYPE indice_economico     AS ENUM ('INPC', 'IPCA', 'IGPM', 'FIXO', 'DISSIDIO');
-- DISSIDIO: percentual fixo anual por convenção coletiva — exclusivo para itens de mão de obra alocada (BPO)
CREATE TYPE status_reajuste      AS ENUM ('CALCULADO', 'AGUARDANDO_APROVACAO', 'APROVADO', 'REPROVADO', 'COMUNICADO', 'EFETIVADO', 'CANCELADO');
CREATE TYPE tipo_aditivo         AS ENUM ('REAJUSTE', 'PRAZO', 'ESCOPO', 'RESCISAO', 'OUTROS');


-- -------------------------------------------------------------
-- CAMPO ADICIONAL em produtos_servicos
-- Marca itens de mão de obra alocada (BPO) — reajuste pelo dissídio
-- -------------------------------------------------------------
ALTER TABLE produtos_servicos
    ADD COLUMN IF NOT EXISTS mao_de_obra_alocada BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN produtos_servicos.mao_de_obra_alocada IS
    'TRUE = item de mão de obra alocada (BPO). Reajuste pelo dissídio da categoria.';


-- -------------------------------------------------------------
-- TABELA: dissidios_historico
-- Percentual fixo anual do dissídio por categoria
-- -------------------------------------------------------------
CREATE TABLE dissidios_historico (
    id               SERIAL PRIMARY KEY,
    categoria        VARCHAR(100) NOT NULL DEFAULT 'GERAL',
    ano_base         INTEGER NOT NULL CHECK (ano_base BETWEEN 2000 AND 2099),
    data_vigencia    DATE NOT NULL,
    valor_percentual NUMERIC(8,4) NOT NULL,
    fonte            VARCHAR(200),
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por       VARCHAR(100),

    CONSTRAINT uq_dissidio_categoria_ano UNIQUE (categoria, ano_base)
);

COMMENT ON TABLE  dissidios_historico           IS 'Histórico anual do dissídio. Percentual fixo negociado em convenção coletiva.';
COMMENT ON COLUMN dissidios_historico.categoria IS 'Categoria sindical. Padrão: GERAL.';


-- -------------------------------------------------------------
-- TABELA: indices_economicos_historico
-- Armazena os valores mensais de cada índice (INPC, IPCA, IGPM)
-- Alimentado manualmente ou via integração com IBGE/FGV
-- -------------------------------------------------------------
CREATE TABLE indices_economicos_historico (
    id              SERIAL PRIMARY KEY,
    indice          indice_economico NOT NULL,
    competencia     DATE NOT NULL,              -- sempre o 1º dia do mês de referência
    valor_percentual NUMERIC(8,4) NOT NULL,     -- variação mensal em % (ex: 0.43 = 0,43%)
    fonte           VARCHAR(100),               -- ex: IBGE, FGV, manual
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100),

    CONSTRAINT uq_indice_competencia UNIQUE (indice, competencia),
    CONSTRAINT chk_competencia_dia1 CHECK (EXTRACT(DAY FROM competencia) = 1)
);

COMMENT ON TABLE  indices_economicos_historico             IS 'Histórico mensal dos índices econômicos. Competência sempre no 1º dia do mês.';
COMMENT ON COLUMN indices_economicos_historico.valor_percentual IS 'Variação mensal em percentual. Ex: 0.43 representa 0,43%.';


-- -------------------------------------------------------------
-- TABELA: contratos_reajustes
-- Cabeçalho do processo de reajuste de um contrato
-- -------------------------------------------------------------
CREATE TABLE contratos_reajustes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_id         UUID NOT NULL REFERENCES contratos(id) ON DELETE RESTRICT,
    numero_reajuste     INTEGER NOT NULL,           -- sequencial por contrato (1º, 2º...)

    -- Índice e período
    indice              indice_economico NOT NULL,
    percentual_fixo     NUMERIC(8,4),               -- preenchido quando indice = FIXO
    data_base           DATE NOT NULL,              -- data de início do período (assinatura ou último reajuste)
    data_fim_periodo    DATE NOT NULL,              -- data de fim dos 12 meses
    competencia_inicial DATE NOT NULL,              -- 1º mês do período para cálculo acumulado
    competencia_final   DATE NOT NULL,              -- último mês do período para cálculo acumulado

    -- Percentual calculado (acumulado do período)
    percentual_calculado NUMERIC(8,4),             -- calculado automaticamente com base no histórico
    percentual_aplicado  NUMERIC(8,4),             -- pode diferir (negociação comercial)

    -- Impacto financeiro
    valor_mensal_anterior NUMERIC(15,2) NOT NULL,
    valor_mensal_novo     NUMERIC(15,2),            -- calculado após aprovação
    variacao_mensal       NUMERIC(15,2),            -- diferença em R$

    -- Fluxo de aprovação
    status              status_reajuste NOT NULL DEFAULT 'CALCULADO',
    data_calculo        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    calculado_por       VARCHAR(100) NOT NULL,
    data_aprovacao      TIMESTAMPTZ,
    aprovado_por        VARCHAR(100),
    motivo_reprovacao   TEXT,
    data_comunicacao    DATE,                       -- data em que o cliente foi comunicado
    data_efetivacao     DATE NOT NULL,              -- data a partir da qual os novos valores vigoram
    observacoes         TEXT,

    -- Aditivo gerado
    aditivo_id          UUID REFERENCES contratos_aditivos(id),

    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_reajuste_numero UNIQUE (contrato_id, numero_reajuste),
    CONSTRAINT chk_periodo CHECK (data_fim_periodo > data_base),
    CONSTRAINT chk_competencias CHECK (competencia_final >= competencia_inicial)
);

COMMENT ON TABLE  contratos_reajustes                     IS 'Processo de reajuste por contrato. Um por período de 12 meses.';
COMMENT ON COLUMN contratos_reajustes.percentual_calculado IS 'Acumulado do índice no período. Calculado pela função fn_calcula_reajuste.';
COMMENT ON COLUMN contratos_reajustes.percentual_aplicado  IS 'Percentual efetivamente aplicado — pode ser negociado com o cliente.';
COMMENT ON COLUMN contratos_reajustes.data_efetivacao      IS 'Data a partir da qual os novos valores passam a valer no faturamento.';


-- -------------------------------------------------------------
-- TABELA: contratos_reajustes_itens
-- Detalhe do reajuste item a item
-- -------------------------------------------------------------
CREATE TABLE contratos_reajustes_itens (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reajuste_id         UUID NOT NULL REFERENCES contratos_reajustes(id) ON DELETE CASCADE,
    contrato_item_id    UUID NOT NULL REFERENCES contratos_itens(id) ON DELETE RESTRICT,

    -- Valores
    valor_anterior      NUMERIC(15,2) NOT NULL,
    percentual_aplicado NUMERIC(8,4)  NOT NULL,
    valor_novo          NUMERIC(15,2) NOT NULL,
    variacao            NUMERIC(15,2) GENERATED ALWAYS AS (valor_novo - valor_anterior) STORED,

    -- Aprovação individual (permite negociar item a item)
    usa_dissidio        BOOLEAN NOT NULL DEFAULT FALSE,
    aprovado            BOOLEAN,
    observacoes         TEXT
);

COMMENT ON TABLE  contratos_reajustes_itens IS 'Reajuste item a item. Itens de mão de obra alocada (BPO) usam dissídio; demais usam o índice do contrato.';
COMMENT ON COLUMN contratos_reajustes_itens.usa_dissidio IS 'TRUE = item reajustado pelo dissídio da categoria, não pelo índice do contrato.';


-- -------------------------------------------------------------
-- TABELA: contratos_aditivos (expansão do módulo 02)
-- O módulo 02 criou a estrutura básica; aqui detalhamos os campos
-- -------------------------------------------------------------
ALTER TABLE contratos_aditivos
    ADD COLUMN IF NOT EXISTS tipo_aditivo   tipo_aditivo,
    ADD COLUMN IF NOT EXISTS status         VARCHAR(30) NOT NULL DEFAULT 'RASCUNHO',
    ADD COLUMN IF NOT EXISTS aprovado_por   VARCHAR(100),
    ADD COLUMN IF NOT EXISTS data_aprovacao DATE,
    ADD COLUMN IF NOT EXISTS arquivo_url    VARCHAR(500),
    ADD COLUMN IF NOT EXISTS atualizado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS atualizado_por VARCHAR(100);

COMMENT ON COLUMN contratos_aditivos.tipo_aditivo IS 'REAJUSTE | PRAZO | ESCOPO | RESCISAO | OUTROS';
COMMENT ON COLUMN contratos_aditivos.status       IS 'RASCUNHO → APROVADO → ASSINADO → VIGENTE';
COMMENT ON COLUMN contratos_aditivos.arquivo_url  IS 'URL do documento do aditivo assinado (futuro: integração com GED)';


-- -------------------------------------------------------------
-- ÍNDICES
-- -------------------------------------------------------------
CREATE INDEX idx_indices_indice_competencia ON indices_economicos_historico (indice, competencia);
CREATE INDEX idx_reajustes_contrato_id      ON contratos_reajustes (contrato_id);
CREATE INDEX idx_reajustes_status           ON contratos_reajustes (status);
CREATE INDEX idx_reajustes_data_efetivacao  ON contratos_reajustes (data_efetivacao);
CREATE INDEX idx_reajustes_itens_reajuste   ON contratos_reajustes_itens (reajuste_id);


-- -------------------------------------------------------------
-- TRIGGER: timestamp nos reajustes
-- -------------------------------------------------------------
CREATE TRIGGER trg_reajuste_timestamp
    BEFORE UPDATE ON contratos_reajustes
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE TRIGGER trg_aditivo_timestamp
    BEFORE UPDATE ON contratos_aditivos
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();


-- -------------------------------------------------------------
-- FUNÇÃO: calcula percentual acumulado de um índice no período
-- Produto dos fatores mensais: (1+v1/100) × (1+v2/100) × ... - 1
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_calcula_acumulado_indice(
    p_indice          indice_economico,
    p_competencia_ini DATE,
    p_competencia_fim DATE
)
RETURNS NUMERIC(8,4) LANGUAGE plpgsql AS $$
DECLARE
    v_fator     NUMERIC := 1;
    v_variacao  NUMERIC;
    v_mes       DATE;
BEGIN
    v_mes := DATE_TRUNC('month', p_competencia_ini);

    WHILE v_mes <= DATE_TRUNC('month', p_competencia_fim) LOOP
        SELECT valor_percentual INTO v_variacao
        FROM indices_economicos_historico
        WHERE indice = p_indice AND competencia = v_mes;

        IF v_variacao IS NULL THEN
            RAISE EXCEPTION 'Índice % sem valor para a competência %.',
                p_indice, TO_CHAR(v_mes, 'MM/YYYY');
        END IF;

        v_fator := v_fator * (1 + v_variacao / 100);
        v_mes   := v_mes + INTERVAL '1 month';
    END LOOP;

    RETURN ROUND((v_fator - 1) * 100, 4);
END;
$$;

COMMENT ON FUNCTION fn_calcula_acumulado_indice IS
    'Calcula a variação acumulada de um índice entre dois meses (inclusive). '
    'Usa produto dos fatores mensais. Retorna percentual. Ex: 5.3421 = 5,3421%.';


-- -------------------------------------------------------------
-- FUNÇÃO: ao efetivar reajuste, atualiza valores dos itens
-- e gera aditivo automaticamente
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_efetiva_reajuste()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_numero_aditivo INTEGER;
    v_aditivo_id     UUID;
BEGIN
    IF NEW.status = 'EFETIVADO' AND OLD.status != 'EFETIVADO' THEN

        -- Atualiza valor unitário de cada item aprovado
        UPDATE contratos_itens ci
        SET valor_unitario = ri.valor_novo,
            atualizado_em  = NOW()
        FROM contratos_reajustes_itens ri
        WHERE ri.reajuste_id      = NEW.id
          AND ri.contrato_item_id = ci.id
          AND ri.aprovado         IS DISTINCT FROM FALSE;

        -- Gera número sequencial do aditivo
        SELECT COALESCE(MAX(numero_aditivo), 0) + 1
        INTO v_numero_aditivo
        FROM contratos_aditivos
        WHERE contrato_id = NEW.contrato_id;

        -- Cria o aditivo de reajuste
        INSERT INTO contratos_aditivos (
            contrato_id, numero_aditivo, tipo, tipo_aditivo, descricao,
            data_aditivo, data_vigencia,
            valor_anterior, valor_novo,
            status, criado_por, atualizado_por
        ) VALUES (
            NEW.contrato_id,
            v_numero_aditivo,
            'REAJUSTE',
            'REAJUSTE',
            'Reajuste ' || NEW.numero_reajuste || 'º — ' || NEW.indice ||
                ' acumulado: ' || NEW.percentual_calculado || '% / aplicado: ' || NEW.percentual_aplicado || '%',
            CURRENT_DATE,
            NEW.data_efetivacao,
            NEW.valor_mensal_anterior,
            NEW.valor_mensal_novo,
            'VIGENTE',
            NEW.aprovado_por,
            NEW.aprovado_por
        )
        RETURNING id INTO v_aditivo_id;

        -- Vincula o aditivo ao reajuste
        NEW.aditivo_id := v_aditivo_id;

        -- Atualiza valor_mensal no cabeçalho do contrato
        UPDATE contratos
        SET valor_mensal   = NEW.valor_mensal_novo,
            atualizado_em  = NOW()
        WHERE id = NEW.contrato_id;

    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_efetiva_reajuste
    BEFORE UPDATE ON contratos_reajustes
    FOR EACH ROW EXECUTE FUNCTION fn_efetiva_reajuste();


-- -------------------------------------------------------------
-- VIEW: vw_reajustes_pendentes
-- Contratos com reajuste vencido (>= 12 meses sem reajuste)
-- ou com reajuste aguardando aprovação
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_reajustes_pendentes AS
SELECT
    c.id                                                AS contrato_id,
    c.numero                                            AS contrato_numero,
    COALESCE(cl.razao_social, cl.nome_completo)         AS cliente_nome,
    c.modalidade,
    c.valor_mensal,
    c.data_inicio_recorrencia,
    -- Último reajuste efetivado
    MAX(CASE WHEN r.status = 'EFETIVADO' THEN r.data_efetivacao END) AS ultimo_reajuste,
    -- Próxima data de reajuste (12 meses após último reajuste ou assinatura)
    COALESCE(
        MAX(CASE WHEN r.status = 'EFETIVADO' THEN r.data_efetivacao END) + INTERVAL '12 months',
        c.data_assinatura + INTERVAL '12 months'
    )::DATE                                             AS proximo_reajuste,
    -- Dias de atraso (negativo = ainda não venceu)
    (CURRENT_DATE - COALESCE(
        MAX(CASE WHEN r.status = 'EFETIVADO' THEN r.data_efetivacao END) + INTERVAL '12 months',
        c.data_assinatura + INTERVAL '12 months'
    )::DATE)                                            AS dias_atraso,
    -- Reajuste em andamento
    MAX(CASE WHEN r.status NOT IN ('EFETIVADO','CANCELADO','REPROVADO')
             THEN r.status END)                         AS status_em_andamento,
    COUNT(r.id)                                         AS total_reajustes
FROM contratos c
JOIN clientes cl ON cl.id = c.cliente_id
LEFT JOIN contratos_reajustes r ON r.contrato_id = c.id
WHERE c.status    = 'ATIVO'
  AND c.fase_atual = 'RECORRENCIA'
GROUP BY c.id, c.numero, cl.razao_social, cl.nome_completo,
         c.modalidade, c.valor_mensal, c.data_inicio_recorrencia, c.data_assinatura;

COMMENT ON VIEW vw_reajustes_pendentes IS 'Contratos ativos em recorrência com controle de próximo reajuste e dias de atraso.';


-- -------------------------------------------------------------
-- DADOS INICIAIS: competências de exemplo (jan–dez 2024)
-- Valores meramente ilustrativos — substituir com dados reais do IBGE/FGV
-- -------------------------------------------------------------
INSERT INTO indices_economicos_historico (indice, competencia, valor_percentual, fonte) VALUES
    ('INPC','2024-01-01', 0.42, 'IBGE'), ('INPC','2024-02-01', 0.36, 'IBGE'),
    ('INPC','2024-03-01', 0.20, 'IBGE'), ('INPC','2024-04-01', 0.34, 'IBGE'),
    ('INPC','2024-05-01', 0.19, 'IBGE'), ('INPC','2024-06-01', 0.56, 'IBGE'),
    ('INPC','2024-07-01', 0.27, 'IBGE'), ('INPC','2024-08-01', 0.45, 'IBGE'),
    ('INPC','2024-09-01', 0.48, 'IBGE'), ('INPC','2024-10-01', 0.56, 'IBGE'),
    ('INPC','2024-11-01', 0.39, 'IBGE'), ('INPC','2024-12-01', 0.48, 'IBGE'),
    ('IPCA','2024-01-01', 0.42, 'IBGE'), ('IPCA','2024-02-01', 0.83, 'IBGE'),
    ('IPCA','2024-03-01', 0.16, 'IBGE'), ('IPCA','2024-04-01', 0.38, 'IBGE'),
    ('IPCA','2024-05-01', 0.46, 'IBGE'), ('IPCA','2024-06-01', 0.20, 'IBGE'),
    ('IPCA','2024-07-01', 0.38, 'IBGE'), ('IPCA','2024-08-01', 0.44, 'IBGE'),
    ('IPCA','2024-09-01', 0.44, 'IBGE'), ('IPCA','2024-10-01', 0.56, 'IBGE'),
    ('IPCA','2024-11-01', 0.39, 'IBGE'), ('IPCA','2024-12-01', 0.52, 'IBGE'),
    ('IGPM','2024-01-01',-0.07, 'FGV'),  ('IGPM','2024-02-01', 0.78, 'FGV'),
    ('IGPM','2024-03-01', 0.47, 'FGV'),  ('IGPM','2024-04-01', 0.89, 'FGV'),
    ('IGPM','2024-05-01', 0.87, 'FGV'),  ('IGPM','2024-06-01', 0.81, 'FGV'),
    ('IGPM','2024-07-01', 0.61, 'FGV'),  ('IGPM','2024-08-01', 0.29, 'FGV'),
    ('IGPM','2024-09-01', 0.62, 'FGV'),  ('IGPM','2024-10-01', 1.52, 'FGV'),
    ('IGPM','2024-11-01', 1.35, 'FGV'),  ('IGPM','2024-12-01', 0.94, 'FGV');
