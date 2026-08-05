-- =============================================================
-- SISTEMA DE GESTÃO — Módulo 08: Contas a Pagar
-- =============================================================

CREATE TYPE status_despesa      AS ENUM ('LANCADA','AGUARDANDO_APROVACAO','APROVADA','PAGA','CONCILIADA','CANCELADA','REPROVADA');
CREATE TYPE tipo_despesa        AS ENUM ('FORNECEDOR','FOLHA','BENEFICIO','IMPOSTO','ADMINISTRATIVA','COMISSAO','OUTROS');
CREATE TYPE subtipo_beneficio   AS ENUM ('VR','VA','SAUDE','SEGURO_VIDA','ODONTO','FARMACIA','OUTROS');
CREATE TYPE forma_pagamento_cp  AS ENUM ('TED','PIX','BOLETO','CHEQUE','DEBITO_AUTOMATICO','OUTROS');
CREATE TYPE status_aprovacao_cp AS ENUM ('PENDENTE','APROVADO','REPROVADO');


-- -------------------------------------------------------------
-- TABELA: centros_custo
-- -------------------------------------------------------------
CREATE TABLE centros_custo (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(20)  NOT NULL UNIQUE,
    nome        VARCHAR(150) NOT NULL,
    descricao   TEXT,
    responsavel VARCHAR(150),
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por  VARCHAR(100)
);

INSERT INTO centros_custo (codigo, nome, responsavel) VALUES
    ('ADM',      'Administrativo',              NULL),
    ('RH',       'Recursos Humanos',            NULL),
    ('DP',       'Departamento Pessoal',        NULL),
    ('COMERC',   'Comercial',                   NULL),
    ('CONV',     'Conversão',                   NULL),
    ('MKT',      'Marketing',                   NULL),
    ('IMPL',     'Implantação',                 NULL),
    ('TI',       'Tecnologia',                  NULL),
    ('QA',       'Quality Assurance',           NULL),
    ('FIN',      'Financeiro',                  NULL),
    ('OPEX',     'Operacional',                 NULL),
    ('DIR_GERAL','Diretoria Geral',             NULL),
    ('DIR_REL',  'Diretoria de Relacionamento', NULL),
    ('DIR_OP',   'Diretoria Operacional',       NULL);


-- -------------------------------------------------------------
-- TABELA: categorias_despesa
-- -------------------------------------------------------------
CREATE TABLE categorias_despesa (
    id          SERIAL PRIMARY KEY,
    tipo        tipo_despesa NOT NULL,
    subtipo     subtipo_beneficio,          -- preenchido apenas quando tipo = BENEFICIO
    nome        VARCHAR(150) NOT NULL,
    descricao   TEXT,
    requer_aprovacao     BOOLEAN NOT NULL DEFAULT TRUE,
    limite_sem_aprovacao NUMERIC(15,2),     -- abaixo deste valor, aprovação é automática
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO categorias_despesa (tipo, subtipo, nome, requer_aprovacao, limite_sem_aprovacao) VALUES
    -- Folha
    ('FOLHA',        NULL,        'Salários',                    TRUE,  NULL),
    ('FOLHA',        NULL,        'Férias',                      TRUE,  NULL),
    ('FOLHA',        NULL,        'Rescisões',                   TRUE,  NULL),
    ('FOLHA',        NULL,        'Reembolsos',                  TRUE,  500.00),
    ('FOLHA',        NULL,        'Encargos (FGTS/INSS)',        TRUE,  NULL),
    -- Benefícios
    ('BENEFICIO',    'VR',        'Vale Refeição',               TRUE,  NULL),
    ('BENEFICIO',    'SAUDE',     'Plano de Saúde',              TRUE,  NULL),
    ('BENEFICIO',    'SEGURO_VIDA','Seguro de Vida',             TRUE,  NULL),
    ('BENEFICIO',    'ODONTO',    'Plano Odontológico',          TRUE,  NULL),
    ('BENEFICIO',    'FARMACIA',  'Convênio Farmácia',           TRUE,  NULL),
    -- Fornecedores
    ('FORNECEDOR',   NULL,        'Internet e Telefonia',        TRUE,  300.00),
    ('FORNECEDOR',   NULL,        'Softwares e Licenças',        TRUE,  NULL),
    ('FORNECEDOR',   NULL,        'Serviços Terceirizados',      TRUE,  NULL),
    -- Impostos
    ('IMPOSTO',      NULL,        'ISS',                         TRUE,  NULL),
    ('IMPOSTO',      NULL,        'PIS/COFINS/CSLL',             TRUE,  NULL),
    ('IMPOSTO',      NULL,        'IRPJ/CSLL',                   TRUE,  NULL),
    ('IMPOSTO',      NULL,        'Outros Impostos',             TRUE,  NULL),
    -- Administrativa
    ('ADMINISTRATIVA',NULL,       'Aluguel',                     TRUE,  NULL),
    ('ADMINISTRATIVA',NULL,       'Energia Elétrica',            TRUE,  500.00),
    ('ADMINISTRATIVA',NULL,       'Material de Escritório',      TRUE,  200.00),
    ('ADMINISTRATIVA',NULL,       'Outros',                      TRUE,  200.00),
    -- Comissões
    ('COMISSAO',     NULL,        'Comissão por Indicação',      TRUE,  NULL);


-- -------------------------------------------------------------
-- TABELA: fornecedores
-- -------------------------------------------------------------
CREATE TABLE fornecedores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    razao_social    VARCHAR(200) NOT NULL,
    nome_fantasia   VARCHAR(200),
    cnpj_cpf        VARCHAR(14)  UNIQUE,
    email           VARCHAR(254),
    telefone        VARCHAR(20),
    banco           VARCHAR(100),
    agencia         VARCHAR(20),
    conta           VARCHAR(30),
    pix_chave       VARCHAR(150),
    observacoes     TEXT,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100)
);


-- -------------------------------------------------------------
-- TABELA: despesas
-- -------------------------------------------------------------
CREATE TABLE despesas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero_despesa      VARCHAR(30) NOT NULL UNIQUE,        -- DES-2026-00001
    categoria_id        INTEGER NOT NULL REFERENCES categorias_despesa(id),
    centro_custo_id     INTEGER NOT NULL REFERENCES centros_custo(id),
    fornecedor_id       UUID REFERENCES fornecedores(id),
    descricao           VARCHAR(300) NOT NULL,
    competencia         DATE NOT NULL,                      -- mês de referência
    data_lancamento     DATE NOT NULL DEFAULT CURRENT_DATE,
    data_vencimento     DATE NOT NULL,
    valor               NUMERIC(15,2) NOT NULL CHECK (valor > 0),
    status              status_despesa NOT NULL DEFAULT 'LANCADA',

    -- Aprovação (dois aprovadores)
    aprovador1_id       UUID REFERENCES usuarios(id),
    aprovador1_status   status_aprovacao_cp,
    aprovador1_em       TIMESTAMPTZ,
    aprovador1_obs      TEXT,
    aprovador2_id       UUID REFERENCES usuarios(id),
    aprovador2_status   status_aprovacao_cp,
    aprovador2_em       TIMESTAMPTZ,
    aprovador2_obs      TEXT,

    -- Pagamento
    data_pagamento      DATE,
    valor_pago          NUMERIC(15,2),
    forma_pagamento     forma_pagamento_cp,
    banco_pagamento     VARCHAR(100),
    identificador_pag   VARCHAR(100),       -- código da transação no banco

    -- Conciliação
    conciliado          BOOLEAN NOT NULL DEFAULT FALSE,
    conciliado_em       TIMESTAMPTZ,
    conciliado_por      VARCHAR(100),

    -- Documento de suporte
    numero_documento    VARCHAR(50),        -- NF, recibo, etc.
    observacoes         TEXT,

    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL,
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por      VARCHAR(100) NOT NULL
);

CREATE INDEX idx_despesas_status         ON despesas (status);
CREATE INDEX idx_despesas_competencia    ON despesas (competencia);
CREATE INDEX idx_despesas_vencimento     ON despesas (data_vencimento);
CREATE INDEX idx_despesas_categoria_id   ON despesas (categoria_id);
CREATE INDEX idx_despesas_centro_custo   ON despesas (centro_custo_id);
CREATE INDEX idx_despesas_fornecedor_id  ON despesas (fornecedor_id);


-- -------------------------------------------------------------
-- SEQUÊNCIA: número da despesa
-- -------------------------------------------------------------
CREATE SEQUENCE seq_despesa_numero START 1;

CREATE OR REPLACE FUNCTION fn_gera_numero_despesa()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.numero_despesa IS NULL OR NEW.numero_despesa = '' THEN
        NEW.numero_despesa := 'DES-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
                              LPAD(NEXTVAL('seq_despesa_numero')::TEXT, 5, '0');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_numero_despesa
    BEFORE INSERT ON despesas
    FOR EACH ROW EXECUTE FUNCTION fn_gera_numero_despesa();


-- -------------------------------------------------------------
-- FUNÇÃO: avança status após aprovações
-- Regra: precisa dos dois aprovadores para ir para APROVADA
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_avanca_status_aprovacao()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Se qualquer aprovador reprovou, vai para REPROVADA
    IF NEW.aprovador1_status = 'REPROVADO' OR NEW.aprovador2_status = 'REPROVADO' THEN
        NEW.status := 'REPROVADA';
    -- Se os dois aprovaram, vai para APROVADA
    ELSIF NEW.aprovador1_status = 'APROVADO' AND NEW.aprovador2_status = 'APROVADO' THEN
        NEW.status := 'APROVADA';
    -- Se apenas um aprovou, continua AGUARDANDO_APROVACAO
    ELSIF NEW.aprovador1_status = 'APROVADO' OR NEW.aprovador2_status = 'APROVADO' THEN
        NEW.status := 'AGUARDANDO_APROVACAO';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_aprovacao_despesa
    BEFORE UPDATE OF aprovador1_status, aprovador2_status ON despesas
    FOR EACH ROW EXECUTE FUNCTION fn_avanca_status_aprovacao();


-- -------------------------------------------------------------
-- VIEW: vw_despesas_resumo
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_despesas_resumo AS
SELECT
    d.id,
    d.numero_despesa,
    d.descricao,
    d.competencia,
    d.data_vencimento,
    d.valor,
    d.valor_pago,
    d.status,
    d.conciliado,
    cd.tipo                                     AS categoria_tipo,
    cd.nome                                     AS categoria_nome,
    cc.codigo                                   AS centro_custo_codigo,
    cc.nome                                     AS centro_custo_nome,
    COALESCE(f.razao_social, f.nome_fantasia)   AS fornecedor_nome,
    CASE WHEN CURRENT_DATE > d.data_vencimento
         AND d.status NOT IN ('PAGA','CONCILIADA','CANCELADA','REPROVADA')
         THEN (CURRENT_DATE - d.data_vencimento) ELSE 0
    END                                         AS dias_atraso,
    d.criado_em,
    d.criado_por
FROM despesas d
JOIN categorias_despesa cd ON cd.id = d.categoria_id
JOIN centros_custo      cc ON cc.id = d.centro_custo_id
LEFT JOIN fornecedores  f  ON f.id  = d.fornecedor_id;


-- -------------------------------------------------------------
-- VIEW: vw_despesas_por_categoria — para DRE e análises
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_despesas_por_categoria AS
SELECT
    DATE_TRUNC('month', competencia)    AS mes,
    categoria_tipo,
    categoria_nome,
    centro_custo_codigo,
    centro_custo_nome,
    COUNT(*)                            AS quantidade,
    SUM(valor)                          AS total_lancado,
    SUM(CASE WHEN status IN ('PAGA','CONCILIADA') THEN COALESCE(valor_pago, valor) ELSE 0 END) AS total_pago
FROM vw_despesas_resumo
WHERE status != 'CANCELADA'
GROUP BY 1,2,3,4,5;
