"""
Alembic env.py — configurado para:
  - SQLAlchemy assíncrono (asyncpg)
  - Leitura da DATABASE_URL pelo .env via pydantic-settings
  - Autogenerate de migrations a partir dos models
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Importa configurações e Base (com todos os models registrados)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config  import settings
from app.database import Base

# Importa TODOS os models para que o autogenerate funcione
# (a ordem de importação não importa — o Alembic resolve as dependências)
from app.models.cliente   import (  # noqa: F401
    Segmento, Cliente, ClienteEndereco, ClienteContato, ClienteHistorico
)
from app.models.contrato  import (  # noqa: F401
    ProdutoServico, Contrato, ContratoItem, ContratoParcela,
    ContratoAditivo, ContratoHistorico
)
from app.models.produto   import (  # noqa: F401
    ProdutoPacote, ProdutoPacoteItem, ContratoItemMovimentacao
)
from app.models.reajuste  import (  # noqa: F401
    IndiceHistorico, ContratoReajuste, ReajusteItem
)
from app.models.fatura    import (  # noqa: F401
    FaixaVolumetria, Fatura, FaturaItem, FaturaVolumetria, FaturaDocumento
)
from app.models.validacao import (  # noqa: F401
    FaturaValidacao, FaturaAlerta, AvisoPrevioCancelamento
)

# Configuração do Alembic
config = context.config

# Sobrescreve a URL pelo valor do .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para autogenerate
target_metadata = Base.metadata


# ------------------------------------------------------------------
# Modo offline (gera SQL sem conectar ao banco)
# ------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url                     = url,
        target_metadata         = target_metadata,
        literal_binds           = True,
        dialect_opts            = {"paramstyle": "named"},
        compare_type            = True,
        compare_server_default  = True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------------
# Modo online (conecta ao banco e executa as migrations)
# ------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection              = connection,
        target_metadata         = target_metadata,
        compare_type            = True,
        compare_server_default  = True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix      = "sqlalchemy.",
        poolclass   = pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
