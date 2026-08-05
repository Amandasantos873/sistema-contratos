"""
Módulo 07 — Contas a Receber
Service + Router
"""
from math import ceil
from decimal import Decimal
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.database import get_db
from app.models.cobranca import (
    Cobranca, Recebimento, Negociacao,
    StatusCobranca, StatusNegociacao, FormaRecebimento
)
from app.models.cobranca import (
    RecebimentoCreate, NegociacaoCreate,
    CobrancaAtualizarERP, CobrancaOut, CobrancaResumoOut, AgingResumoOut
)


# ==================================================================
# SERVICE
# ==================================================================

async def _get_cobranca_ou_404(db: AsyncSession, cobranca_id: UUID) -> Cobranca:
    result = await db.execute(
        select(Cobranca)
        .options(
            selectinload(Cobranca.recebimentos),
            selectinload(Cobranca.negociacoes),
        )
        .where(Cobranca.id == cobranca_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada.")
    return c


async def listar_cobrancas(
    db:          AsyncSession,
    pagina:      int = 1,
    por_pagina:  int = 20,
    status:      Optional[str]  = None,
    cliente_id:  Optional[UUID] = None,
    competencia: Optional[date] = None,
    em_atraso:   bool = False,
    faixa_aging: Optional[str] = None,
) -> dict:
    params = {
        "status":      status,
        "cliente_id":  str(cliente_id) if cliente_id else None,
        "competencia": competencia,
        "em_atraso":   em_atraso,
        "faixa_aging": faixa_aging,
        "limit":       por_pagina,
        "offset":      (pagina - 1) * por_pagina,
    }
    filtro = """
        (:status      IS NULL OR status       = :status::status_cobranca)
        AND (:cliente_id IS NULL OR cliente_id = :cliente_id::uuid)
        AND (:competencia IS NULL OR competencia = :competencia)
        AND (:em_atraso = FALSE OR dias_atraso > 0)
        AND (:faixa_aging IS NULL OR faixa_aging = :faixa_aging)
        AND status != 'CANCELADA'
    """
    rows = await db.execute(text(f"""
        SELECT id, numero_cobranca, cliente_nome, contrato_numero, modalidade,
               competencia, data_vencimento, valor_original, valor_recebido,
               valor_saldo, dias_atraso, faixa_aging, status
        FROM vw_aging WHERE {filtro}
        ORDER BY data_vencimento, cliente_nome
        LIMIT :limit OFFSET :offset
    """), params)
    total = (await db.execute(text(f"SELECT COUNT(*) FROM vw_aging WHERE {filtro}"), params)).scalar()
    dados = [CobrancaResumoOut.model_validate(dict(r._mapping)) for r in rows]
    return {
        "dados": dados,
        "meta": {"total": total, "pagina": pagina, "por_pagina": por_pagina, "paginas": ceil(total / por_pagina) if total else 0}
    }


async def buscar_cobranca(db: AsyncSession, cobranca_id: UUID) -> Cobranca:
    return await _get_cobranca_ou_404(db, cobranca_id)


async def atualizar_erp(
    db: AsyncSession, cobranca_id: UUID, dados: CobrancaAtualizarERP, usuario: str
) -> Cobranca:
    c = await _get_cobranca_ou_404(db, cobranca_id)
    if dados.numero_erp is not None:
        c.numero_erp  = dados.numero_erp
    if dados.observacoes is not None:
        c.observacoes = dados.observacoes
    c.atualizado_por = usuario
    await db.flush()
    return c


async def registrar_recebimento(
    db: AsyncSession, cobranca_id: UUID, dados: RecebimentoCreate, usuario: str
) -> Cobranca:
    c = await _get_cobranca_ou_404(db, cobranca_id)
    if c.status == StatusCobranca.CANCELADA:
        raise HTTPException(status_code=400, detail="Cobrança cancelada — não é possível registrar recebimento.")
    if c.status == StatusCobranca.RECEBIDA:
        raise HTTPException(status_code=400, detail="Cobrança já foi totalmente recebida.")

    db.add(Recebimento(
        cobranca_id      = cobranca_id,
        data_recebimento = dados.data_recebimento,
        valor            = dados.valor,
        forma            = dados.forma,
        banco            = dados.banco,
        agencia          = dados.agencia,
        conta            = dados.conta,
        identificador    = dados.identificador,
        observacoes      = dados.observacoes,
        criado_por       = usuario,
    ))
    await db.flush()
    await db.refresh(c)

    # Sincroniza com a fatura
    from app.models.fatura import Fatura, StatusFatura
    fatura = await db.get(Fatura, c.fatura_id)
    if fatura and c.status == StatusCobranca.RECEBIDA:
        fatura.status         = StatusFatura.PAGA
        fatura.valor_pago     = c.valor_recebido
        fatura.data_pagamento = dados.data_recebimento
        fatura.atualizado_por = usuario
    await db.flush()
    return c


async def cancelar_recebimento(
    db: AsyncSession, recebimento_id: UUID, usuario: str
) -> None:
    rec = await db.get(Recebimento, recebimento_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recebimento não encontrado.")
    await db.delete(rec)
    await db.flush()


async def registrar_negociacao(
    db: AsyncSession, cobranca_id: UUID, dados: NegociacaoCreate, usuario: str
) -> Negociacao:
    c = await _get_cobranca_ou_404(db, cobranca_id)
    neg = Negociacao(
        cobranca_id     = cobranca_id,
        valor_original  = c.valor_original,
        valor_negociado = dados.valor_negociado,
        motivo          = dados.motivo,
        condicoes       = dados.condicoes,
        num_parcelas    = dados.num_parcelas,
        data_negociacao = date.today(),
        criado_por      = usuario,
    )
    db.add(neg)
    c.status         = StatusCobranca.NEGOCIADA
    c.atualizado_por = usuario
    await db.flush()
    await db.refresh(neg)
    return neg


async def aprovar_negociacao(
    db: AsyncSession, negociacao_id: UUID, usuario: str
) -> Negociacao:
    neg = await db.get(Negociacao, negociacao_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negociação não encontrada.")
    neg.status        = StatusNegociacao.APROVADA
    neg.aprovado_por  = usuario
    neg.data_aprovacao = date.today()
    await db.flush()
    return neg


async def resumo_aging(db: AsyncSession) -> list[dict]:
    rows = await db.execute(text("""
        SELECT
            faixa_aging                             AS faixa,
            COUNT(*)                                AS quantidade,
            COALESCE(SUM(valor_saldo), 0)           AS valor_total
        FROM vw_aging
        WHERE status NOT IN ('RECEBIDA','CANCELADA')
        GROUP BY faixa_aging
        ORDER BY
            CASE faixa_aging
                WHEN 'A_VENCER'   THEN 1
                WHEN '1_A_30'     THEN 2
                WHEN '31_A_60'    THEN 3
                WHEN '61_A_90'    THEN 4
                WHEN 'ACIMA_90'   THEN 5
                ELSE 6
            END
    """))
    return [dict(r._mapping) for r in rows]


# ==================================================================
# ROUTER
# ==================================================================

router = APIRouter(tags=["Contas a Receber"])


def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


@router.get("/contas-receber", summary="Lista cobranças com filtros e aging")
async def listar(
    pagina:      int           = Query(1, ge=1),
    por_pagina:  int           = Query(20, ge=1, le=100),
    status:      Optional[str] = Query(None),
    cliente_id:  Optional[UUID]= Query(None),
    competencia: Optional[date]= Query(None),
    em_atraso:   bool          = Query(False),
    faixa_aging: Optional[str] = Query(None, description="A_VENCER | 1_A_30 | 31_A_60 | 61_A_90 | ACIMA_90"),
    db: AsyncSession = Depends(get_db),
):
    return await listar_cobrancas(db, pagina, por_pagina, status, cliente_id, competencia, em_atraso, faixa_aging)


@router.get("/contas-receber/aging", summary="Resumo de aging por faixa de vencimento")
async def aging(db: AsyncSession = Depends(get_db)):
    return await resumo_aging(db)


@router.get("/contas-receber/{cobranca_id}", response_model=CobrancaOut, summary="Detalhe da cobrança")
async def buscar(cobranca_id: UUID, db: AsyncSession = Depends(get_db)):
    return await buscar_cobranca(db, cobranca_id)


@router.patch("/contas-receber/{cobranca_id}/erp", response_model=CobrancaOut,
              summary="Vincula número do ERP à cobrança")
async def atualizar(
    cobranca_id: UUID,
    dados: CobrancaAtualizarERP,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await atualizar_erp(db, cobranca_id, dados, usuario)


@router.post("/contas-receber/{cobranca_id}/recebimentos",
             response_model=CobrancaOut, status_code=status.HTTP_201_CREATED,
             summary="Registra baixa de pagamento (boleto, PIX, TED, etc.)")
async def receber(
    cobranca_id: UUID,
    dados: RecebimentoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await registrar_recebimento(db, cobranca_id, dados, usuario)


@router.delete("/contas-receber/recebimentos/{recebimento_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Cancela um recebimento registrado por engano")
async def cancelar(
    recebimento_id: UUID,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    await cancelar_recebimento(db, recebimento_id, usuario)


@router.post("/contas-receber/{cobranca_id}/negociacoes",
             status_code=status.HTTP_201_CREATED,
             summary="Registra negociação para cobrança inadimplente")
async def negociar(
    cobranca_id: UUID,
    dados: NegociacaoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await registrar_negociacao(db, cobranca_id, dados, usuario)


@router.patch("/contas-receber/negociacoes/{negociacao_id}/aprovar",
              summary="Aprova uma negociação pendente")
async def aprovar(
    negociacao_id: UUID,
    db: AsyncSession = Depends(get_db),
    usuario: str = Depends(get_usuario_atual),
):
    return await aprovar_negociacao(db, negociacao_id, usuario)
