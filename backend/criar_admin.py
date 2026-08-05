"""
Script para criar o primeiro usuário administrador.
Execute uma única vez após rodar as migrations.

Uso:
    python criar_admin.py
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings
from app.models.usuario import Usuario, PerfilUsuario
from app.services.auth_service import hash_senha
import uuid


async def criar_admin():
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Dados do administrador — altere antes de executar
    NOME  = "Maria Lavrador"
    EMAIL = "maria@suaempresa.com.br"
    SENHA = "Troque@123"      # ← altere para uma senha forte

    async with AsyncSessionLocal() as db:
        # Verifica se já existe
        from sqlalchemy import select
        existe = await db.execute(select(Usuario).where(Usuario.email == EMAIL))
        if existe.scalar_one_or_none():
            print(f"⚠️  Usuário {EMAIL} já existe.")
            return

        admin = Usuario(
            id         = uuid.uuid4(),
            nome       = NOME,
            email      = EMAIL.lower(),
            senha_hash = hash_senha(SENHA),
            perfil     = PerfilUsuario.ADMINISTRADOR,
            ativo      = True,
            criado_por = "setup",
        )
        db.add(admin)
        await db.commit()
        print(f"✅  Administrador criado com sucesso!")
        print(f"    E-mail: {EMAIL}")
        print(f"    Senha:  {SENHA}")
        print(f"    ⚠️  Altere a senha no primeiro acesso.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(criar_admin())
