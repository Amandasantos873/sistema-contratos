"""
Endpoints de go-live por item.
Adicionar ao router de contratos (app/routers/contratos.py) ou incluir como router separado.
"""
from datetime import date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.goLive_item_service import (
    registrar_goLive_item,
    registrar_goLive_lote,
    listar_itens_aguardando_goLive,
    listar_itens_faturamento,
)

router = APIRouter(tags=["Go-live por item"])


def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


# ------------------------------------------------------------------
# Schemas inline
# ------------------------------------------------------------------

class GoLiveItemRequest(BaseModel):
    data_goLive: date

class GoLiveLoteRequest(BaseModel):
    data_goLive: date
    item_ids: Optional[list[UUID]] = None   # None = todos os pendentes


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.patch(
    "/contratos/{contrato_id}/itens/{item_id}/go-live",
    summary="Registra go-live de um item específico do contrato",
)
async def registrar_goLive_item_endpoint(
    contrato_id: UUID,
    item_id:     UUID,
    dados:       GoLiveItemRequest,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    item = await registrar_goLive_item(db, contrato_id, item_id, dados.data_goLive, usuario)
    return {
        "item_id":                str(item.id),
        "status_item":            item.status_item,
        "data_goLive_item":       item.data_goLive_item,
        "data_inicio_faturamento":item.data_inicio_faturamento,
        "confirmado_por":         item.goLive_confirmado_por,
    }


@router.patch(
    "/contratos/{contrato_id}/itens/go-live-lote",
    summary="Registra go-live para múltiplos itens de uma vez (ou todos os pendentes)",
)
async def registrar_goLive_lote_endpoint(
    contrato_id: UUID,
    dados:       GoLiveLoteRequest,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    itens = await registrar_goLive_lote(db, contrato_id, dados.data_goLive, usuario, dados.item_ids)
    return {
        "itens_atualizados": len(itens),
        "data_goLive":       dados.data_goLive,
        "itens": [
            {
                "item_id":                str(i.id),
                "status_item":            i.status_item,
                "data_inicio_faturamento":i.data_inicio_faturamento,
            }
            for i in itens
        ]
    }


@router.get(
    "/go-live/pendentes",
    summary="Painel: itens recorrentes aguardando confirmação de go-live",
)
async def itens_aguardando_goLive(
    contrato_id: Optional[UUID] = Query(None),
    db:          AsyncSession   = Depends(get_db),
):
    return await listar_itens_aguardando_goLive(db, contrato_id)


@router.get(
    "/faturamento/itens",
    summary="Itens elegíveis para faturamento por dia de apuração e competência",
)
async def itens_a_faturar(
    dia_faturamento: str          = Query(..., description="DIA_01 | DIA_15 | DIA_25"),
    competencia:     date         = Query(..., description="Data de referência da apuração"),
    db:              AsyncSession = Depends(get_db),
):
    return await listar_itens_faturamento(db, dia_faturamento, competencia)
