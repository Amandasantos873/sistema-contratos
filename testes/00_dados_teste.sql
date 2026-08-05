-- =============================================================
-- DADOS DE TESTE — SISTEMA DE GESTÃO DE CONTRATOS E FATURAMENTO
-- Ambiente: desenvolvimento / homologação
-- Cobre todos os módulos 01 a 06
-- Execute APÓS todos os scripts de schema (01 a 06)
-- =============================================================

BEGIN;

-- -------------------------------------------------------------
-- LIMPEZA (ordem inversa das dependências)
-- -------------------------------------------------------------
TRUNCATE TABLE
    faturas_alertas, faturas_validacoes,
    faturas_documentos, faturas_volumetrias, faturas_itens, faturas,
    aviso_previo_cancelamento,
    contratos_reajustes_itens, contratos_reajustes,
    contratos_itens_movimentacoes,
    contratos_parcelas_implantacao, contratos_itens, contratos_aditivos, contratos_historico, contratos,
    clientes_historico, clientes_contatos, clientes_enderecos, clientes,
    faixas_volumetria,
    dissidios_historico
RESTART IDENTITY CASCADE;


-- =============================================================
-- DISSÍDIO ANUAL
-- =============================================================
INSERT INTO dissidios_historico (categoria, ano_base, data_vigencia, valor_percentual, fonte, criado_por) VALUES
    ('GERAL', 2024, '2024-01-01', 4.50, 'Sindicato TI SP - ACT 2024', 'sistema'),
    ('GERAL', 2025, '2025-01-01', 5.20, 'Sindicato TI SP - ACT 2025', 'sistema'),
    ('GERAL', 2026, '2026-01-01', 5.80, 'Sindicato TI SP - ACT 2026', 'sistema');


-- =============================================================
-- CLIENTES (6 clientes — PJ e PF, variados)
-- =============================================================

-- IDs fixos para facilitar referências
DO $$
DECLARE
    id_cliente_1  UUID := 'aaaaaaaa-0001-0001-0001-000000000001';
    id_cliente_2  UUID := 'aaaaaaaa-0002-0002-0002-000000000002';
    id_cliente_3  UUID := 'aaaaaaaa-0003-0003-0003-000000000003';
    id_cliente_4  UUID := 'aaaaaaaa-0004-0004-0004-000000000004';
    id_cliente_5  UUID := 'aaaaaaaa-0005-0005-0005-000000000005';
    id_cliente_6  UUID := 'aaaaaaaa-0006-0006-0006-000000000006';
BEGIN

    -- -------------------------------------------------------
    -- CLIENTE 1: Grande empresa — ASP ativo e em dia
    -- -------------------------------------------------------
    INSERT INTO clientes (id, tipo_pessoa, razao_social, nome_fantasia, cnpj,
        segmento_id, porte, status, origem, criado_por, atualizado_por)
    SELECT 'aaaaaaaa-0001-0001-0001-000000000001', 'PJ',
        'Grupo Horizonte Tecnologia LTDA', 'Horizonte Tech', '11222333000181',
        s.id, 'GRANDE', 'ATIVO', 'Prospecção comercial', 'sistema', 'sistema'
    FROM segmentos s WHERE s.nome = 'Tecnologia';

    INSERT INTO clientes_enderecos (cliente_id, tipo, principal, cep, logradouro, numero, bairro, cidade, uf)
    VALUES ('aaaaaaaa-0001-0001-0001-000000000001', 'MATRIZ', TRUE, '01310100', 'Avenida Paulista', '1000', 'Bela Vista', 'São Paulo', 'SP');

    INSERT INTO clientes_contatos (cliente_id, nome, cargo, email, telefone, is_financeiro, is_contrato, principal)
    VALUES
        ('aaaaaaaa-0001-0001-0001-000000000001', 'Ricardo Almeida',  'CFO',             'ricardo@horizontetech.com.br', '11987650001', TRUE,  TRUE,  TRUE),
        ('aaaaaaaa-0001-0001-0001-000000000001', 'Fernanda Costa',   'Gerente de TI',   'fernanda@horizontetech.com.br','11987650002', FALSE, TRUE,  FALSE),
        ('aaaaaaaa-0001-0001-0001-000000000001', 'Paulo Menezes',    'Analista Técnico', 'paulo@horizontetech.com.br',  '11987650003', FALSE, FALSE, FALSE);

    -- -------------------------------------------------------
    -- CLIENTE 2: Médio porte — BSP com reajuste pendente
    -- -------------------------------------------------------
    INSERT INTO clientes (id, tipo_pessoa, razao_social, nome_fantasia, cnpj,
        segmento_id, porte, status, origem, criado_por, atualizado_por)
    SELECT 'aaaaaaaa-0002-0002-0002-000000000002', 'PJ',
        'Farma Distribuidora Nacional S/A', 'FarmaNacional', '22333444000195',
        s.id, 'MEDIO', 'ATIVO', 'Indicação de parceiro', 'sistema', 'sistema'
    FROM segmentos s WHERE s.nome = 'Saúde';

    INSERT INTO clientes_enderecos (cliente_id, tipo, principal, cep, logradouro, numero, bairro, cidade, uf)
    VALUES ('aaaaaaaa-0002-0002-0002-000000000002', 'MATRIZ', TRUE, '04538133', 'Rua Olimpíadas', '205', 'Itaim Bibi', 'São Paulo', 'SP');

    INSERT INTO clientes_contatos (cliente_id, nome, cargo, email, telefone, is_financeiro, is_contrato, principal)
    VALUES
        ('aaaaaaaa-0002-0002-0002-000000000002', 'Mariana Souza',  'Diretora Financeira', 'mariana@farmanacional.com.br', '11976540001', TRUE,  TRUE,  TRUE),
        ('aaaaaaaa-0002-0002-0002-000000000002', 'Carlos Brito',   'Coord. de Sistemas',  'carlos@farmanacional.com.br',  '11976540002', FALSE, TRUE,  FALSE);

    -- -------------------------------------------------------
    -- CLIENTE 3: BPO — com volumetria de folha
    -- -------------------------------------------------------
    INSERT INTO clientes (id, tipo_pessoa, razao_social, nome_fantasia, cnpj,
        segmento_id, porte, status, origem, criado_por, atualizado_por)
    SELECT 'aaaaaaaa-0003-0003-0003-000000000003', 'PJ',
        'Construtora Vale Verde LTDA', 'Vale Verde', '33444555000108',
        s.id, 'GRANDE', 'ATIVO', 'Evento de setor', 'sistema', 'sistema'
    FROM segmentos s WHERE s.nome = 'Construção Civil';

    INSERT INTO clientes_enderecos (cliente_id, tipo, principal, cep, logradouro, numero, bairro, cidade, uf)
    VALUES ('aaaaaaaa-0003-0003-0003-000000000003', 'MATRIZ', TRUE, '80010020', 'Rua XV de Novembro', '700', 'Centro', 'Curitiba', 'PR');

    INSERT INTO clientes_contatos (cliente_id, nome, cargo, email, telefone, is_financeiro, is_contrato, principal)
    VALUES
        ('aaaaaaaa-0003-0003-0003-000000000003', 'Gustavo Pires',  'Diretor Administrativo', 'gustavo@valeverde.com.br',  '41987650001', TRUE, TRUE,  TRUE),
        ('aaaaaaaa-0003-0003-0003-000000000003', 'Aline Ferreira', 'Analista de RH',         'aline@valeverde.com.br',    '41987650002', FALSE, FALSE, FALSE);

    -- -------------------------------------------------------
    -- CLIENTE 4: Em implantação — ainda não fatura recorrência
    -- -------------------------------------------------------
    INSERT INTO clientes (id, tipo_pessoa, razao_social, nome_fantasia, cnpj,
        segmento_id, porte, status, origem, criado_por, atualizado_por)
    SELECT 'aaaaaaaa-0004-0004-0004-000000000004', 'PJ',
        'Agro Campos Gerais LTDA', 'Campos Gerais', '44555666000161',
        s.id, 'MEDIO', 'ATIVO', 'Site institucional', 'sistema', 'sistema'
    FROM segmentos s WHERE s.nome = 'Agronegócio';

    INSERT INTO clientes_enderecos (cliente_id, tipo, principal, cep, logradouro, numero, bairro, cidade, uf)
    VALUES ('aaaaaaaa-0004-0004-0004-000000000004', 'MATRIZ', TRUE, '84010230', 'Rua Sete de Setembro', '300', 'Centro', 'Ponta Grossa', 'PR');

    INSERT INTO clientes_contatos (cliente_id, nome, cargo, email, telefone, is_financeiro, is_contrato, principal)
    VALUES
        ('aaaaaaaa-0004-0004-0004-000000000004', 'Rodrigo Campos', 'Sócio-Diretor', 'rodrigo@camposgerais.com.br', '42987650001', TRUE, TRUE, TRUE);

    -- -------------------------------------------------------
    -- CLIENTE 5: Contrato quase vencido (alerta VAL005)
    -- -------------------------------------------------------
    INSERT INTO clientes (id, tipo_pessoa, razao_social, nome_fantasia, cnpj,
        segmento_id, porte, status, origem, criado_por, atualizado_por)
    SELECT 'aaaaaaaa-0005-0005-0005-000000000005', 'PJ',
        'Escola Aprender Mais LTDA', 'Aprender Mais', '55666777000172',
        s.id, 'PEQUENO', 'ATIVO', 'Indicação', 'sistema', 'sistema'
    FROM segmentos s WHERE s.nome = 'Educação';

    INSERT INTO clientes_enderecos (cliente_id, tipo, principal, cep, logradouro, numero, bairro, cidade, uf)
    VALUES ('aaaaaaaa-0005-0005-0005-000000000005', 'MATRIZ', TRUE, '30140071', 'Rua da Bahia', '1148', 'Lourdes', 'Belo Horizonte', 'MG');

    INSERT INTO clientes_contatos (cliente_id, nome, cargo, email, telefone, is_financeiro, is_contrato, principal)
    VALUES
        ('aaaaaaaa-0005-0005-0005-000000000005', 'Juliana Martins', 'Diretora Financeira', 'juliana@aprendermais.com.br', '31987650001', TRUE, TRUE, TRUE);

    -- -------------------------------------------------------
    -- CLIENTE 6: Inadimplente (para teste de alertas)
    -- -------------------------------------------------------
    INSERT INTO clientes (id, tipo_pessoa, razao_social, nome_fantasia, cnpj,
        segmento_id, porte, status, origem, observacoes, criado_por, atualizado_por)
    SELECT 'aaaaaaaa-0006-0006-0006-000000000006', 'PJ',
        'Varejo Conectado LTDA', 'ConectaShop', '66777888000183',
        s.id, 'PEQUENO', 'ATIVO', 'Evento de setor',
        'Cliente com histórico de atraso nos pagamentos.',
        'sistema', 'sistema'
    FROM segmentos s WHERE s.nome = 'Varejo';

    INSERT INTO clientes_enderecos (cliente_id, tipo, principal, cep, logradouro, numero, bairro, cidade, uf)
    VALUES ('aaaaaaaa-0006-0006-0006-000000000006', 'MATRIZ', TRUE, '88010400', 'Rua Felipe Schmidt', '500', 'Centro', 'Florianópolis', 'SC');

    INSERT INTO clientes_contatos (cliente_id, nome, cargo, email, telefone, is_financeiro, is_contrato, principal)
    VALUES
        ('aaaaaaaa-0006-0006-0006-000000000006', 'Tiago Oliveira', 'Sócio', 'tiago@conectashop.com.br', '48987650001', TRUE, TRUE, TRUE);

END $$;


-- =============================================================
-- CONTRATOS (7 contratos cobrindo todos os cenários)
-- =============================================================

DO $$
DECLARE
    -- Contratos
    id_ctr_1  UUID := 'cccccccc-0001-0001-0001-000000000001';  -- ASP ativo, recorrência, dia 25
    id_ctr_2  UUID := 'cccccccc-0002-0002-0002-000000000002';  -- BSP ativo, recorrência, dia 15
    id_ctr_3  UUID := 'cccccccc-0003-0003-0003-000000000003';  -- BPO ativo, volumetria, dia 25
    id_ctr_4  UUID := 'cccccccc-0004-0004-0004-000000000004';  -- ASP em implantação
    id_ctr_5  UUID := 'cccccccc-0005-0005-0005-000000000005';  -- ASP quase vencido
    id_ctr_6  UUID := 'cccccccc-0006-0006-0006-000000000006';  -- BSP inadimplente
    id_ctr_7  UUID := 'cccccccc-0007-0007-0007-000000000007';  -- ASP 2º contrato cliente 1

    -- Itens de contratos
    id_item_ctr1_a UUID := 'eeeeeeee-0001-0001-0001-000000000001';
    id_item_ctr1_b UUID := 'eeeeeeee-0001-0001-0001-000000000002';
    id_item_ctr1_c UUID := 'eeeeeeee-0001-0001-0001-000000000003';
    id_item_ctr2_a UUID := 'eeeeeeee-0002-0002-0002-000000000001';
    id_item_ctr2_b UUID := 'eeeeeeee-0002-0002-0002-000000000002';
    id_item_ctr3_a UUID := 'eeeeeeee-0003-0003-0003-000000000001';
    id_item_ctr3_b UUID := 'eeeeeeee-0003-0003-0003-000000000002';
    id_item_ctr3_c UUID := 'eeeeeeee-0003-0003-0003-000000000003';  -- MOA (dissídio)
    id_item_ctr4_a UUID := 'eeeeeeee-0004-0004-0004-000000000001';
    id_item_ctr4_b UUID := 'eeeeeeee-0004-0004-0004-000000000002';
    id_item_ctr5_a UUID := 'eeeeeeee-0005-0005-0005-000000000001';
    id_item_ctr6_a UUID := 'eeeeeeee-0006-0006-0006-000000000001';
    id_item_ctr7_a UUID := 'eeeeeeee-0007-0007-0007-000000000001';

    -- Produtos
    pid_asp_lic_base    INTEGER;
    pid_asp_lic_usuario INTEGER;
    pid_asp_suporte     INTEGER;
    pid_bsp_fee_mensal  INTEGER;
    pid_bsp_transacao   INTEGER;
    pid_bsp_suporte     INTEGER;
    pid_bpo_gestao      INTEGER;
    pid_bpo_hora_tec    INTEGER;
    pid_bpo_relatorio   INTEGER;
BEGIN

    -- Busca IDs dos produtos
    SELECT id INTO pid_asp_lic_base    FROM produtos_servicos WHERE codigo = 'ASP-LIC-BASE';
    SELECT id INTO pid_asp_lic_usuario FROM produtos_servicos WHERE codigo = 'ASP-LIC-USUARIO';
    SELECT id INTO pid_asp_suporte     FROM produtos_servicos WHERE codigo = 'ASP-SUPORTE';
    SELECT id INTO pid_bsp_fee_mensal  FROM produtos_servicos WHERE codigo = 'BSP-OPER-MENSAL';
    SELECT id INTO pid_bsp_transacao   FROM produtos_servicos WHERE codigo = 'BSP-TRANSACAO';
    SELECT id INTO pid_bsp_suporte     FROM produtos_servicos WHERE codigo = 'BSP-SUPORTE';
    SELECT id INTO pid_bpo_gestao      FROM produtos_servicos WHERE codigo = 'BPO-GESTAO-MENSAL';
    SELECT id INTO pid_bpo_hora_tec    FROM produtos_servicos WHERE codigo = 'BPO-HORA-TECNICA';
    SELECT id INTO pid_bpo_relatorio   FROM produtos_servicos WHERE codigo = 'BPO-RELATORIO';

    -- Marca item de mão de obra alocada
    UPDATE produtos_servicos SET mao_de_obra_alocada = TRUE WHERE codigo IN ('BPO-HORA-TECNICA');

    -- =====================================================
    -- CONTRATO 1: Horizonte Tech — ASP, ativo, dia 25
    -- Go-live: 2024-03-01 | Recorrência desde 2024-03-01
    -- =====================================================
    INSERT INTO contratos (id, numero, cliente_id, modalidade, data_assinatura,
        data_inicio_impl, data_goLive, data_inicio_recorrencia,
        prazo_meses, data_fim_contrato, dia_faturamento, fase_atual, status,
        responsavel_comercial, responsavel_implantacao, criado_por, atualizado_por)
    VALUES (id_ctr_1, 'CTR-2024-0001', 'aaaaaaaa-0001-0001-0001-000000000001', 'ASP',
        '2024-01-15', '2024-01-20', '2024-03-01', '2024-03-01',
        24, '2026-03-01', 'DIA_25', 'RECORRENCIA', 'ATIVO',
        'Ana Comercial', 'Bruno Implantação', 'sistema', 'sistema');

    INSERT INTO contratos_itens (id, contrato_id, produto_id, quantidade, valor_unitario, desconto_pct, fase, status_item, data_goLive_item, data_inicio_faturamento, goLive_confirmado_por)
    VALUES
        (id_item_ctr1_a, id_ctr_1, pid_asp_lic_base,    1,    4500.00, 0,   'RECORRENCIA', 'ATIVO', '2024-03-01', '2024-03-01', 'Bruno Implantação'),
        (id_item_ctr1_b, id_ctr_1, pid_asp_lic_usuario, 15,    180.00, 5,   'RECORRENCIA', 'ATIVO', '2024-03-01', '2024-03-01', 'Bruno Implantação'),
        (id_item_ctr1_c, id_ctr_1, pid_asp_suporte,     1,   1200.00, 0,   'RECORRENCIA', 'ATIVO', '2024-03-15', '2024-03-15', 'Bruno Implantação');

    -- Parcelas de implantação (já pagas)
    INSERT INTO contratos_parcelas_implantacao (contrato_id, numero_parcela, valor, data_vencimento, status, data_faturamento, data_pagamento)
    VALUES
        (id_ctr_1, 1, 8000.00, '2024-02-15', 'PAGA', '2024-02-10', '2024-02-16'),
        (id_ctr_1, 2, 8000.00, '2024-03-15', 'PAGA', '2024-03-10', '2024-03-17');

    -- =====================================================
    -- CONTRATO 2: FarmaNacional — BSP, ativo, dia 15
    -- Com reajuste já aplicado
    -- =====================================================
    INSERT INTO contratos (id, numero, cliente_id, modalidade, data_assinatura,
        data_inicio_impl, data_goLive, data_inicio_recorrencia,
        prazo_meses, data_fim_contrato, dia_faturamento, fase_atual, status,
        responsavel_comercial, criado_por, atualizado_por)
    VALUES (id_ctr_2, 'CTR-2024-0002', 'aaaaaaaa-0002-0002-0002-000000000002', 'BSP',
        '2024-02-01', '2024-02-05', '2024-04-01', '2024-04-01',
        24, '2026-04-01', 'DIA_15', 'RECORRENCIA', 'ATIVO',
        'Ana Comercial', 'sistema', 'sistema');

    INSERT INTO contratos_itens (id, contrato_id, produto_id, quantidade, valor_unitario, desconto_pct, fase, status_item, data_goLive_item, data_inicio_faturamento, goLive_confirmado_por)
    VALUES
        (id_item_ctr2_a, id_ctr_2, pid_bsp_fee_mensal, 1, 6800.00, 0, 'RECORRENCIA', 'ATIVO', '2024-04-01', '2024-04-01', 'Bruno Implantação'),
        (id_item_ctr2_b, id_ctr_2, pid_bsp_suporte,    1, 1500.00, 0, 'RECORRENCIA', 'ATIVO', '2024-04-01', '2024-04-01', 'Bruno Implantação');

    INSERT INTO contratos_parcelas_implantacao (contrato_id, numero_parcela, valor, data_vencimento, status, data_faturamento, data_pagamento)
    VALUES
        (id_ctr_2, 1, 5000.00, '2024-03-01', 'PAGA', '2024-02-25', '2024-03-05'),
        (id_ctr_2, 2, 5000.00, '2024-04-01', 'PAGA', '2024-03-25', '2024-04-03');

    -- Reajuste aplicado (INPC 2024 → 2025, acumulado ~4.7%)
    INSERT INTO contratos_reajustes (
        contrato_id, numero_reajuste, indice,
        data_base, data_fim_periodo, competencia_inicial, competencia_final,
        percentual_calculado, percentual_aplicado,
        valor_mensal_anterior, valor_mensal_novo, variacao_mensal,
        status, data_efetivacao,
        calculado_por, aprovado_por, data_aprovacao
    ) VALUES (
        id_ctr_2, 1, 'INPC',
        '2024-02-01', '2025-02-01', '2024-02-01', '2025-01-01',
        4.7200, 4.5000,
        8300.00, 8673.50, 373.50,
        'EFETIVADO', '2025-04-01',
        'sistema', 'Ana Gestora', NOW() - INTERVAL '6 months'
    );

    UPDATE contratos_itens SET valor_unitario = valor_unitario * 1.045 WHERE contrato_id = id_ctr_2;
    UPDATE contratos SET valor_mensal = 8673.50 WHERE id = id_ctr_2;

    -- =====================================================
    -- CONTRATO 3: Vale Verde — BPO, ativo, dia 25, volumetria
    -- =====================================================
    INSERT INTO contratos (id, numero, cliente_id, modalidade, data_assinatura,
        data_inicio_impl, data_goLive, data_inicio_recorrencia,
        prazo_meses, data_fim_contrato, dia_faturamento, fase_atual, status,
        responsavel_comercial, criado_por, atualizado_por)
    VALUES (id_ctr_3, 'CTR-2024-0003', 'aaaaaaaa-0003-0003-0003-000000000003', 'BPO',
        '2024-03-01', '2024-03-10', '2024-06-01', '2024-06-01',
        36, '2027-06-01', 'DIA_25', 'RECORRENCIA', 'ATIVO',
        'Carlos Comercial', 'sistema', 'sistema');

    INSERT INTO contratos_itens (id, contrato_id, produto_id, quantidade, valor_unitario, desconto_pct, fase, status_item, data_goLive_item, data_inicio_faturamento, goLive_confirmado_por)
    VALUES
        (id_item_ctr3_a, id_ctr_3, pid_bpo_gestao,    1, 12000.00, 0, 'RECORRENCIA', 'ATIVO', '2024-06-01', '2024-06-01', 'sistema'),
        (id_item_ctr3_b, id_ctr_3, pid_bpo_relatorio, 1,  2000.00, 0, 'RECORRENCIA', 'ATIVO', '2024-06-01', '2024-06-01', 'sistema'),
        (id_item_ctr3_c, id_ctr_3, pid_bpo_hora_tec,  1,  3500.00, 0, 'RECORRENCIA', 'ATIVO', '2024-06-01', '2024-06-01', 'sistema');
        -- id_item_ctr3_c = mão de obra alocada (reajuste por dissídio)

    INSERT INTO contratos_parcelas_implantacao (contrato_id, numero_parcela, valor, data_vencimento, status, data_faturamento, data_pagamento)
    VALUES
        (id_ctr_3, 1, 15000.00, '2024-04-15', 'PAGA', '2024-04-10', '2024-04-18'),
        (id_ctr_3, 2, 15000.00, '2024-05-15', 'PAGA', '2024-05-10', '2024-05-16'),
        (id_ctr_3, 3, 10000.00, '2024-06-15', 'PAGA', '2024-06-10', '2024-06-20');

    -- Faixas de volumetria para o produto BPO-HORA-TECNICA
    INSERT INTO faixas_volumetria (produto_id, tipo_vinculo, faixa_de, faixa_ate, valor_unitario, vigencia_inicio) VALUES
        (pid_bpo_hora_tec, 'CLT',        0,   50,  85.00, '2024-01-01'),
        (pid_bpo_hora_tec, 'CLT',       51,  100,  78.00, '2024-01-01'),
        (pid_bpo_hora_tec, 'CLT',      101, NULL,  70.00, '2024-01-01'),
        (pid_bpo_hora_tec, 'AUTONOMO',   0,   20,  65.00, '2024-01-01'),
        (pid_bpo_hora_tec, 'AUTONOMO',  21, NULL,  58.00, '2024-01-01'),
        (pid_bpo_hora_tec, 'ESTAGIARIO', 0, NULL,  40.00, '2024-01-01');

    -- Faixas para fee mensal BSP (transações)
    INSERT INTO faixas_volumetria (produto_id, tipo_vinculo, faixa_de, faixa_ate, valor_unitario, vigencia_inicio) VALUES
        (pid_bsp_transacao, 'OUTROS',    0, 1000, 1.20, '2024-01-01'),
        (pid_bsp_transacao, 'OUTROS', 1001, 5000, 0.95, '2024-01-01'),
        (pid_bsp_transacao, 'OUTROS', 5001, NULL, 0.75, '2024-01-01');

    -- =====================================================
    -- CONTRATO 4: Campos Gerais — ASP, em implantação
    -- Itens com go-live parcial (cenário VAL002)
    -- =====================================================
    INSERT INTO contratos (id, numero, cliente_id, modalidade, data_assinatura,
        data_inicio_impl, prazo_meses, dia_faturamento, fase_atual, status,
        responsavel_comercial, criado_por, atualizado_por)
    VALUES (id_ctr_4, 'CTR-2025-0001', 'aaaaaaaa-0004-0004-0004-000000000004', 'ASP',
        '2025-10-01', '2025-10-10', 24, 'DIA_25', 'IMPLANTACAO', 'ATIVO',
        'Carlos Comercial', 'sistema', 'sistema');

    INSERT INTO contratos_itens (id, contrato_id, produto_id, quantidade, valor_unitario, desconto_pct, fase, status_item)
    VALUES
        (id_item_ctr4_a, id_ctr_4, pid_asp_lic_base,    1, 3200.00, 5, 'RECORRENCIA', 'IMPLANTACAO'),
        (id_item_ctr4_b, id_ctr_4, pid_asp_lic_usuario, 8,  160.00, 0, 'RECORRENCIA', 'IMPLANTACAO');

    INSERT INTO contratos_parcelas_implantacao (contrato_id, numero_parcela, valor, data_vencimento, status)
    VALUES
        (id_ctr_4, 1, 4500.00, '2025-11-15', 'PAGA'),
        (id_ctr_4, 2, 4500.00, '2026-01-15', 'PENDENTE');

    -- =====================================================
    -- CONTRATO 5: Aprender Mais — ASP, quase vencido
    -- Vence em 30 dias (alerta VAL005 nos próximos ciclos)
    -- =====================================================
    INSERT INTO contratos (id, numero, cliente_id, modalidade, data_assinatura,
        data_inicio_impl, data_goLive, data_inicio_recorrencia,
        prazo_meses, data_fim_contrato, dia_faturamento, fase_atual, status,
        responsavel_comercial, criado_por, atualizado_por)
    VALUES (id_ctr_5, 'CTR-2024-0004', 'aaaaaaaa-0005-0005-0005-000000000005', 'ASP',
        '2024-07-01', '2024-07-05', '2024-08-01', '2024-08-01',
        24, (CURRENT_DATE + INTERVAL '25 days')::DATE,   -- vence daqui a 25 dias!
        'DIA_01', 'RECORRENCIA', 'ATIVO',
        'Ana Comercial', 'sistema', 'sistema');

    INSERT INTO contratos_itens (id, contrato_id, produto_id, quantidade, valor_unitario, desconto_pct, fase, status_item, data_goLive_item, data_inicio_faturamento, goLive_confirmado_por)
    VALUES
        (id_item_ctr5_a, id_ctr_5, pid_asp_lic_base, 1, 2800.00, 0, 'RECORRENCIA', 'ATIVO', '2024-08-01', '2024-08-01', 'sistema');

    -- =====================================================
    -- CONTRATO 6: ConectaShop — BSP, fatura em atraso (inadimplência)
    -- =====================================================
    INSERT INTO contratos (id, numero, cliente_id, modalidade, data_assinatura,
        data_inicio_impl, data_goLive, data_inicio_recorrencia,
        prazo_meses, data_fim_contrato, dia_faturamento, fase_atual, status,
        responsavel_comercial, criado_por, atualizado_por)
    VALUES (id_ctr_6, 'CTR-2024-0005', 'aaaaaaaa-0006-0006-0006-000000000006', 'BSP',
        '2024-09-01', '2024-09-05', '2024-10-01', '2024-10-01',
        12, '2025-10-01', 'DIA_15', 'RECORRENCIA', 'ATIVO',
        'Carlos Comercial', 'sistema', 'sistema');

    INSERT INTO contratos_itens (id, contrato_id, produto_id, quantidade, valor_unitario, desconto_pct, fase, status_item, data_goLive_item, data_inicio_faturamento, goLive_confirmado_por)
    VALUES
        (id_item_ctr6_a, id_ctr_6, pid_bsp_fee_mensal, 1, 3900.00, 10, 'RECORRENCIA', 'ATIVO', '2024-10-01', '2024-10-01', 'sistema');

    -- =====================================================
    -- CONTRATO 7: Horizonte Tech — 2º contrato ASP (dia 01)
    -- Para mostrar que um cliente pode ter múltiplos contratos
    -- =====================================================
    INSERT INTO contratos (id, numero, cliente_id, modalidade, data_assinatura,
        data_inicio_impl, data_goLive, data_inicio_recorrencia,
        prazo_meses, data_fim_contrato, dia_faturamento, fase_atual, status,
        responsavel_comercial, criado_por, atualizado_por)
    VALUES (id_ctr_7, 'CTR-2025-0002', 'aaaaaaaa-0001-0001-0001-000000000001', 'ASP',
        '2025-06-01', '2025-06-10', '2025-08-01', '2025-08-01',
        12, '2026-08-01', 'DIA_01', 'RECORRENCIA', 'ATIVO',
        'Ana Comercial', 'sistema', 'sistema');

    INSERT INTO contratos_itens (id, contrato_id, produto_id, quantidade, valor_unitario, desconto_pct, fase, status_item, data_goLive_item, data_inicio_faturamento, goLive_confirmado_por)
    VALUES
        (id_item_ctr7_a, id_ctr_7, pid_asp_suporte, 1, 1800.00, 0, 'RECORRENCIA', 'ATIVO', '2025-08-01', '2025-08-01', 'sistema');

END $$;


-- =============================================================
-- FATURAS (competência maio/2026 — cenário de testes)
-- =============================================================

DO $$
DECLARE
    id_fat_1  UUID := 'ffffffff-0001-0001-0001-000000000001';  -- CTR-0001, dia 25, OK
    id_fat_2  UUID := 'ffffffff-0002-0002-0002-000000000002';  -- CTR-0002, dia 15, OK
    id_fat_3  UUID := 'ffffffff-0003-0003-0003-000000000003';  -- CTR-0003, BPO c/ volumetria
    id_fat_4  UUID := 'ffffffff-0004-0004-0004-000000000004';  -- CTR-0005, dia 01
    id_fat_5  UUID := 'ffffffff-0005-0005-0005-000000000005';  -- CTR-0006, INADIMPLENTE
    id_fat_6  UUID := 'ffffffff-0006-0006-0006-000000000006';  -- CTR-0001 valor ERRADO (VAL001)

    pid_asp_lic_base    INTEGER;
    pid_asp_lic_usuario INTEGER;
    pid_asp_suporte     INTEGER;
    pid_bsp_fee_mensal  INTEGER;
    pid_bsp_suporte     INTEGER;
    pid_bpo_gestao      INTEGER;
    pid_bpo_relatorio   INTEGER;
    pid_bpo_hora_tec    INTEGER;
BEGIN
    SELECT id INTO pid_asp_lic_base    FROM produtos_servicos WHERE codigo = 'ASP-LIC-BASE';
    SELECT id INTO pid_asp_lic_usuario FROM produtos_servicos WHERE codigo = 'ASP-LIC-USUARIO';
    SELECT id INTO pid_asp_suporte     FROM produtos_servicos WHERE codigo = 'ASP-SUPORTE';
    SELECT id INTO pid_bsp_fee_mensal  FROM produtos_servicos WHERE codigo = 'BSP-OPER-MENSAL';
    SELECT id INTO pid_bsp_suporte     FROM produtos_servicos WHERE codigo = 'BSP-SUPORTE';
    SELECT id INTO pid_bpo_gestao      FROM produtos_servicos WHERE codigo = 'BPO-GESTAO-MENSAL';
    SELECT id INTO pid_bpo_relatorio   FROM produtos_servicos WHERE codigo = 'BPO-RELATORIO';
    SELECT id INTO pid_bpo_hora_tec    FROM produtos_servicos WHERE codigo = 'BPO-HORA-TECNICA';

    -- FAT-1: CTR-0001 (Horizonte Tech ASP) — correta, paga
    INSERT INTO faturas (id, contrato_id, numero_fatura, competencia, dia_apuracao,
        data_apuracao, data_vencimento, status, numero_nf, data_emissao_nf,
        valor_pago, data_pagamento, descricao_nf, criado_por, atualizado_por)
    VALUES (id_fat_1, 'cccccccc-0001-0001-0001-000000000001',
        'FAT-2026-00001', '2026-05-01', 'DIA_25', '2026-05-25', '2026-06-10',
        'PAGA', '202605001', '2026-05-25', 8471.00, '2026-06-08',
        'Prestação de Serviços Conforme Contrato ASP competência 05/2026 — Valor Total R$ 8.471,00',
        'sistema', 'sistema');

    INSERT INTO faturas_itens (fatura_id, contrato_item_id, produto_id, descricao, quantidade, valor_unitario, desconto_pct, eh_volumetria)
    VALUES
        (id_fat_1, 'eeeeeeee-0001-0001-0001-000000000001', pid_asp_lic_base,    'Licença base do sistema', 1,    4500.00, 0,  FALSE),
        (id_fat_1, 'eeeeeeee-0001-0001-0001-000000000002', pid_asp_lic_usuario, 'Licença por usuário',     15,    171.00, 5,  FALSE),
        (id_fat_1, 'eeeeeeee-0001-0001-0001-000000000003', pid_asp_suporte,     'Suporte técnico',         1,    1200.00, 0,  FALSE);

    -- FAT-2: CTR-0002 (FarmaNacional BSP) — correta, emitida
    INSERT INTO faturas (id, contrato_id, numero_fatura, competencia, dia_apuracao,
        data_apuracao, data_vencimento, status, numero_nf, data_emissao_nf,
        descricao_nf, criado_por, atualizado_por)
    VALUES (id_fat_2, 'cccccccc-0002-0002-0002-000000000002',
        'FAT-2026-00002', '2026-05-01', 'DIA_15', '2026-05-15', '2026-05-30',
        'EMITIDA', '202605002', '2026-05-15',
        'Prestação de Serviços Conforme Contrato BSP competência 05/2026 — Valor Total R$ 8.673,50',
        'sistema', 'sistema');

    INSERT INTO faturas_itens (fatura_id, contrato_item_id, produto_id, descricao, quantidade, valor_unitario, desconto_pct, eh_volumetria)
    VALUES
        (id_fat_2, 'eeeeeeee-0002-0002-0002-000000000001', pid_bsp_fee_mensal, 'Fee de operação mensal', 1, 7106.00, 0, FALSE),
        (id_fat_2, 'eeeeeeee-0002-0002-0002-000000000002', pid_bsp_suporte,    'Suporte e monitoramento',1, 1567.50, 0, FALSE);

    -- FAT-3: CTR-0003 (Vale Verde BPO) — com volumetria
    INSERT INTO faturas (id, contrato_id, numero_fatura, competencia, dia_apuracao,
        data_apuracao, data_vencimento, status,
        descricao_nf, criado_por, atualizado_por)
    VALUES (id_fat_3, 'cccccccc-0003-0003-0003-000000000003',
        'FAT-2026-00003', '2026-05-01', 'DIA_25', '2026-05-25', '2026-06-10',
        'APURADA',
        'Prestação de Serviços Conforme Contrato BPO competência 05/2026 — Valor Total R$ X',
        'sistema', 'sistema');

    INSERT INTO faturas_itens (fatura_id, contrato_item_id, produto_id, descricao, quantidade, valor_unitario, desconto_pct, eh_volumetria)
    VALUES
        (id_fat_3, 'eeeeeeee-0003-0003-0003-000000000001', pid_bpo_gestao,    'Gestão do processo terceirizado', 1, 12000.00, 0, FALSE),
        (id_fat_3, 'eeeeeeee-0003-0003-0003-000000000002', pid_bpo_relatorio, 'Relatórios e dashboards',         1,  2000.00, 0, FALSE),
        -- Mão de obra (volumetria)
        (id_fat_3, 'eeeeeeee-0003-0003-0003-000000000003', pid_bpo_hora_tec,  'Folha de Pagamento — CLT',        72,   78.00, 0, TRUE),
        (id_fat_3, 'eeeeeeee-0003-0003-0003-000000000003', pid_bpo_hora_tec,  'Folha de Pagamento — Estagiário', 8,    40.00, 0, TRUE);

    INSERT INTO faturas_volumetrias (fatura_id, contrato_item_id, tipo_vinculo, quantidade, valor_unitario, fonte, competencia_folha)
    VALUES
        (id_fat_3, 'eeeeeeee-0003-0003-0003-000000000003', 'CLT',        72, 78.00, 'INTEGRACAO_FOLHA', '2026-05-01'),
        (id_fat_3, 'eeeeeeee-0003-0003-0003-000000000003', 'ESTAGIARIO',  8, 40.00, 'INTEGRACAO_FOLHA', '2026-05-01');

    -- FAT-4: CTR-0005 (Aprender Mais) — dia 01, enviada
    INSERT INTO faturas (id, contrato_id, numero_fatura, competencia, dia_apuracao,
        data_apuracao, data_vencimento, status, numero_nf, data_emissao_nf,
        descricao_nf, criado_por, atualizado_por)
    VALUES (id_fat_4, 'cccccccc-0005-0005-0005-000000000005',
        'FAT-2026-00004', '2026-05-01', 'DIA_01', '2026-05-02', '2026-05-20',
        'ENVIADA', '202605004', '2026-05-02',
        'Prestação de Serviços Conforme Contrato ASP competência 05/2026 — Valor Total R$ 2.800,00',
        'sistema', 'sistema');

    INSERT INTO faturas_itens (fatura_id, contrato_item_id, produto_id, descricao, quantidade, valor_unitario, desconto_pct, eh_volumetria)
    VALUES (id_fat_4, 'eeeeeeee-0005-0005-0005-000000000001', pid_asp_lic_base, 'Licença base do sistema', 1, 2800.00, 0, FALSE);

    -- FAT-5: CTR-0006 (ConectaShop) — INADIMPLENTE, vencida há 45 dias
    INSERT INTO faturas (id, contrato_id, numero_fatura, competencia, dia_apuracao,
        data_apuracao, data_vencimento, status,
        descricao_nf, criado_por, atualizado_por)
    VALUES (id_fat_5, 'cccccccc-0006-0006-0006-000000000006',
        'FAT-2026-00005', '2026-04-01', 'DIA_15', '2026-04-15',
        (CURRENT_DATE - INTERVAL '45 days')::DATE,   -- vencida há 45 dias!
        'INADIMPLENTE',
        'Prestação de Serviços Conforme Contrato BSP competência 04/2026 — Valor Total R$ 3.510,00',
        'sistema', 'sistema');

    INSERT INTO faturas_itens (fatura_id, contrato_item_id, produto_id, descricao, quantidade, valor_unitario, desconto_pct, eh_volumetria)
    VALUES (id_fat_5, 'eeeeeeee-0006-0006-0006-000000000001', pid_bsp_fee_mensal, 'Fee de operação mensal', 1, 3510.00, 10, FALSE);

    -- FAT-6: CTR-0001 com VALOR ERRADO (para disparar VAL001 nos testes)
    INSERT INTO faturas (id, contrato_id, numero_fatura, competencia, dia_apuracao,
        data_apuracao, data_vencimento, status,
        descricao_nf, criado_por, atualizado_por)
    VALUES (id_fat_6, 'cccccccc-0001-0001-0001-000000000001',
        'FAT-2026-00006', '2026-06-01', 'DIA_25', '2026-06-25', '2026-07-10',
        'APURADA',
        'Prestação de Serviços Conforme Contrato ASP competência 06/2026',
        'sistema', 'sistema');

    INSERT INTO faturas_itens (fatura_id, contrato_item_id, produto_id, descricao, quantidade, valor_unitario, desconto_pct, eh_volumetria)
    VALUES
        (id_fat_6, 'eeeeeeee-0001-0001-0001-000000000001', pid_asp_lic_base,    'Licença base do sistema', 1,    5200.00, 0,  FALSE),  -- ERRADO: deveria ser 4500
        (id_fat_6, 'eeeeeeee-0001-0001-0001-000000000002', pid_asp_lic_usuario, 'Licença por usuário',     15,    171.00, 5,  FALSE),
        (id_fat_6, 'eeeeeeee-0001-0001-0001-000000000003', pid_asp_suporte,     'Suporte técnico',         1,    1200.00, 0,  FALSE);

END $$;


-- =============================================================
-- AVISO PRÉVIO DE CANCELAMENTO
-- Item de suporte do CTR-0001 com aviso prévio vencido (VAL008)
-- =============================================================

INSERT INTO aviso_previo_cancelamento
    (contrato_item_id, data_solicitacao, prazo_vigencia_dias, data_fim_vigencia, motivo, status, criado_por)
VALUES (
    'eeeeeeee-0001-0001-0001-000000000003',  -- ASP-SUPORTE do CTR-0001
    (CURRENT_DATE - INTERVAL '45 days')::DATE,
    30,
    (CURRENT_DATE - INTERVAL '15 days')::DATE,   -- prazo venceu há 15 dias!
    'Cliente solicitou cancelamento do suporte técnico por redução de escopo.',
    'ATIVO',
    'sistema'
);


-- =============================================================
-- VERIFICAÇÃO FINAL
-- =============================================================

SELECT '=== CLIENTES ===' AS tabela, COUNT(*) AS registros FROM clientes
UNION ALL SELECT '=== CONTRATOS ===', COUNT(*) FROM contratos
UNION ALL SELECT '=== ITENS DE CONTRATO ===', COUNT(*) FROM contratos_itens
UNION ALL SELECT '=== PARCELAS IMPLANTAÇÃO ===', COUNT(*) FROM contratos_parcelas_implantacao
UNION ALL SELECT '=== FATURAS ===', COUNT(*) FROM faturas
UNION ALL SELECT '=== ITENS DE FATURA ===', COUNT(*) FROM faturas_itens
UNION ALL SELECT '=== VOLUMETRIAS ===', COUNT(*) FROM faturas_volumetrias
UNION ALL SELECT '=== FAIXAS VOLUMETRIA ===', COUNT(*) FROM faixas_volumetria
UNION ALL SELECT '=== DISSÍDIOS ===', COUNT(*) FROM dissidios_historico
UNION ALL SELECT '=== AVISOS PRÉVIOS ===', COUNT(*) FROM aviso_previo_cancelamento;

COMMIT;
