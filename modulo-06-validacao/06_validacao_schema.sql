-- =============================================================
-- SISTEMA DE GESTÃO DE CONTRATOS E FATURAMENTO
-- Módulo 06 — Validação por IA
-- Banco: PostgreSQL 14+
-- Depende dos Módulos 01 a 05
-- =============================================================

-- -------------------------------------------------------------
-- TIPOS ENUMERADOS
-- -------------------------------------------------------------
CREATE TYPE severidade_alerta  AS ENUM ('CRITICO', 'ATENCAO', 'INFO');
CREATE TYPE status_validacao   AS ENUM ('APROVADA', 'COM_ALERTAS', 'BLOQUEADA', 'JUSTIFICADA');
CREATE TYPE status_alerta      AS ENUM ('ABERTO', 'JUSTIFICADO', 'RESOLVIDO', 'IGNORADO');


-- -------------------------------------------------------------
-- TABELA: codigos_alerta
-- Catálogo de todos os códigos de erro possíveis
-- Permite configurar severidade e se bloqueia a emissão
-- -------------------------------------------------------------
CREATE TABLE codigos_alerta (
    codigo          VARCHAR(20) PRIMARY KEY,
    descricao       VARCHAR(200) NOT NULL,
    severidade      severidade_alerta NOT NULL,
    requer_justificativa BOOLEAN NOT NULL DEFAULT TRUE,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE codigos_alerta IS 'Catálogo de códigos de alerta da validação. Configurável sem alterar código.';

INSERT INTO codigos_alerta (codigo, descricao, severidade, requer_justificativa) VALUES
    ('VAL001', 'Valor faturado diferente do valor contratado',               'CRITICO',  TRUE),
    ('VAL002', 'Item faturado sem go-live confirmado',                       'CRITICO',  TRUE),
    ('VAL003', 'Fatura gerada fora da data de apuração do contrato',         'ATENCAO',  TRUE),
    ('VAL004', 'Reajuste aplicado sem aprovação interna',                    'CRITICO',  TRUE),
    ('VAL005', 'Contrato vencido ou encerrado — vigência expirada',          'CRITICO',  TRUE),
    ('VAL006', 'Volumetria faturada sem integração de folha recebida',       'ATENCAO',  TRUE),
    ('VAL007', 'Produto cancelado sendo faturado após data de cancelamento', 'CRITICO',  TRUE),
    ('VAL008', 'Produto em aviso prévio com prazo de vigência vencido',      'CRITICO',  TRUE),
    ('VAL009', 'Volumetria com variação acima de 20% em relação ao mês anterior', 'ATENCAO', TRUE),
    ('VAL010', 'Fatura duplicada para a mesma competência',                  'CRITICO',  TRUE),
    ('VAL011', 'Cliente bloqueado ou inativo com fatura em aberto',          'ATENCAO',  FALSE),
    ('VAL012', 'Desconto aplicado não consta no contrato',                   'ATENCAO',  TRUE);


-- -------------------------------------------------------------
-- TABELA: faturas_validacoes
-- Resultado de cada execução da validação em uma fatura
-- -------------------------------------------------------------
CREATE TABLE faturas_validacoes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fatura_id       UUID NOT NULL REFERENCES faturas(id) ON DELETE CASCADE,
    status          status_validacao NOT NULL,
    total_criticos  INTEGER NOT NULL DEFAULT 0,
    total_atencao   INTEGER NOT NULL DEFAULT 0,
    total_info      INTEGER NOT NULL DEFAULT 0,
    executado_em    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executado_por   VARCHAR(100) NOT NULL,
    -- Análise IA de anomalias (opcional, Claude API)
    analise_ia      JSONB,
    analise_ia_em   TIMESTAMPTZ
);

COMMENT ON TABLE  faturas_validacoes         IS 'Resultado consolidado da validação de cada fatura.';
COMMENT ON COLUMN faturas_validacoes.analise_ia IS 'Resultado opcional da análise de anomalias via Claude API (volumetria, padrões históricos).';


-- -------------------------------------------------------------
-- TABELA: faturas_alertas
-- Alertas individuais encontrados na validação
-- -------------------------------------------------------------
CREATE TABLE faturas_alertas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    validacao_id    UUID NOT NULL REFERENCES faturas_validacoes(id) ON DELETE CASCADE,
    fatura_id       UUID NOT NULL REFERENCES faturas(id) ON DELETE CASCADE,
    codigo          VARCHAR(20) NOT NULL REFERENCES codigos_alerta(codigo),
    severidade      severidade_alerta NOT NULL,
    detalhe         TEXT NOT NULL,      -- contexto específico: "Item X: R$ 500 contratado vs R$ 600 faturado"
    item_referencia UUID,               -- UUID do item relacionado (fatura_item, contrato_item, etc.)
    valor_esperado  NUMERIC(15,2),
    valor_encontrado NUMERIC(15,2),
    status          status_alerta NOT NULL DEFAULT 'ABERTO',
    justificativa   TEXT,               -- preenchida pelo usuário ao emitir com ressalva
    justificado_por VARCHAR(100),
    justificado_em  TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  faturas_alertas           IS 'Alertas individuais da validação. Um por regra violada.';
COMMENT ON COLUMN faturas_alertas.detalhe   IS 'Texto descritivo do problema encontrado, gerado pelo validador.';
COMMENT ON COLUMN faturas_alertas.justificativa IS 'Obrigatória para emissão quando severidade = CRITICO.';


-- -------------------------------------------------------------
-- TABELA: aviso_previo_cancelamento
-- Controla o prazo de vigência do aviso prévio de cancelamento de itens
-- Referenciado pela regra VAL008
-- -------------------------------------------------------------
CREATE TABLE aviso_previo_cancelamento (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_item_id    UUID NOT NULL REFERENCES contratos_itens(id) ON DELETE CASCADE,
    data_solicitacao    DATE NOT NULL DEFAULT CURRENT_DATE,
    prazo_vigencia_dias INTEGER NOT NULL DEFAULT 30,
    data_fim_vigencia   DATE NOT NULL,      -- data_solicitacao + prazo_vigencia_dias
    motivo              TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'ATIVO',   -- ATIVO | ENCERRADO
    criado_por          VARCHAR(100) NOT NULL,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_aviso_fim CHECK (data_fim_vigencia >= data_solicitacao)
);

COMMENT ON TABLE  aviso_previo_cancelamento              IS 'Aviso prévio de cancelamento de item. VAL008 verifica se o prazo expirou.';
COMMENT ON COLUMN aviso_previo_cancelamento.data_fim_vigencia IS 'Após esta data, o item não deve mais ser faturado.';


-- -------------------------------------------------------------
-- ÍNDICES
-- -------------------------------------------------------------
CREATE INDEX idx_validacoes_fatura    ON faturas_validacoes (fatura_id);
CREATE INDEX idx_alertas_fatura       ON faturas_alertas (fatura_id);
CREATE INDEX idx_alertas_codigo       ON faturas_alertas (codigo);
CREATE INDEX idx_alertas_status       ON faturas_alertas (status);
CREATE INDEX idx_alertas_severidade   ON faturas_alertas (severidade);
CREATE INDEX idx_aviso_item           ON aviso_previo_cancelamento (contrato_item_id);
CREATE INDEX idx_aviso_status_fim     ON aviso_previo_cancelamento (status, data_fim_vigencia);


-- -------------------------------------------------------------
-- VIEW: vw_faturas_alertas_abertos
-- Alertas abertos para acompanhamento no painel
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_faturas_alertas_abertos AS
SELECT
    fa.id                   AS alerta_id,
    fa.fatura_id,
    f.numero_fatura,
    COALESCE(cl.razao_social, cl.nome_completo) AS cliente_nome,
    f.competencia,
    fa.codigo,
    ca.descricao            AS descricao_alerta,
    fa.severidade,
    fa.detalhe,
    fa.valor_esperado,
    fa.valor_encontrado,
    fa.status               AS status_alerta,
    fa.criado_em
FROM faturas_alertas fa
JOIN faturas f         ON f.id  = fa.fatura_id
JOIN contratos c       ON c.id  = f.contrato_id
JOIN clientes cl       ON cl.id = c.cliente_id
JOIN codigos_alerta ca ON ca.codigo = fa.codigo
WHERE fa.status = 'ABERTO'
ORDER BY
    CASE fa.severidade WHEN 'CRITICO' THEN 1 WHEN 'ATENCAO' THEN 2 ELSE 3 END,
    fa.criado_em DESC;
