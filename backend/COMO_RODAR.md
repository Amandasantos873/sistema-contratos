# Como rodar o sistema localmente

## Pré-requisitos

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+

---

## Backend

### 1. Instalar dependências

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configurar o banco de dados

Crie o banco no PostgreSQL:
```sql
CREATE DATABASE contratos_db;
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env com suas credenciais
```

### 4. Executar as migrations

```bash
# Cria todas as tabelas do zero
alembic upgrade head

# Ver histórico de migrations
alembic history

# Reverter última migration
alembic downgrade -1
```

### 5. Carregar dados de teste

```bash
psql -d contratos_db -f ../testes/00_dados_teste.sql
```

### 6. Subir a API

```bash
uvicorn app.main:app --reload
```

API disponível em: http://localhost:8000
Documentação:      http://localhost:8000/docs

---

## Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend disponível em: http://localhost:3000

---

## Estrutura do projeto

```
sistema-contratos/
├── backend/
│   ├── app/
│   │   ├── main.py          ← ponto de entrada
│   │   ├── config.py        ← configurações
│   │   ├── database.py      ← conexão com o banco
│   │   ├── models/          ← tabelas (SQLAlchemy)
│   │   ├── schemas/         ← validação (Pydantic)
│   │   ├── services/        ← regras de negócio
│   │   └── routers/         ← endpoints HTTP
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial.py
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
├── testes/
│   ├── 00_dados_teste.sql
│   └── GUIA_DE_TESTES.md
└── prototipo/
    ├── prototipo.html
    └── log-colaborativo.html
```

---

## Comandos úteis

```bash
# Gerar nova migration após alterar um model
alembic revision --autogenerate -m "descricao da alteracao"

# Aplicar migrations pendentes
alembic upgrade head

# Ver SQL que seria executado sem aplicar
alembic upgrade head --sql

# Verificar versão atual do banco
alembic current
```
