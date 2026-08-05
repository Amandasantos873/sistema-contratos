# Sistema de Gestão de Contratos e Faturamento

Sistema interno completo para gestão de contratos, faturamento e financeiro. Desenvolvido para empresas que oferecem serviços nas modalidades **ASP**, **BSP** e **BPO**.

---

## Sobre o projeto

Centraliza todo o ciclo de vida de um contrato e da gestão financeira — desde a proposta comercial até o DRE gerencial — eliminando processos manuais por e-mail e planilhas.

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + FastAPI |
| Banco de dados | PostgreSQL 14+ |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Autenticação | JWT + bcrypt |
| Frontend | React / Next.js |
| IA | Claude API (Anthropic) |

---

## Módulos

### Gestão de Contratos
| # | Módulo | Descrição |
|---|--------|-----------|
| 01 | Clientes | Cadastro PF/PJ com endereços, contatos e histórico |
| 02 | Contratos | ASP/BSP/BPO com go-live por item individual |
| 03 | Produtos | Catálogo por modalidade com pacotes e movimentações |
| 04 | Reajustes | INPC/IPCA/IGPM/Dissídio com fluxo de aprovação |
| 05 | Faturamento | Apuração em lote, volumetria e integração K2 Software |
| 06 | Validação IA | 12 regras automáticas + análise via Claude API |

### Financeiro
| # | Módulo | Descrição |
|---|--------|-----------|
| 07 | Contas a Receber | Cobranças automáticas, baixa por PIX/TED/boleto, aging e negociação |
| 08 | Contas a Pagar | Despesas por categoria e centro de custo, dois aprovadores |
| 09 | Fluxo de Caixa | Projetado × realizado mensal com drill-down diário |
| 10 | DRE Gerencial | Receita bruta → EBITDA → resultado, comparativo YoY |
| 11 | Conciliação Bancária | Lançamento manual com sugestão automática por valor e data |
| 12 | Comissões | Indicações de parceiros com fluxo de aprovação e pagamento |
| 13 | Orçamento × Realizado | Meta anual distribuída em 12 meses, acompanhamento de atingimento |

---

## Perfis de acesso

| Perfil | Clientes | Contratos | Reajustes | Faturamento | Go-live | Financeiro | Usuários |
|--------|----------|-----------|-----------|-------------|---------|------------|----------|
| **Administrador** | ✅ total | ✅ total | ✅ total | ✅ total | ✅ total | ✅ total | ✅ total |
| **Comercial** | ✅ criar/editar | ✅ criar/editar | ❌ | ❌ | ✅ criar/editar | ❌ | ❌ |
| **Operacional** | 👁 ver | 👁 ver | ❌ | ❌ | ✅ criar/editar | ❌ | ❌ |
| **Financeiro** | 👁 ver | 👁 ver | ✅ criar/editar | ✅ criar/editar | 👁 ver | ✅ total | ❌ |
| **Gestão** | 👁 ver | 👁 ver | 👁 ver | 👁 ver | 👁 ver | 👁 ver | ❌ |

---

## Centros de custo

ADM · RH · DP · Comercial · Conversão · Marketing · Implantação · TI · QA · Financeiro · Operacional · Diretoria Geral · Diretoria de Relacionamento · Diretoria Operacional

---

## Como rodar localmente

```bash
# 1. Instalar dependências
cd backend
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com credenciais do PostgreSQL

# 3. Criar o banco e executar migrations
psql -c "CREATE DATABASE contratos_db"
alembic upgrade head

# 4. Criar usuário administrador
python criar_admin.py

# 5. Carregar dados de teste (opcional)
psql -d contratos_db -f ../testes/00_dados_teste.sql

# 6. Subir a API
uvicorn app.main:app --reload
```

**API:** http://localhost:8000  
**Documentação:** http://localhost:8000/docs

---

## Estrutura do projeto

```
sistema-contratos/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── routers/
│   ├── alembic/versions/
│   │   ├── 0001_initial.py
│   │   └── 0002_auth.py
│   ├── requirements.txt
│   └── .env.example
├── modulo-01-clientes/
├── modulo-02-contratos/
├── modulo-03-produtos/
├── modulo-04-reajustes/
├── modulo-05-faturamento/
├── modulo-06-validacao/
├── modulo-07-contas-receber/
├── modulo-08-contas-pagar/
├── modulo-09-fluxo-caixa/
├── modulo-10-dre/
├── modulo-11-conciliacao/
├── modulo-12-comissoes/
├── modulo-13-orcamento/
├── testes/
│   ├── 00_dados_teste.sql
│   └── GUIA_DE_TESTES.md
└── prototipo/
    ├── prototipo.html
    └── log-colaborativo.html
```

---

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost/contratos_db` |
| `SECRET_KEY` | Chave JWT — gerar com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duração do token (padrão: 480 = 8h) |
| `ENVIRONMENT` | `development` ou `production` |
| `ANTHROPIC_API_KEY` | Opcional — módulo 06 validação IA |

---

## Licença

Uso interno — todos os direitos reservados.
