from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.fatura import (
    FaixaCreate, FaixaOut,
    FaturaApurarRequest, FaturaRegistrarPagamento, FaturaRegistrarNF,
    VolumetriaInput, FaturaOut, FaturaListOut, ApuracaoResultado,
)
from app.services import fatura_service as svc

router = APIRouter(tags=["Faturamento"])


def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


# ==================================================================
# FAIXAS DE VOLUMETRIA
# ==================================================================

@router.get("/faturamento/faixas", response_model=list[FaixaOut],
            summary="Lista faixas de preço por volumetria")
async def listar_faixas(
    produto_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.listar_faixas(db, produto_id)


@router.post("/faturamento/faixas", response_model=FaixaOut,
             status_code=status.HTTP_201_CREATED,
             summary="Cria faixa de preço por volumetria")
async def criar_faixa(
    dados: FaixaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await svc.criar_faixa(db, dados, usuario)


# ==================================================================
# APURAÇÃO EM LOTE
# ==================================================================

@router.post("/faturamento/apurar", response_model=ApuracaoResultado,
             status_code=status.HTTP_201_CREATED,
             summary="Apura e gera faturas em lote para um dia de apuração")
async def apurar_faturas(
    dados: FaturaApurarRequest,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await svc.apurar_faturas(db, dados, usuario)


# ==================================================================
# FATURAS
# ==================================================================

@router.get("/faturas", response_model=FaturaListOut,
            summary="Lista faturas com filtros")
async def listar_faturas(
    pagina:       int           = Query(1, ge=1),
    por_pagina:   int           = Query(20, ge=1, le=100),
    competencia:  Optional[date]= Query(None),
    status:       Optional[str] = Query(None),
    dia_apuracao: Optional[str] = Query(None),
    contrato_id:  Optional[UUID]= Query(None),
    em_atraso:    bool          = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await svc.listar_faturas(db, pagina, por_pagina, competencia, status, dia_apuracao, contrato_id, em_atraso)


@router.get("/faturas/{fatura_id}", response_model=FaturaOut,
            summary="Retorna fatura completa com itens, volumetrias e documentos")
async def buscar_fatura(fatura_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.buscar_fatura(db, fatura_id)


@router.patch("/faturas/{fatura_id}/pagamento", response_model=FaturaOut,
              summary="Registra pagamento da fatura")
async def registrar_pagamento(
    fatura_id: UUID,
    dados: FaturaRegistrarPagamento,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await svc.registrar_pagamento(db, fatura_id, dados, usuario)


@router.patch("/faturas/{fatura_id}/nf", response_model=FaturaOut,
              summary="Registra dados da NFS-e emitida no K2")
async def registrar_nf(
    fatura_id: UUID,
    dados: FaturaRegistrarNF,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await svc.registrar_nf(db, fatura_id, dados, usuario)


@router.get("/faturas/{fatura_id}/payload-k2",
            summary="Gera payload para emissão de RPS/NFS-e no K2 Software")
async def gerar_payload_k2(
    fatura_id: UUID,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await svc.gerar_payload_k2(db, fatura_id)


@router.get("/faturas/{fatura_id}/descritivo",
            summary="Gera descritivo detalhado da fatura com volumetrias")
async def gerar_descritivo(
    fatura_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await svc.gerar_descritivo(db, fatura_id)


# ==================================================================
# VOLUMETRIAS (recebidas via integração de folha)
# ==================================================================

@router.post("/faturas/{fatura_id}/volumetrias", response_model=FaturaOut,
             summary="Recebe volumetrias do sistema de folha e calcula valores por faixa")
async def receber_volumetrias(
    fatura_id:   UUID,
    volumetrias: list[VolumetriaInput],
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.receber_volumetrias(db, fatura_id, volumetrias, usuario)
