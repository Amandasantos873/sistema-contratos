# Guia de Testes — Sistema de Gestão de Contratos e Faturamento

## Como executar

```bash
# 1. Execute os schemas na ordem
psql -d contratos_db -f 01_clientes_schema.sql
psql -d contratos_db -f 02_contratos_schema.sql
psql -d contratos_db -f 02b_goLive_por_item.sql
psql -d contratos_db -f 03_produtos_schema.sql
psql -d contratos_db -f 04_reajustes_schema.sql
psql -d contratos_db -f 05_faturamento_schema.sql
psql -d contratos_db -f 06_validacao_schema.sql

# 2. Carregue os dados de teste
psql -d contratos_db -f testes/00_dados_teste.sql
```

---

## Clientes cadastrados

| ID (sufixo) | Razão Social | Segmento | Porte | Status |
|-------------|-------------|----------|-------|--------|
| `...0001` | Grupo Horizonte Tecnologia LTDA | Tecnologia | Grande | Ativo |
| `...0002` | Farma Distribuidora Nacional S/A | Saúde | Médio | Ativo |
| `...0003` | Construtora Vale Verde LTDA | Construção | Grande | Ativo |
| `...0004` | Agro Campos Gerais LTDA | Agronegócio | Médio | Ativo |
| `...0005` | Escola Aprender Mais LTDA | Educação | Pequeno | Ativo |
| `...0006` | Varejo Conectado LTDA | Varejo | Pequeno | Ativo |

**IDs completos:**
```
aaaaaaaa-0001-0001-0001-000000000001  (Horizonte Tech)
aaaaaaaa-0002-0002-0002-000000000002  (FarmaNacional)
aaaaaaaa-0003-0003-0003-000000000003  (Vale Verde)
aaaaaaaa-0004-0004-0004-000000000004  (Campos Gerais)
aaaaaaaa-0005-0005-0005-000000000005  (Aprender Mais)
aaaaaaaa-0006-0006-0006-000000000006  (ConectaShop)
```

---

## Contratos cadastrados

| Número | Cliente | Modalidade | Fase | Dia Fat. | Status | Cenário |
|--------|---------|------------|------|----------|--------|---------|
| CTR-2024-0001 | Horizonte Tech | ASP | Recorrência | DIA_25 | Ativo | ✅ Normal, 2 contratos no cliente |
| CTR-2024-0002 | FarmaNacional | BSP | Recorrência | DIA_15 | Ativo | ✅ Com reajuste INPC aplicado |
| CTR-2024-0003 | Vale Verde | BPO | Recorrência | DIA_25 | Ativo | ✅ Com volumetria de folha |
| CTR-2025-0001 | Campos Gerais | ASP | Implantação | DIA_25 | Ativo | 🔧 Go-live pendente |
| CTR-2024-0004 | Aprender Mais | ASP | Recorrência | DIA_01 | Ativo | ⚠️ Vence em ~25 dias |
| CTR-2024-0005 | ConectaShop | BSP | Recorrência | DIA_15 | Ativo | 🔴 Inadimplente |
| CTR-2025-0002 | Horizonte Tech | ASP | Recorrência | DIA_01 | Ativo | ✅ 2º contrato mesmo cliente |

---

## Faturas cadastradas

| Número | Contrato | Competência | Status | Cenário de teste |
|--------|---------|-------------|--------|-----------------|
| FAT-2026-00001 | CTR-0001 | 05/2026 | PAGA | ✅ Fatura correta e quitada |
| FAT-2026-00002 | CTR-0002 | 05/2026 | EMITIDA | ✅ Com valores pós-reajuste |
| FAT-2026-00003 | CTR-0003 | 05/2026 | APURADA | ✅ Com volumetria CLT + Estagiário |
| FAT-2026-00004 | CTR-0005 | 05/2026 | ENVIADA | ✅ Dia 01 — Aprender Mais |
| FAT-2026-00005 | CTR-0006 | 04/2026 | INADIMPLENTE | 🔴 Vencida há 45 dias |
| FAT-2026-00006 | CTR-0001 | 06/2026 | APURADA | 🔴 Valor errado (VAL001) |

---

## Cenários de validação (módulo 6)

### VAL001 — Valor faturado incorreto
```bash
POST /api/v1/faturas/ffffffff-0006-0006-0006-000000000006/validar
# FAT-2026-00006: licença base faturada a R$5.200 (deveria ser R$4.500)
# Esperado: status=BLOQUEADA, 1 alerta crítico VAL001
```

### VAL002 — Item sem go-live
```bash
# Crie uma fatura manualmente para CTR-2025-0001 (Campos Gerais)
# Os itens estão em status IMPLANTACAO — sem data_goLive_item
# Esperado: VAL002 crítico para cada item
```

### VAL005 — Contrato quase vencido
```bash
POST /api/v1/faturas/ffffffff-0004-0004-0004-000000000004/validar
# CTR-0005 vence em ~25 dias — ainda não dispara VAL005
# Mas a view vw_reajustes_pendentes mostrará alerta de proximidade
```

### VAL006 — Volumetria sem integração
```bash
# Crie uma fatura para CTR-0003 sem enviar volumetrias
# Esperado: VAL006 atenção — BPO com mão de obra sem integração
```

### VAL008 — Aviso prévio vencido
```bash
POST /api/v1/faturas/ffffffff-0006-0006-0006-000000000006/validar
# Item ASP-SUPORTE do CTR-0001 com aviso prévio vencido há 15 dias
# Esperado: VAL008 crítico
```

### VAL009 — Anomalia de volumetria (IA)
```bash
POST /api/v1/faturas/ffffffff-0003-0003-0003-000000000003/validar?com_ia=true
# Volumetria atual: 72 CLT + 8 estagiários
# Se mês anterior tiver valores muito diferentes → Claude API detecta
```

---

## Testes por módulo

### Módulo 1 — Clientes
```bash
# Listar todos
GET /api/v1/clientes/

# Buscar por CNPJ
GET /api/v1/clientes/?busca=11222333000181

# Detalhe com endereços e contatos
GET /api/v1/clientes/aaaaaaaa-0001-0001-0001-000000000001

# Filtrar por segmento Saúde
GET /api/v1/clientes/?status=ATIVO&tipo_pessoa=PJ
```

### Módulo 2 — Contratos
```bash
# Listar contratos em recorrência dia 25
GET /api/v1/contratos/?fase=RECORRENCIA&dia_faturamento=DIA_25

# Contrato em implantação
GET /api/v1/contratos/cccccccc-0004-0004-0004-000000000004

# Registrar go-live de item (Campos Gerais)
PATCH /api/v1/contratos/cccccccc-0004-0004-0004-000000000004/itens/eeeeeeee-0004-0004-0004-000000000001/go-live
{ "data_goLive": "2026-01-15" }

# Itens aguardando go-live
GET /api/v1/go-live/pendentes
```

### Módulo 4 — Reajustes
```bash
# Painel de reajustes pendentes
GET /api/v1/reajustes/pendentes

# Calcular acumulado INPC jan-dez 2024
GET /api/v1/indices/acumulado?indice=INPC&competencia_ini=2024-01-01&competencia_fim=2024-12-01

# Calcular reajuste para CTR-0001 (Horizonte Tech)
POST /api/v1/reajustes
{
  "contrato_id": "cccccccc-0001-0001-0001-000000000001",
  "indice": "INPC",
  "data_efetivacao": "2026-03-01"
}
# CTR-0003 tem item mão de obra → sistema separará INPC vs dissídio automaticamente
```

### Módulo 5 — Faturamento
```bash
# Apurar faturas dia 25 — competência junho/2026
POST /api/v1/faturamento/apurar
{
  "dia_apuracao": "DIA_25",
  "competencia": "2026-06-01",
  "data_apuracao": "2026-06-25",
  "data_vencimento": "2026-07-10"
}

# Descritivo da fatura BPO com volumetria
GET /api/v1/faturas/ffffffff-0003-0003-0003-000000000003/descritivo

# Payload K2 para emissão de NF
GET /api/v1/faturas/ffffffff-0003-0003-0003-000000000003/payload-k2

# Registrar pagamento
PATCH /api/v1/faturas/ffffffff-0002-0002-0002-000000000002/pagamento
{ "valor_pago": 8673.50, "data_pagamento": "2026-05-28" }
```

### Módulo 6 — Validação
```bash
# Validar fatura com erro de valor
POST /api/v1/faturas/ffffffff-0006-0006-0006-000000000006/validar
# Esperado: BLOQUEADA com VAL001 + VAL008

# Painel de alertas em aberto
GET /api/v1/validacao/alertas

# Registrar aviso prévio de cancelamento
POST /api/v1/contratos/aviso-previo
{
  "contrato_item_id": "eeeeeeee-0002-0002-0002-000000000002",
  "data_solicitacao": "2026-06-01",
  "prazo_vigencia_dias": 30,
  "motivo": "Cliente solicitou redução de escopo BSP."
}
```

---

## Consultas SQL úteis para inspeção

```sql
-- Visão geral dos contratos e valores
SELECT contrato_numero, cliente_nome, modalidade, fase_atual,
       valor_mensal, dia_faturamento, dias_ate_fim
FROM vw_contratos_resumo ORDER BY cliente_nome;

-- Itens aguardando go-live
SELECT * FROM vw_itens_aguardando_goLive;

-- Faturas com inadimplência
SELECT numero_fatura, cliente_nome, data_vencimento, valor_total, dias_atraso
FROM vw_faturas_resumo WHERE dias_atraso > 0 ORDER BY dias_atraso DESC;

-- Contratos com reajuste pendente
SELECT contrato_numero, cliente_nome, proximo_reajuste, dias_atraso, valor_mensal
FROM vw_reajustes_pendentes ORDER BY dias_atraso DESC;

-- Faixas de volumetria cadastradas
SELECT ps.nome, fv.tipo_vinculo, fv.faixa_de, fv.faixa_ate, fv.valor_unitario
FROM faixas_volumetria fv JOIN produtos_servicos ps ON ps.id = fv.produto_id
ORDER BY ps.nome, fv.tipo_vinculo, fv.faixa_de;
```
