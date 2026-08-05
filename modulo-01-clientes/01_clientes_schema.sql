-- =============================================================
-- SISTEMA DE GESTÃO DE CONTRATOS E FATURAMENTO
-- Módulo 01 — Cadastro de Clientes
-- Banco: PostgreSQL 14+
-- =============================================================

-- -------------------------------------------------------------
-- EXTENSÕES
-- -------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";


-- -------------------------------------------------------------
-- TIPOS ENUMERADOS
-- -------------------------------------------------------------
CREATE TYPE tipo_pessoa      AS ENUM ('PF', 'PJ');
CREATE TYPE porte_empresa    AS ENUM ('MEI', 'MICRO', 'PEQUENO', 'MEDIO', 'GRANDE');
CREATE TYPE status_cliente   AS ENUM ('PROSPECTO', 'ATIVO', 'INATIVO', 'BLOQUEADO');
CREATE TYPE tipo_endereco    AS ENUM ('MATRIZ', 'FILIAL', 'COBRANCA', 'ENTREGA');
CREATE TYPE tipo_contato     AS ENUM ('FINANCEIRO', 'CONTRATO', 'TECNICO', 'COMERCIAL', 'OUTRO');


-- -------------------------------------------------------------
-- TABELA: segmentos
-- Lookup de segmentos de mercado (configurável pelo usuário)
-- -------------------------------------------------------------
CREATE TABLE segmentos (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL UNIQUE,
    descricao   TEXT,
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE segmentos IS 'Segmentos de mercado dos clientes (ex: Saúde, Varejo, Indústria)';


-- -------------------------------------------------------------
-- TABELA: clientes
-- -------------------------------------------------------------
CREATE TABLE clientes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo_pessoa         tipo_pessoa NOT NULL,

    -- Pessoa Jurídica
    razao_social        VARCHAR(200),
    nome_fantasia       VARCHAR(200),
    cnpj                CHAR(14),               -- apenas dígitos
    inscricao_estadual  VARCHAR(20),
    inscricao_municipal VARCHAR(20),

    -- Pessoa Física
    nome_completo       VARCHAR(200),
    cpf                 CHAR(11),               -- apenas dígitos

    -- Classificação
    segmento_id         INTEGER REFERENCES segmentos(id) ON DELETE SET NULL,
    porte               porte_empresa,
    origem              VARCHAR(100),           -- ex: indicação, site, prospecção
    observacoes         TEXT,

    -- Status
    status              status_cliente NOT NULL DEFAULT 'PROSPECTO',
    motivo_inativacao   TEXT,
    inativado_em        TIMESTAMPTZ,
    inativado_por       VARCHAR(100),

    -- Auditoria
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100) NOT NULL,
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_por      VARCHAR(100) NOT NULL,

    -- Constraints
    CONSTRAINT chk_pj_campos CHECK (
        tipo_pessoa = 'PF' OR (razao_social IS NOT NULL AND cnpj IS NOT NULL)
    ),
    CONSTRAINT chk_pf_campos CHECK (
        tipo_pessoa = 'PJ' OR (nome_completo IS NOT NULL AND cpf IS NOT NULL)
    ),
    CONSTRAINT chk_cnpj_formato CHECK (
        cnpj IS NULL OR (LENGTH(cnpj) = 14 AND cnpj ~ '^\d{14}$')
    ),
    CONSTRAINT chk_cpf_formato CHECK (
        cpf IS NULL OR (LENGTH(cpf) = 11 AND cpf ~ '^\d{11}$')
    ),
    CONSTRAINT uq_cnpj UNIQUE (cnpj),
    CONSTRAINT uq_cpf  UNIQUE (cpf)
);

COMMENT ON TABLE  clientes                  IS 'Cadastro central de clientes (PF e PJ)';
COMMENT ON COLUMN clientes.cnpj             IS 'Somente dígitos, sem pontuação. Validação de dígitos verificadores feita na aplicação.';
COMMENT ON COLUMN clientes.cpf              IS 'Somente dígitos, sem pontuação.';
COMMENT ON COLUMN clientes.status           IS 'PROSPECTO: em negociação | ATIVO: com contrato vigente | INATIVO: sem contratos | BLOQUEADO: impedido de operar';


-- -------------------------------------------------------------
-- TABELA: clientes_enderecos
-- Um cliente pode ter múltiplos endereços
-- -------------------------------------------------------------
CREATE TABLE clientes_enderecos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    tipo            tipo_endereco NOT NULL DEFAULT 'MATRIZ',
    principal       BOOLEAN NOT NULL DEFAULT FALSE,

    cep             CHAR(8) NOT NULL,           -- apenas dígitos
    logradouro      VARCHAR(200) NOT NULL,
    numero          VARCHAR(20) NOT NULL,
    complemento     VARCHAR(100),
    bairro          VARCHAR(100) NOT NULL,
    cidade          VARCHAR(100) NOT NULL,
    uf              CHAR(2) NOT NULL,
    ibge_codigo     CHAR(7),                    -- código IBGE do município

    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_uf     CHECK (uf ~ '^[A-Z]{2}$'),
    CONSTRAINT chk_cep    CHECK (cep ~ '^\d{8}$')
);

COMMENT ON TABLE  clientes_enderecos           IS 'Endereços do cliente. Pode ter matriz, filiais, endereço de cobrança, etc.';
COMMENT ON COLUMN clientes_enderecos.principal IS 'Endereço principal para correspondências e documentos fiscais';


-- Garante que cada cliente tenha no máximo um endereço principal por tipo
CREATE UNIQUE INDEX uq_endereco_principal
    ON clientes_enderecos (cliente_id, tipo)
    WHERE principal = TRUE;


-- -------------------------------------------------------------
-- TABELA: clientes_contatos
-- Múltiplos contatos por cliente, com papéis definidos
-- -------------------------------------------------------------
CREATE TABLE clientes_contatos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,

    nome            VARCHAR(200) NOT NULL,
    cargo           VARCHAR(100),
    departamento    VARCHAR(100),
    email           VARCHAR(254),
    telefone        VARCHAR(20),
    whatsapp        VARCHAR(20),
    linkedin        VARCHAR(200),

    -- Papéis (um contato pode ter mais de um)
    is_financeiro   BOOLEAN NOT NULL DEFAULT FALSE,
    is_contrato     BOOLEAN NOT NULL DEFAULT FALSE,
    is_tecnico      BOOLEAN NOT NULL DEFAULT FALSE,
    is_comercial    BOOLEAN NOT NULL DEFAULT FALSE,

    principal       BOOLEAN NOT NULL DEFAULT FALSE,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes     TEXT,

    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_contato_meio CHECK (
        email IS NOT NULL OR telefone IS NOT NULL OR whatsapp IS NOT NULL
    )
);

COMMENT ON TABLE  clientes_contatos             IS 'Contatos do cliente. Cada contato pode acumular múltiplos papéis.';
COMMENT ON COLUMN clientes_contatos.is_financeiro IS 'Recebe cobranças, boletos e avisos de vencimento';
COMMENT ON COLUMN clientes_contatos.is_contrato   IS 'Assina e recebe aditivos contratuais';
COMMENT ON COLUMN clientes_contatos.is_tecnico    IS 'Ponto de contato para suporte e implantação';


-- Garante um único contato principal por cliente
CREATE UNIQUE INDEX uq_contato_principal
    ON clientes_contatos (cliente_id)
    WHERE principal = TRUE;


-- -------------------------------------------------------------
-- TABELA: clientes_historico
-- Auditoria completa de alterações no cadastro do cliente
-- -------------------------------------------------------------
CREATE TABLE clientes_historico (
    id              BIGSERIAL PRIMARY KEY,
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    operacao        CHAR(1) NOT NULL CHECK (operacao IN ('I','U','D')), -- Insert/Update/Delete
    campo_alterado  VARCHAR(100),
    valor_anterior  TEXT,
    valor_novo      TEXT,
    alterado_por    VARCHAR(100) NOT NULL,
    alterado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_origem       INET,
    motivo          TEXT
);

COMMENT ON TABLE  clientes_historico            IS 'Log de auditoria de todas as alterações no cadastro de clientes';
COMMENT ON COLUMN clientes_historico.operacao   IS 'I=Insert, U=Update, D=Delete';


-- -------------------------------------------------------------
-- ÍNDICES DE BUSCA
-- -------------------------------------------------------------

-- Busca por razão social / nome (case-insensitive, sem acento)
CREATE INDEX idx_clientes_razao_social
    ON clientes USING gin (to_tsvector('portuguese', unaccent(COALESCE(razao_social, '') || ' ' || COALESCE(nome_fantasia, ''))));

CREATE INDEX idx_clientes_nome_completo
    ON clientes USING gin (to_tsvector('portuguese', unaccent(COALESCE(nome_completo, ''))));

-- Busca por status e segmento (filtros mais comuns)
CREATE INDEX idx_clientes_status      ON clientes (status);
CREATE INDEX idx_clientes_segmento    ON clientes (segmento_id);
CREATE INDEX idx_clientes_tipo_pessoa ON clientes (tipo_pessoa);

-- Índices nas foreign keys
CREATE INDEX idx_enderecos_cliente_id ON clientes_enderecos (cliente_id);
CREATE INDEX idx_contatos_cliente_id  ON clientes_contatos  (cliente_id);
CREATE INDEX idx_historico_cliente_id ON clientes_historico (cliente_id);
CREATE INDEX idx_historico_alterado_em ON clientes_historico (alterado_em DESC);


-- -------------------------------------------------------------
-- FUNÇÃO: atualiza timestamp automaticamente
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_atualiza_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_clientes_timestamp
    BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE TRIGGER trg_enderecos_timestamp
    BEFORE UPDATE ON clientes_enderecos
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE TRIGGER trg_contatos_timestamp
    BEFORE UPDATE ON clientes_contatos
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();


-- -------------------------------------------------------------
-- FUNÇÃO: impede inativação de cliente com contrato ativo
-- (a trigger completa será adicionada no módulo de contratos)
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_valida_inativacao_cliente()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IN ('INATIVO', 'BLOQUEADO') AND OLD.status = 'ATIVO' THEN
        -- Verificação será implementada quando o módulo de contratos existir.
        -- Por ora, registra o motivo e quem inativou.
        IF NEW.motivo_inativacao IS NULL THEN
            RAISE EXCEPTION 'Informe o motivo da inativação do cliente.';
        END IF;
        NEW.inativado_em  = NOW();
        NEW.inativado_por = NEW.atualizado_por;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_valida_inativacao
    BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION fn_valida_inativacao_cliente();


-- -------------------------------------------------------------
-- DADOS INICIAIS: segmentos padrão
-- -------------------------------------------------------------
INSERT INTO segmentos (nome, descricao) VALUES
    ('Saúde',           'Hospitais, clínicas, laboratórios e operadoras'),
    ('Varejo',          'Comércio físico e e-commerce'),
    ('Indústria',       'Manufatura e transformação'),
    ('Serviços',        'Prestação de serviços em geral'),
    ('Tecnologia',      'Empresas de software, hardware e TI'),
    ('Financeiro',      'Bancos, fintechs e seguradoras'),
    ('Educação',        'Escolas, universidades e edtechs'),
    ('Agronegócio',     'Produção rural, cooperativas e insumos'),
    ('Construção Civil','Construtoras, incorporadoras e imobiliárias'),
    ('Governo',         'Órgãos públicos e autarquias');


-- -------------------------------------------------------------
-- VIEW: clientes_resumo
-- Visão consolidada para listagens e buscas
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_clientes_resumo AS
SELECT
    c.id,
    c.tipo_pessoa,
    COALESCE(c.razao_social, c.nome_completo)   AS nome_principal,
    COALESCE(c.nome_fantasia, '')               AS nome_fantasia,
    COALESCE(c.cnpj, c.cpf)                     AS documento,
    s.nome                                       AS segmento,
    c.porte,
    c.status,
    c.criado_em,
    -- Contato financeiro principal
    (SELECT cc.nome  FROM clientes_contatos cc
     WHERE cc.cliente_id = c.id AND cc.is_financeiro = TRUE AND cc.ativo = TRUE
     LIMIT 1)                                    AS contato_financeiro,
    (SELECT cc.email FROM clientes_contatos cc
     WHERE cc.cliente_id = c.id AND cc.is_financeiro = TRUE AND cc.ativo = TRUE
     LIMIT 1)                                    AS email_financeiro,
    -- Cidade/UF do endereço principal
    (SELECT e.cidade || '/' || e.uf FROM clientes_enderecos e
     WHERE e.cliente_id = c.id AND e.principal = TRUE AND e.ativo = TRUE
     LIMIT 1)                                    AS cidade_uf
FROM clientes c
LEFT JOIN segmentos s ON s.id = c.segmento_id;

COMMENT ON VIEW vw_clientes_resumo IS 'Visão consolidada de clientes para listagens. Não inclui inativos por padrão — filtrar por status conforme necessário.';
