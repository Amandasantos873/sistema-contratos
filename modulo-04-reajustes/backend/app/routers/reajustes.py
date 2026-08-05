from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.reajuste import IndiceEconomico
from app.schemas.reajuste import (
    IndiceCreate, IndiceOut, IndiceAcumuladoOut,
    ReajusteCalcularRequest, ReajusteAprovarRequest,
    ReajusteReprovarRequest, ReajusteComunicarRequest,
    ReajusteOut, ReajustePendenteOut,
    AditivoCreate,
)
from app.services import reajuste_service as svc

router = APIRouter(tags=["Reajustes e Aditivos"])


def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


# ==================================================================
# ÍNDICES ECONÔMICOS
# ==================================================================

@router.get("/indices", response_model=list[IndiceOut], summary="Lista histórico de índices econômicos")
async def listar_indices(
    indice: Optional[IndiceEconomico] = Query(None),
    ano:    Optional[int]             = Query(None),
    db:     AsyncSession              = Depends(get_db),
):
    return await svc.listar_indices(db, indice.value if indice else None, ano)


@router.post("/indices", response_model=IndiceOut, status_code=status.HTTP_201_CREATED,
             summary="Cadastra valor mensal de índice econômico")
async def cadastrar_indice(
    dados:   IndiceCreate,
    db:      AsyncSession = Depends(get_db),
    usuario: str          = Depends(get_usuario_atual),
):
    return await svc.cadastrar_indice(db, dados, usuario)


@router.get("/indices/acumulado", response_model=IndiceAcumuladoOut,
            summary="Calcula acumulado de um índice entre dois meses")
async def calcular_acumulado(
    indice:          IndiceEconomico = Query(...),
    competencia_ini: date            = Query(...),
    competencia_fim: date            = Query(...),
    db:              AsyncSession    = Depends(get_db),
):
    return await svc.calcular_acumulado(db, indice.value, competencia_ini, competencia_fim)


# ==================================================================
# DISSÍDIO
# ==================================================================

@router.get("/dissidios", summary="Lista histórico de dissídios cadastrados")
async def listar_dissidios(db: AsyncSession = Depends(get_db)):
    return await svc.listar_dissidios(db)


@router.post("/dissidios", status_code=status.HTTP_201_CREATED,
             summary="Cadastra ou atualiza percentual de dissídio anual")
async def cadastrar_dissidio(
    ano_base:         int     = Query(..., ge=2000, le=2099),
    data_vigencia:    date    = Query(...),
    valor_percentual: Decimal = Query(..., gt=0),
    categoria:        str     = Query(default="GERAL"),
    fonte:            Optional[str] = Query(None),
    db:               AsyncSession  = Depends(get_db),
    usuario:          str           = Depends(get_usuario_atual),
):
    return await svc.cadastrar_dissidio(db, ano_base, data_vigencia, valor_percentual, categoria, fonte, usuario)


# ==================================================================
# REAJUSTES PENDENTES (painel de controle)
# ==================================================================

@router.get("/reajustes/pendentes", response_model=list[ReajustePendenteOut],
            summary="Contratos com reajuste vencido ou em andamento")
async def reajustes_pendentes(
    apenas_vencidos: bool        = Query(False),
    db:              AsyncSession = Depends(get_db),
):
    return await svc.listar_reajustes_pendentes(db, apenas_vencidos)


# ==================================================================
# REAJUSTES — FLUXO COMPLETO
# ==================================================================

@router.post("/reajustes", response_model=ReajusteOut, status_code=status.HTTP_201_CREATED,
             summary="Calcula reajuste de um contrato (separa MOA do índice principal)")
async def calcular_reajuste(
    dados:   ReajusteCalcularRequest,
    db:      AsyncSession = Depends(get_db),
    usuario: str          = Depends(get_usuario_atual),
):
    return await svc.calcular_reajuste(db, dados, usuario)


@router.get("/reajustes/contrato/{contrato_id}", response_model=list[ReajusteOut],
            summary="Lista todos os reajustes de um contrato")
async def listar_reajustes_contrato(
    contrato_id: UUID,
    db:          AsyncSession = Depends(get_db),
):
    return await svc.listar_reajustes_contrato(db, contrato_id)


@router.patch("/reajustes/{reajuste_id}/enviar-aprovacao", response_model=ReajusteOut,
              summary="Envia reajuste para aprovação interna")
async def enviar_para_aprovacao(
    reajuste_id: UUID,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.enviar_para_aprovacao(db, reajuste_id, usuario)


@router.patch("/reajustes/{reajuste_id}/aprovar", response_model=ReajusteOut,
              summary="Aprova reajuste (permite ajustar percentual e negociar por item)")
async def aprovar_reajuste(
    reajuste_id: UUID,
    dados:       ReajusteAprovarRequest,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.aprovar_reajuste(db, reajuste_id, dados, usuario)


@router.patch("/reajustes/{reajuste_id}/reprovar", response_model=ReajusteOut,
              summary="Reprova reajuste com motivo obrigatório")
async def reprovar_reajuste(
    reajuste_id: UUID,
    dados:       ReajusteReprovarRequest,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.reprovar_reajuste(db, reajuste_id, dados, usuario)


@router.patch("/reajustes/{reajuste_id}/comunicar", response_model=ReajusteOut,
              summary="Registra comunicação do reajuste ao cliente")
async def comunicar_cliente(
    reajuste_id: UUID,
    dados:       ReajusteComunicarRequest,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.comunicar_cliente(db, reajuste_id, dados, usuario)


@router.patch("/reajustes/{reajuste_id}/efetivar", response_model=ReajusteOut,
              summary="Efetiva reajuste — atualiza itens, gera aditivo e atualiza mensalidade")
async def efetivar_reajuste(
    reajuste_id: UUID,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.efetivar_reajuste(db, reajuste_id, usuario)


# ==================================================================
# ADITIVOS MANUAIS
# ==================================================================

@router.get("/contratos/{contrato_id}/aditivos",
            summary="Lista aditivos de um contrato")
async def listar_aditivos(
    contrato_id: UUID,
    db:          AsyncSession = Depends(get_db),
):
    return await svc.listar_aditivos_contrato(db, contrato_id)


@router.post("/contratos/{contrato_id}/aditivos",
             status_code=status.HTTP_201_CREATED,
             summary="Cria aditivo manual (prazo, escopo, rescisão, etc.)")
async def criar_aditivo_manual(
    contrato_id: UUID,
    dados:       AditivoCreate,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.criar_aditivo_manual(db, contrato_id, dados, usuario)
