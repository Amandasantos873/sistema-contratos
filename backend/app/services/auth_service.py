"""
Service de autenticação.

Responsabilidades:
  - Hash e verificação de senha (bcrypt)
  - Geração e validação de tokens JWT
  - Login, cadastro e gerenciamento de usuários
  - Dependências FastAPI para proteção de rotas por perfil
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.database import get_db
from app.models.usuario import Usuario, PerfilUsuario, PerfilPermissao
from app.schemas.usuario import (
    LoginRequest, TokenOut, UsuarioCreate, UsuarioUpdate,
    UsuarioAlterarSenha, UsuarioOut, MeOut, PermissaoOut,
)

# ------------------------------------------------------------------
# Configuração
# ------------------------------------------------------------------
pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ------------------------------------------------------------------
# Senha
# ------------------------------------------------------------------
def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)

def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


# ------------------------------------------------------------------
# JWT
# ------------------------------------------------------------------
def criar_token(data: dict) -> tuple[str, datetime]:
    expira = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {**data, "exp": expira}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expira


async def get_usuario_token(
    token: str               = Depends(oauth2_scheme),
    db:    AsyncSession      = Depends(get_db),
) -> Usuario:
    """Dependência FastAPI: valida o token e retorna o usuário logado."""
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        usuario_id: str = payload.get("sub")
        if not usuario_id:
            raise credenciais_invalidas
    except JWTError:
        raise credenciais_invalidas

    usuario = await db.get(Usuario, UUID(usuario_id))
    if not usuario or not usuario.ativo:
        raise credenciais_invalidas

    # Atualiza último acesso
    usuario.ultimo_acesso = datetime.now(timezone.utc)
    await db.flush()

    return usuario


# ------------------------------------------------------------------
# Dependências de perfil
# ------------------------------------------------------------------
def requer_perfil(*perfis: PerfilUsuario):
    """
    Dependência que exige que o usuário tenha um dos perfis informados.

    Uso nos routers:
        @router.post("/", dependencies=[Depends(requer_perfil(PerfilUsuario.ADMINISTRADOR))])
    """
    async def _verificar(usuario: Usuario = Depends(get_usuario_token)):
        if usuario.perfil not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Seu perfil ({usuario.perfil.value}) não tem permissão para esta ação."
            )
        return usuario
    return _verificar


def requer_permissao(modulo: str, acao: str):
    """
    Dependência que verifica permissão específica na tabela perfis_permissoes.
    acao: 'ler' | 'criar' | 'editar' | 'excluir'

    Uso:
        @router.post("/", dependencies=[Depends(requer_permissao("faturamento","criar"))])
    """
    async def _verificar(
        usuario: Usuario    = Depends(get_usuario_token),
        db:      AsyncSession = Depends(get_db),
    ):
        row = await db.execute(
            text(f"""
                SELECT {acao} FROM perfis_permissoes
                WHERE perfil = :perfil AND modulo = :modulo
            """),
            {"perfil": usuario.perfil.value, "modulo": modulo}
        )
        permitido = row.scalar()
        if not permitido:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Perfil '{usuario.perfil.value}' não tem permissão de '{acao}' em '{modulo}'."
            )
        return usuario
    return _verificar


# ------------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------------
async def login(db: AsyncSession, dados: LoginRequest) -> TokenOut:
    result = await db.execute(
        select(Usuario).where(Usuario.email == dados.email)
    )
    usuario = result.scalar_one_or_none()

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )
    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Contate o administrador.",
        )

    token, expira = criar_token({"sub": str(usuario.id), "perfil": usuario.perfil.value})
    usuario.ultimo_acesso = datetime.now(timezone.utc)
    await db.flush()

    return TokenOut(
        access_token = token,
        perfil       = usuario.perfil,
        nome         = usuario.nome,
        expira_em    = expira,
    )


# ------------------------------------------------------------------
# ME (usuário logado)
# ------------------------------------------------------------------
async def get_me(db: AsyncSession, usuario: Usuario) -> MeOut:
    rows = await db.execute(
        select(PerfilPermissao).where(PerfilPermissao.perfil == usuario.perfil)
    )
    permissoes = [
        PermissaoOut(
            modulo  = p.modulo,
            ler     = p.ler,
            criar   = p.criar,
            editar  = p.editar,
            excluir = p.excluir,
        )
        for p in rows.scalars().all()
    ]
    return MeOut(
        id          = usuario.id,
        nome        = usuario.nome,
        email       = usuario.email,
        perfil      = usuario.perfil,
        permissoes  = permissoes,
    )


# ------------------------------------------------------------------
# CRUD DE USUÁRIOS (somente ADMINISTRADOR)
# ------------------------------------------------------------------
async def listar_usuarios(db: AsyncSession) -> list[Usuario]:
    result = await db.execute(
        select(Usuario).order_by(Usuario.nome)
    )
    return result.scalars().all()


async def criar_usuario(
    db:      AsyncSession,
    dados:   UsuarioCreate,
    criador: str,
) -> Usuario:
    existe = await db.execute(
        select(Usuario).where(Usuario.email == dados.email)
    )
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

    usuario = Usuario(
        nome       = dados.nome,
        email      = dados.email.lower(),
        senha_hash = hash_senha(dados.senha),
        perfil     = dados.perfil,
        criado_por = criador,
    )
    db.add(usuario)
    await db.flush()
    await db.refresh(usuario)
    return usuario


async def atualizar_usuario(
    db:         AsyncSession,
    usuario_id: UUID,
    dados:      UsuarioUpdate,
    editor:     str,
) -> Usuario:
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)

    usuario.atualizado_em = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(usuario)
    return usuario


async def alterar_senha(
    db:         AsyncSession,
    usuario_id: UUID,
    dados:      UsuarioAlterarSenha,
) -> None:
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    usuario.senha_hash    = hash_senha(dados.senha_nova)
    usuario.atualizado_em = datetime.now(timezone.utc)
    await db.flush()


async def redefinir_senha_admin(
    db:         AsyncSession,
    usuario_id: UUID,
    nova_senha: str,
    admin:      str,
) -> None:
    """Administrador redefine a senha de qualquer usuário sem precisar da senha atual."""
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if len(nova_senha) < 8:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 8 caracteres.")

    usuario.senha_hash    = hash_senha(nova_senha)
    usuario.atualizado_em = datetime.now(timezone.utc)
    await db.flush()
