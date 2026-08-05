"""
Router do módulo de clientes.
Responsável apenas por: receber request, chamar service, retornar response.
"""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.cliente import StatusCliente, TipoPessoa
from app.schemas.cliente import (
    ClienteCreate, ClienteUpdate, ClienteInativar,
    ClienteOut, ClienteListOut, SegmentoOut,
    EnderecoCreate, EnderecoUpdate, EnderecoOut,
    ContatoCreate, ContatoUpdate, ContatoOut,
)
from app.services import cliente_service as svc

router = APIRouter(prefix="/clientes", tags=["Clientes"])


# ------------------------------------------------------------------
# Dependência temporária de usuário
# (substituir por autenticação JWT no módulo de auth)
# ------------------------------------------------------------------
def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")

def get_ip(request: Request) -> str:
    return request.client.host if request.client else None


# ==================================================================
# SEGMENTOS (lookup)
# ==================================================================

@router.get(
    "/segmentos",
    response_model=list[SegmentoOut],
    summary="Lista os segmentos disponíveis",
)
async def listar_segmentos(db: AsyncSession = Depends(get_db)):
    return await svc.listar_segmentos(db)


# ==================================================================
# CEP (autopreenchimento)
# ==================================================================

@router.get(
    "/cep/{cep}",
    summary="Consulta endereço pelo CEP via ViaCEP",
)
async def consultar_cep(cep: str):
    return await svc.consultar_cep(cep)


# ==================================================================
# CLIENTES — CRUD principal
# ==================================================================

@router.post(
    "/",
    response_model=ClienteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo cliente",
)
async def criar_cliente(
    dados:   ClienteCreate,
    request: Request,
    db:      AsyncSession = Depends(get_db),
    usuario: str          = Depends(get_usuario_atual),
):
    return await svc.criar_cliente(db, dados, usuario, get_ip(request))


@router.get(
    "/",
    response_model=ClienteListOut,
    summary="Lista clientes com filtros e paginação",
)
async def listar_clientes(
    pagina:      int                    = Query(1,  ge=1),
    por_pagina:  int                    = Query(20, ge=1, le=100),
    busca:       Optional[str]          = Query(None, description="Busca por nome, fantasia ou documento"),
    status:      Optional[StatusCliente]= Query(None),
    segmento_id: Optional[int]          = Query(None),
    tipo_pessoa: Optional[TipoPessoa]   = Query(None),
    db:          AsyncSession           = Depends(get_db),
):
    return await svc.listar_clientes(
        db, pagina, por_pagina, busca, status, segmento_id, tipo_pessoa
    )


@router.get(
    "/{cliente_id}",
    response_model=ClienteOut,
    summary="Retorna um cliente com endereços e contatos",
)
async def buscar_cliente(
    cliente_id: UUID,
    db:         AsyncSession = Depends(get_db),
):
    return await svc.buscar_cliente(db, cliente_id)


@router.patch(
    "/{cliente_id}",
    response_model=ClienteOut,
    summary="Atualiza dados cadastrais do cliente",
)
async def atualizar_cliente(
    cliente_id: UUID,
    dados:      ClienteUpdate,
    request:    Request,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    return await svc.atualizar_cliente(db, cliente_id, dados, usuario, get_ip(request))


@router.patch(
    "/{cliente_id}/inativar",
    response_model=ClienteOut,
    summary="Inativa um cliente (exige motivo)",
)
async def inativar_cliente(
    cliente_id: UUID,
    dados:      ClienteInativar,
    request:    Request,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    return await svc.inativar_cliente(db, cliente_id, dados, usuario, get_ip(request))


# ==================================================================
# ENDEREÇOS
# ==================================================================

@router.post(
    "/{cliente_id}/enderecos",
    response_model=EnderecoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona um endereço ao cliente",
)
async def adicionar_endereco(
    cliente_id: UUID,
    dados:      EnderecoCreate,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    return await svc.adicionar_endereco(db, cliente_id, dados, usuario)


@router.patch(
    "/{cliente_id}/enderecos/{endereco_id}",
    response_model=EnderecoOut,
    summary="Atualiza um endereço do cliente",
)
async def atualizar_endereco(
    cliente_id:  UUID,
    endereco_id: UUID,
    dados:       EnderecoUpdate,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.atualizar_endereco(db, cliente_id, endereco_id, dados, usuario)


# ==================================================================
# CONTATOS
# ==================================================================

@router.post(
    "/{cliente_id}/contatos",
    response_model=ContatoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona um contato ao cliente",
)
async def adicionar_contato(
    cliente_id: UUID,
    dados:      ContatoCreate,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    return await svc.adicionar_contato(db, cliente_id, dados, usuario)


@router.patch(
    "/{cliente_id}/contatos/{contato_id}",
    response_model=ContatoOut,
    summary="Atualiza um contato do cliente",
)
async def atualizar_contato(
    cliente_id: UUID,
    contato_id: UUID,
    dados:      ContatoUpdate,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    return await svc.atualizar_contato(db, cliente_id, contato_id, dados, usuario)


@router.delete(
    "/{cliente_id}/contatos/{contato_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove (desativa) um contato do cliente",
)
async def remover_contato(
    cliente_id: UUID,
    contato_id: UUID,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    await svc.remover_contato(db, cliente_id, contato_id, usuario)
