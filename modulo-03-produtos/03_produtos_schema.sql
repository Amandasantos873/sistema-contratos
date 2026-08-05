-- =============================================================
-- SISTEMA DE GESTÃO DE CONTRATOS E FATURAMENTO
-- Módulo 03 — Produtos e Serviços
-- Banco: PostgreSQL 14+
-- Depende dos Módulos 01 e 02
-- =============================================================

-- -------------------------------------------------------------
-- TIPOS ENUMERADOS
-- -------------------------------------------------------------
CREATE TYPE status_produto      AS ENUM ('ATIVO', 'DESCONTINUADO', 'SUSPENSO');
CREATE TYPE tipo_movimentacao   AS ENUM ('CANCELAMENTO', 'SUSPENSAO', 'REATIVACAO', 'SUBSTITUICAO');


-- -------------------------------------------------------------
-- EXPANSÃO DA TABELA produtos_servicos
-- Adiciona campos de controle de ciclo de vida ao catálogo
-- criado no Módulo 02
-- -------------------------------------------------------------
ALTER TABLE produtos_servicos
    ADD COLUMN IF NOT EXISTS status              status_produto NOT NULL DEFAULT 'ATIVO',
    ADD COLUMN IF NOT EXISTS data_descontinuacao DATE,
    ADD COLUMN IF NOT EXISTS motivo_descontinuacao TEXT,
    ADD COLUMN IF NOT EXISTS substituido_por    INTEGER REFERENCES produtos_servicos(id),
    ADD COLUMN IF NOT EXISTS versao             INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS criado_por         VARCHAR(100),
    ADD COLUMN IF NOT EXISTS atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS atualizado_por     VARCHAR(100);

COMMENT ON COLUMN produtos_servicos.status               IS 'ATIVO: disponível | DESCONTINUADO: não pode entrar em novos contratos | SUSPENSO: temporariamente indisponível';
COMMENT ON COLUMN produtos_servicos.substituido_por      IS 'Produto que substitui este quando descontinuado';
COMMENT ON COLUMN produtos_servicos.versao               IS 'Contador de alterações para auditoria';


-- -------------------------------------------------------------
-- TABELA: produtos_pacotes
-- Define os pacotes mínimos por modalidade
-- Cada pacote é um conjunto de produtos que compõem uma oferta base
-- -------------------------------------------------------------
CREATE TABLE produtos_pacotes (
    id          SERIAL PRIMARY KEY,
    modalidade  modalidade_contrato NOT NULL,
    nome        VARCHAR(150) NOT NULL,
    descricao   TEXT,
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por  VARCHAR(100),

    CONSTRAINT uq_pacote_nome_modalidade UNIQUE (modalidade, nome)
);

COMMENT ON TABLE produtos_pacotes IS 'Pacotes mínimos por modalidade. Servem de referência comercial — não são obrigatórios no contrato.';


-- -------------------------------------------------------------
-- TABELA: produtos_pacotes_itens
-- Itens que compõem cada pacote mínimo
-- -------------------------------------------------------------
CREATE TABLE produtos_pacotes_itens (
    id              SERIAL PRIMARY KEY,
    pacote_id       INTEGER NOT NULL REFERENCES produtos_pacotes(id) ON DELETE CASCADE,
    produto_id      INTEGER NOT NULL REFERENCES produtos_servicos(id) ON DELETE RESTRICT,
    quantidade_min  NUMERIC(10,3) NOT NULL DEFAULT 1,
    obrigatorio     BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes     TEXT,

    CONSTRAINT uq_pacote_produto UNIQUE (pacote_id, produto_id)
);

COMMENT ON TABLE  produtos_pacotes_itens              IS 'Composição dos pacotes mínimos';
COMMENT ON COLUMN produtos_pacotes_itens.obrigatorio  IS 'TRUE = item obrigatório no pacote | FALSE = item recomendado';


-- -------------------------------------------------------------
-- TABELA: contratos_itens_movimentacoes
-- Registra cancelamentos, suspensões e substituições de itens
-- dentro de um contrato (aditivo de escopo)
-- -------------------------------------------------------------
CREATE TABLE contratos_itens_movimentacoes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contrato_id         UUID NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    contrato_item_id    UUID NOT NULL REFERENCES contratos_itens(id) ON DELETE CASCADE,
    tipo                tipo_movimentacao NOT NULL,
    data_solicitacao    DATE NOT NULL DEFAULT CURRENT_DATE,
    data_efetivacao     DATE NOT NULL,
    motivo              TEXT NOT NULL,

    -- Para substituição: qual item entrou no lugar
    novo_item_id        UUID REFERENCES contratos_itens(id),

    -- Impacto financeiro
    valor_anterior      NUMERIC(15,2),
    valor_novo          NUMERIC(15,2),

    -- Aditivo gerado
    aditivo_id          UUID REFERENCES contratos_aditivos(id),

    criado_por          VARCHAR(100) NOT NULL,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  contratos_itens_movimentacoes             IS 'Histórico de cancelamentos, suspensões e substituições de itens em contratos';
COMMENT ON COLUMN contratos_itens_movimentacoes.tipo        IS 'CANCELAMENTO: item removido definitivamente | SUSPENSAO: pausa temporária | REATIVACAO: retorno após suspensão | SUBSTITUICAO: troca por outro item';


-- -------------------------------------------------------------
-- ÍNDICES
-- -------------------------------------------------------------
CREATE INDEX idx_produtos_status      ON produtos_servicos (status);
CREATE INDEX idx_produtos_modalidade2 ON produtos_servicos (modalidade, status);
CREATE INDEX idx_pacotes_modalidade   ON produtos_pacotes (modalidade);
CREATE INDEX idx_pacotes_itens_pacote ON produtos_pacotes_itens (pacote_id);
CREATE INDEX idx_movimentacoes_contrato ON contratos_itens_movimentacoes (contrato_id);
CREATE INDEX idx_movimentacoes_item     ON contratos_itens_movimentacoes (contrato_item_id);


-- -------------------------------------------------------------
-- TRIGGER: timestamp e versão do produto
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_atualiza_produto()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    NEW.versao        = OLD.versao + 1;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_produto_timestamp
    BEFORE UPDATE ON produtos_servicos
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_produto();


-- -------------------------------------------------------------
-- FUNÇÃO: impede descontinuação de produto com contratos ativos
-- Avisa (não bloqueia) — decisão final fica na aplicação
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_valida_descontinuacao_produto()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_contratos_ativos INTEGER;
BEGIN
    IF NEW.status = 'DESCONTINUADO' AND OLD.status = 'ATIVO' THEN
        SELECT COUNT(DISTINCT ci.contrato_id) INTO v_contratos_ativos
        FROM contratos_itens ci
        JOIN contratos c ON c.id = ci.contrato_id
        WHERE ci.produto_id = NEW.id
          AND ci.ativo = TRUE
          AND c.status IN ('ATIVO', 'SUSPENSO');

        IF v_contratos_ativos > 0 THEN
            RAISE EXCEPTION
                'Produto possui % contrato(s) ativo(s). Encerre ou substitua o item antes de descontinuar.',
                v_contratos_ativos;
        END IF;

        NEW.data_descontinuacao = CURRENT_DATE;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_valida_descontinuacao
    BEFORE UPDATE ON produtos_servicos
    FOR EACH ROW EXECUTE FUNCTION fn_valida_descontinuacao_produto();


-- -------------------------------------------------------------
-- VIEW: vw_produtos_catalogo
-- Catálogo completo com contagem de uso em contratos ativos
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_produtos_catalogo AS
SELECT
    p.id,
    p.modalidade,
    p.codigo,
    p.nome,
    p.descricao,
    p.unidade,
    p.permite_impl,
    p.permite_recorr,
    p.status,
    p.data_descontinuacao,
    p.versao,
    p.criado_em,
    p.atualizado_em,
    -- Uso em contratos ativos
    COUNT(DISTINCT CASE WHEN c.status IN ('ATIVO','SUSPENSO') AND ci.ativo = TRUE
                        THEN ci.contrato_id END)           AS contratos_ativos,
    -- Valor médio praticado nos contratos ativos
    ROUND(AVG(CASE WHEN c.status IN ('ATIVO','SUSPENSO') AND ci.ativo = TRUE
                   THEN ci.valor_unitario END), 2)         AS valor_medio_praticado,
    -- Produto substituto (se descontinuado)
    ps.nome                                                AS substituto_nome,
    p.substituido_por                                      AS substituto_id
FROM produtos_servicos p
LEFT JOIN contratos_itens ci ON ci.produto_id = p.id
LEFT JOIN contratos c        ON c.id = ci.contrato_id
LEFT JOIN produtos_servicos ps ON ps.id = p.substituido_por
GROUP BY p.id, ps.nome;

COMMENT ON VIEW vw_produtos_catalogo IS 'Catálogo de produtos com métricas de uso em contratos ativos';


-- -------------------------------------------------------------
-- VIEW: vw_produto_contratos_uso
-- Detalhe de uso de um produto específico nos contratos
-- Filtrar por produto_id na aplicação
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW vw_produto_contratos_uso AS
SELECT
    p.id                                                   AS produto_id,
    p.nome                                                 AS produto_nome,
    c.id                                                   AS contrato_id,
    c.numero                                               AS contrato_numero,
    COALESCE(cl.razao_social, cl.nome_completo)            AS cliente_nome,
    c.modalidade,
    c.status                                               AS contrato_status,
    c.fase_atual,
    ci.quantidade,
    ci.valor_unitario,
    ci.desconto_pct,
    ci.valor_total,
    ci.fase                                                AS item_fase,
    ci.ativo                                               AS item_ativo
FROM contratos_itens ci
JOIN produtos_servicos p ON p.id = ci.produto_id
JOIN contratos c         ON c.id = ci.contrato_id
JOIN clientes cl         ON cl.id = c.cliente_id;

COMMENT ON VIEW vw_produto_contratos_uso IS 'Rastreabilidade: mostra todos os contratos que usam um produto específico';
