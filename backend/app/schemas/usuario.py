from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from app.models.usuario import PerfilUsuario


# ==================================================================
# LOGIN
# ==================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(..., min_length=6)

class TokenOut(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    perfil:       PerfilUsuario
    nome:         str
    expira_em:    datetime


# ==================================================================
# USUÁRIO
# ==================================================================

class UsuarioCreate(BaseModel):
    nome:   str           = Field(..., min_length=3, max_length=200)
    email:  EmailStr
    senha:  str           = Field(..., min_length=8, description="Mínimo 8 caracteres")
    perfil: PerfilUsuario

class UsuarioUpdate(BaseModel):
    nome:   Optional[str]           = None
    perfil: Optional[PerfilUsuario] = None
    ativo:  Optional[bool]          = None

class UsuarioAlterarSenha(BaseModel):
    senha_atual: str = Field(..., min_length=6)
    senha_nova:  str = Field(..., min_length=8)

class UsuarioOut(BaseModel):
    id:            UUID
    nome:          str
    email:         str
    perfil:        PerfilUsuario
    ativo:         bool
    ultimo_acesso: Optional[datetime]
    criado_em:     datetime

    model_config = {"from_attributes": True}


# ==================================================================
# PERMISSÕES
# ==================================================================

class PermissaoOut(BaseModel):
    modulo:  str
    ler:     bool
    criar:   bool
    editar:  bool
    excluir: bool

    model_config = {"from_attributes": True}

class MeOut(BaseModel):
    """Dados do usuário logado + suas permissões."""
    id:           UUID
    nome:         str
    email:        str
    perfil:       PerfilUsuario
    permissoes:   list[PermissaoOut] = []

    model_config = {"from_attributes": True}
