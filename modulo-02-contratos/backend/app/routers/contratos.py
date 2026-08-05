from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.contrato import ModalidadeContrato, StatusContrato, FaseContrato
from app.schemas.contrato import (
    ContratoCreate, ContratoUpdate, ContratoGoLive, ContratoOut, ContratoListOut,
    ItemCreate, ItemOut,
    ParcelaCreate, ParcelaUpdate, ParcelaOut,
    ProdutoServicoOut,
)
from app.services import contrato_service as svc

router = APIRouter(prefix="/contratos", tags=["Contratos"])


def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


# ==================================================================
# PRODUTOS/SERVIÇOS (catálogo)
# ==================================================================

@router.get(
    "/produtos",
    response_model=list[ProdutoServicoOut],
    summary="Lista produtos/serviços disponíveis por modalidade e fase",
)
async def listar_produtos(
    modalidade: Optional[ModalidadeContrato] = Query(None),
    fase:       Optional[FaseContrato]       = Query(None),
    db:         AsyncSession                 = Depends(get_db),
):
    return await svc.listar_produtos(db, modalidade, fase)


# ==================================================================
# CONTRATOS — CRUD
# ==================================================================

@router.post(
    "/",
    response_model=ContratoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo contrato",
)
async def criar_contrato(
    dados:   ContratoCreate,
    db:      AsyncSession = Depends(get_db),
    usuario: str          = Depends(get_usuario_atual),
):
    return await svc.criar_contrato(db, dados, usuario)


@router.get(
    "/",
    response_model=ContratoListOut,
    summary="Lista contratos com filtros e paginação",
)
async def listar_contratos(
    pagina:     int                          = Query(1,  ge=1),
    por_pagina: int                          = Query(20, ge=1, le=100),
    cliente_id: Optional[UUID]               = Query(None),
    modalidade: Optional[ModalidadeContrato] = Query(None),
    status:     Optional[StatusContrato]     = Query(None),
    fase:       Optional[FaseContrato]       = Query(None),
    db:         AsyncSession                 = Depends(get_db),
):
    return await svc.listar_contratos(db, pagina, por_pagina, cliente_id, modalidade, status, fase)


@router.get(
    "/a-faturar",
    summary="Lista contratos elegíveis para faturamento por dia de apuração",
)
async def contratos_a_faturar(
    dia_faturamento: str    = Query(..., description="DIA_01 | DIA_15 | DIA_25"),
    db:              AsyncSession = Depends(get_db),
):
    return await svc.contratos_a_faturar(db, dia_faturamento)


@router.get(
    "/{contrato_id}",
    response_model=ContratoOut,
    summary="Retorna contrato completo com itens e parcelas",
)
async def buscar_contrato(
    contrato_id: UUID,
    db:          AsyncSession = Depends(get_db),
):
    return await svc.buscar_contrato(db, contrato_id)


@router.patch(
    "/{contrato_id}",
    response_model=ContratoOut,
    summary="Atualiza dados do contrato",
)
async def atualizar_contrato(
    contrato_id: UUID,
    dados:       ContratoUpdate,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.atualizar_contrato(db, contrato_id, dados, usuario)


@router.patch(
    "/{contrato_id}/go-live",
    response_model=ContratoOut,
    summary="Registra go-live e inicia fase de recorrência",
)
async def registrar_goLive(
    contrato_id: UUID,
    dados:       ContratoGoLive,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.registrar_goLive(db, contrato_id, dados, usuario)


# ==================================================================
# ITENS
# ==================================================================

@router.post(
    "/{contrato_id}/itens",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona item ao contrato",
)
async def adicionar_item(
    contrato_id: UUID,
    dados:       ItemCreate,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.adicionar_item(db, contrato_id, dados, usuario)


@router.delete(
    "/{contrato_id}/itens/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove (desativa) item do contrato",
)
async def remover_item(
    contrato_id: UUID,
    item_id:     UUID,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    await svc.remover_item(db, contrato_id, item_id, usuario)


# ==================================================================
# PARCELAS DE IMPLANTAÇÃO
# ==================================================================

@router.post(
    "/{contrato_id}/parcelas",
    response_model=ParcelaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona parcela de implantação",
)
async def adicionar_parcela(
    contrato_id: UUID,
    dados:       ParcelaCreate,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.adicionar_parcela(db, contrato_id, dados, usuario)


@router.patch(
    "/{contrato_id}/parcelas/{parcela_id}",
    response_model=ParcelaOut,
    summary="Atualiza parcela de implantação (status, pagamento, etc.)",
)
async def atualizar_parcela(
    contrato_id: UUID,
    parcela_id:  UUID,
    dados:       ParcelaUpdate,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.atualizar_parcela(db, contrato_id, parcela_id, dados, usuario)
