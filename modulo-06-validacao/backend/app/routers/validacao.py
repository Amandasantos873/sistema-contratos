"""Router FastAPI do módulo de validação."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.validacao import (
    ValidacaoOut, AlertaPainelOut,
    JustificarAlertaRequest, EmitirComRessalvaRequest,
    AvisoPrevioCreate, AvisoPrevioOut,
)
from app.services import validacao_service as svc

router = APIRouter(tags=["Validação por IA"])


def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


@router.post("/faturas/{fatura_id}/validar", response_model=ValidacaoOut,
             summary="Executa validação completa da fatura (12 regras + IA opcional)")
async def validar_fatura(
    fatura_id: UUID,
    com_ia:    bool         = Query(False, description="Ativa análise de anomalias via Claude API"),
    db:        AsyncSession = Depends(get_db),
    usuario:   str          = Depends(get_usuario_atual),
):
    return await svc.validar_fatura(db, fatura_id, usuario, com_ia)


@router.get("/validacao/alertas", response_model=list[AlertaPainelOut],
            summary="Painel: todos os alertas abertos em todas as faturas")
async def alertas_abertos(db: AsyncSession = Depends(get_db)):
    return await svc.listar_alertas_abertos(db)


@router.patch("/validacao/alertas/{alerta_id}/justificar", response_model=dict,
              summary="Justifica um alerta individual")
async def justificar_alerta(
    alerta_id: UUID,
    dados:     JustificarAlertaRequest,
    db:        AsyncSession = Depends(get_db),
    usuario:   str          = Depends(get_usuario_atual),
):
    await svc.justificar_alerta(db, alerta_id, dados, usuario)
    return {"status": "JUSTIFICADO", "alerta_id": str(alerta_id)}


@router.post("/faturas/{fatura_id}/emitir-com-ressalva",
             summary="Emite fatura com alertas críticos mediante justificativa obrigatória")
async def emitir_com_ressalva(
    fatura_id: UUID,
    dados:     EmitirComRessalvaRequest,
    db:        AsyncSession = Depends(get_db),
    usuario:   str          = Depends(get_usuario_atual),
):
    return await svc.emitir_com_ressalva(db, fatura_id, dados, usuario)


@router.post("/contratos/aviso-previo", response_model=AvisoPrevioOut,
             status_code=status.HTTP_201_CREATED,
             summary="Registra aviso prévio de cancelamento de item (ativa VAL008)")
async def registrar_aviso_previo(
    dados:   AvisoPrevioCreate,
    db:      AsyncSession = Depends(get_db),
    usuario: str          = Depends(get_usuario_atual),
):
    return await svc.registrar_aviso_previo(db, dados, usuario)
