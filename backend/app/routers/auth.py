"""
Router de autenticação.

Endpoints públicos:
  POST /auth/login         — login com e-mail e senha
  POST /auth/login/form    — login no formato OAuth2 (compatível com /docs)

Endpoints protegidos:
  GET  /auth/me            — dados e permissões do usuário logado
  POST /auth/me/senha      — alterar própria senha

Endpoints exclusivos do ADMINISTRADOR:
  GET  /usuarios           — lista todos os usuários
  POST /usuarios           — cria novo usuário
  PATCH /usuarios/{id}     — edita perfil/status
  PATCH /usuarios/{id}/senha — redefine senha de qualquer usuário
"""
from uuid import UUID
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.usuario import Usuario, PerfilUsuario
from app.schemas.usuario import (
    LoginRequest, TokenOut, MeOut,
    UsuarioCreate, UsuarioUpdate, UsuarioAlterarSenha, UsuarioOut,
)
from app.services import auth_service as svc
from app.services.auth_service import get_usuario_token, requer_perfil

router = APIRouter(tags=["Autenticação"])


# ==================================================================
# LOGIN
# ==================================================================

@router.post(
    "/auth/login",
    response_model=TokenOut,
    summary="Login com e-mail e senha — retorna token JWT",
)
async def login(
    dados: LoginRequest,
    db:    AsyncSession = Depends(get_db),
):
    return await svc.login(db, dados)


@router.post(
    "/auth/login/form",
    response_model=TokenOut,
    summary="Login no formato OAuth2 (usado pelo /docs do Swagger)",
    include_in_schema=False,
)
async def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   AsyncSession              = Depends(get_db),
):
    """Compatibilidade com o botão 'Authorize' da documentação automática."""
    return await svc.login(db, LoginRequest(email=form.username, senha=form.password))


# ==================================================================
# USUÁRIO LOGADO
# ==================================================================

@router.get(
    "/auth/me",
    response_model=MeOut,
    summary="Retorna dados e permissões do usuário logado",
)
async def me(
    usuario: Usuario    = Depends(get_usuario_token),
    db:      AsyncSession = Depends(get_db),
):
    return await svc.get_me(db, usuario)


@router.post(
    "/auth/me/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Alterar própria senha",
)
async def alterar_senha(
    dados:   UsuarioAlterarSenha,
    usuario: Usuario    = Depends(get_usuario_token),
    db:      AsyncSession = Depends(get_db),
):
    await svc.alterar_senha(db, usuario.id, dados)


# ==================================================================
# GERENCIAMENTO DE USUÁRIOS (somente ADMINISTRADOR)
# ==================================================================

@router.get(
    "/usuarios",
    response_model=list[UsuarioOut],
    summary="Lista todos os usuários — apenas ADMINISTRADOR",
    dependencies=[Depends(requer_perfil(PerfilUsuario.ADMINISTRADOR))],
)
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
):
    return await svc.listar_usuarios(db)


@router.post(
    "/usuarios",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria novo usuário — apenas ADMINISTRADOR",
    dependencies=[Depends(requer_perfil(PerfilUsuario.ADMINISTRADOR))],
)
async def criar_usuario(
    dados:   UsuarioCreate,
    usuario: Usuario    = Depends(get_usuario_token),
    db:      AsyncSession = Depends(get_db),
):
    return await svc.criar_usuario(db, dados, usuario.nome)


@router.patch(
    "/usuarios/{usuario_id}",
    response_model=UsuarioOut,
    summary="Edita perfil ou status de um usuário — apenas ADMINISTRADOR",
    dependencies=[Depends(requer_perfil(PerfilUsuario.ADMINISTRADOR))],
)
async def atualizar_usuario(
    usuario_id: UUID,
    dados:      UsuarioUpdate,
    usuario:    Usuario    = Depends(get_usuario_token),
    db:         AsyncSession = Depends(get_db),
):
    return await svc.atualizar_usuario(db, usuario_id, dados, usuario.nome)


@router.patch(
    "/usuarios/{usuario_id}/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Redefine senha de qualquer usuário — apenas ADMINISTRADOR",
    dependencies=[Depends(requer_perfil(PerfilUsuario.ADMINISTRADOR))],
)
async def redefinir_senha(
    usuario_id: UUID,
    nova_senha: str,
    usuario:    Usuario    = Depends(get_usuario_token),
    db:         AsyncSession = Depends(get_db),
):
    await svc.redefinir_senha_admin(db, usuario_id, nova_senha, usuario.nome)
