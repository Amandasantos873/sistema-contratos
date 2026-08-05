"""
Módulo 11 — Conciliação Bancária
Service + Router

Fluxo:
  1. Usuário digita lançamentos do extrato
  2. Sistema busca sugestões automáticas por valor ± R$0,10 e data ± 3 dias
  3. Usuário confirma, corrige ou ignora cada sugestão
  4. Lançamento conciliado atualiza o sistema de origem (recebimento/despesa)
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from math import ceil

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status as http_status
from pydantic import BaseModel, Field

from app.database import get_db


# ================================================================
# SCHEMAS
# ================================================================

class ContaBancariaOut(BaseModel):
    id:                 int
    banco:              str
    agencia:            str
    conta:              str
    descricao:          Optional[str]
    saldo_atual:        Decimal
    pendentes:          int
    conciliados:        int
    divergentes:        int
    creditos_pendentes: Decimal
    debitos_pendentes:  Decimal
    model_config = {"from_attributes": True}

class ContaBancariaUpdate(BaseModel):
    banco:    str
    agencia:  str
    conta:    str
    descricao:Optional[str] = None

class ExtratoBancarioCreate(BaseModel):
    data_lancamento:  date
    data_compensacao: Optional[date] = None
    tipo:             str = Field(..., pattern="^(CREDITO|DEBITO)$")
    valor:            Decimal = Field(..., gt=0)
    descricao:        str = Field(..., min_length=3, max_length=300)
    documento:        Optional[str] = None
    saldo_apos:       Optional[Decimal] = None
    observacoes:      Optional[str] = None

class ExtratoOut(BaseModel):
    id:                UUID
    data_lancamento:   date
    tipo:              str
    valor:             Decimal
    descricao:         str
    documento:         Optional[str]
    status_conciliacao:str
    origem:            Optional[str]
    origem_numero:     Optional[str]
    conciliado_em:     Optional[str]
    conciliado_por:    Optional[str]
    model_config = {"from_attributes": True}

class SugestaoOut(BaseModel):
    origem:        str
    origem_id:     UUID
    origem_numero: str
    descricao:     str
    valor:         Decimal
    data_ref:      date
    score:         int

class ConciliarRequest(BaseModel):
    origem_id:     UUID
    origem:        str = Field(..., pattern="^(RECEBIMENTO|DESPESA|TRANSFERENCIA|OUTROS)$")
    origem_numero: str
    observacoes:   Optional[str] = None

class IgnorarRequest(BaseModel):
    motivo: Optional[str] = None


# ================================================================
# SERVICE
# ================================================================

async def _get_extrato_ou_404(db: AsyncSession, extrato_id: UUID):
    from app.models.conciliacao import ExtratoBancario
    e = await db.get(ExtratoBancario, extrato_id)
    if not e:
        raise HTTPException(status_code=404, detail="Lançamento do extrato não encontrado.")
    return e


async def get_posicao_bancaria(db: AsyncSession) -> list[dict]:
    rows = await db.execute(text("SELECT * FROM vw_posicao_bancaria"))
    return [dict(r._mapping) for r in rows]


async def atualizar_conta(db: AsyncSession, conta_id: int, dados: ContaBancariaUpdate, usuario: str) -> dict:
    await db.execute(text("""
        UPDATE contas_bancarias SET banco=:banco, agencia=:agencia, conta=:conta, descricao=:desc
        WHERE id = :id
    """), {"banco": dados.banco, "agencia": dados.agencia, "conta": dados.conta, "desc": dados.descricao, "id": conta_id})
    await db.flush()
    return {"status": "atualizado"}


async def listar_extrato(
    db:         AsyncSession,
    conta_id:   int = 1,
    pagina:     int = 1,
    por_pagina: int = 30,
    status:     Optional[str]  = None,
    tipo:       Optional[str]  = None,
    data_ini:   Optional[date] = None,
    data_fim:   Optional[date] = None,
) -> dict:
    params = {
        "conta_id":  conta_id,
        "status":    status,
        "tipo":      tipo,
        "data_ini":  data_ini,
        "data_fim":  data_fim,
        "limit":     por_pagina,
        "offset":    (pagina - 1) * por_pagina,
    }
    filtro = """
        conta_id = :conta_id
        AND (:status   IS NULL OR status_conciliacao = :status::status_conciliacao)
        AND (:tipo     IS NULL OR tipo = :tipo::tipo_lancamento_banco)
        AND (:data_ini IS NULL OR data_lancamento >= :data_ini)
        AND (:data_fim IS NULL OR data_lancamento <= :data_fim)
    """
    rows  = await db.execute(text(f"SELECT * FROM vw_conciliacao_resumo WHERE {filtro} LIMIT :limit OFFSET :offset"), params)
    total = (await db.execute(text(f"SELECT COUNT(*) FROM vw_conciliacao_resumo WHERE {filtro}"), params)).scalar()
    dados = [dict(r._mapping) for r in rows]
    return {
        "dados": dados,
        "meta": {"total": total, "pagina": pagina, "por_pagina": por_pagina, "paginas": ceil(total / por_pagina) if total else 0}
    }


async def criar_lancamento(
    db:       AsyncSession,
    conta_id: int,
    dados:    ExtratoBancarioCreate,
    usuario:  str,
) -> dict:
    result = await db.execute(text("""
        INSERT INTO extratos_bancarios
            (conta_id, data_lancamento, data_compensacao, tipo, valor, descricao,
             documento, saldo_apos, observacoes, criado_por)
        VALUES
            (:conta_id, :data, :data_comp, :tipo::tipo_lancamento_banco, :valor,
             :descricao, :doc, :saldo, :obs, :usuario)
        RETURNING id
    """), {
        "conta_id": conta_id,
        "data":     dados.data_lancamento,
        "data_comp":dados.data_compensacao,
        "tipo":     dados.tipo,
        "valor":    dados.valor,
        "descricao":dados.descricao,
        "doc":      dados.documento,
        "saldo":    dados.saldo_apos,
        "obs":      dados.observacoes,
        "usuario":  usuario,
    })
    await db.flush()
    novo_id = result.scalar()
    return {"id": str(novo_id), "status": "criado"}


async def buscar_sugestoes(
    db:                AsyncSession,
    extrato_id:        UUID,
    tolerancia_valor:  float = 0.10,
    tolerancia_dias:   int   = 3,
) -> list[SugestaoOut]:
    rows = await db.execute(text("""
        SELECT * FROM fn_sugestoes_conciliacao(
            :eid::uuid, :tv::numeric, :td::integer
        )
    """), {"eid": str(extrato_id), "tv": tolerancia_valor, "td": tolerancia_dias})
    return [SugestaoOut.model_validate(dict(r._mapping)) for r in rows]


async def conciliar(
    db:         AsyncSession,
    extrato_id: UUID,
    dados:      ConciliarRequest,
    usuario:    str,
) -> dict:
    # Verifica se o lançamento existe e está pendente
    row = await db.execute(
        text("SELECT status_conciliacao FROM extratos_bancarios WHERE id = :id"),
        {"id": str(extrato_id)}
    )
    status_atual = row.scalar()
    if not status_atual:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    if status_atual == "CONCILIADO":
        raise HTTPException(status_code=400, detail="Lançamento já foi conciliado.")

    await db.execute(text("""
        UPDATE extratos_bancarios SET
            status_conciliacao = 'CONCILIADO',
            origem             = :origem::origem_lancamento,
            origem_id          = :origem_id::uuid,
            origem_numero      = :origem_numero,
            conciliado_em      = NOW(),
            conciliado_por     = :usuario,
            observacoes        = COALESCE(:obs, observacoes),
            atualizado_em      = NOW()
        WHERE id = :id
    """), {
        "id":           str(extrato_id),
        "origem":       dados.origem,
        "origem_id":    str(dados.origem_id),
        "origem_numero":dados.origem_numero,
        "usuario":      usuario,
        "obs":          dados.observacoes,
    })

    # Marca despesa como conciliada se aplicável
    if dados.origem == "DESPESA":
        await db.execute(text("""
            UPDATE despesas SET status='CONCILIADA', conciliado=TRUE,
                conciliado_em=NOW(), conciliado_por=:usuario
            WHERE id=:id AND status='PAGA'
        """), {"id": str(dados.origem_id), "usuario": usuario})

    await db.flush()
    return {"extrato_id": str(extrato_id), "status": "CONCILIADO", "origem": dados.origem_numero}


async def ignorar(
    db:         AsyncSession,
    extrato_id: UUID,
    dados:      IgnorarRequest,
    usuario:    str,
) -> dict:
    await db.execute(text("""
        UPDATE extratos_bancarios SET
            status_conciliacao = 'IGNORADO',
            observacoes        = COALESCE(:motivo, observacoes),
            conciliado_por     = :usuario,
            conciliado_em      = NOW(),
            atualizado_em      = NOW()
        WHERE id = :id
    """), {"id": str(extrato_id), "motivo": dados.motivo, "usuario": usuario})
    await db.flush()
    return {"extrato_id": str(extrato_id), "status": "IGNORADO"}


async def marcar_divergente(db: AsyncSession, extrato_id: UUID, usuario: str) -> dict:
    await db.execute(text("""
        UPDATE extratos_bancarios SET
            status_conciliacao = 'DIVERGENTE',
            conciliado_por     = :usuario,
            atualizado_em      = NOW()
        WHERE id = :id
    """), {"id": str(extrato_id), "usuario": usuario})
    await db.flush()
    return {"extrato_id": str(extrato_id), "status": "DIVERGENTE"}


async def resumo_periodo(db: AsyncSession, conta_id: int, mes: date) -> dict:
    row = await db.execute(text("""
        SELECT
            COUNT(*)                                                            AS total,
            COUNT(CASE WHEN status_conciliacao='CONCILIADO' THEN 1 END)        AS conciliados,
            COUNT(CASE WHEN status_conciliacao='PENDENTE'   THEN 1 END)        AS pendentes,
            COUNT(CASE WHEN status_conciliacao='DIVERGENTE' THEN 1 END)        AS divergentes,
            SUM(CASE WHEN tipo='CREDITO' THEN valor ELSE 0 END)                AS total_creditos,
            SUM(CASE WHEN tipo='DEBITO'  THEN valor ELSE 0 END)                AS total_debitos,
            SUM(CASE WHEN tipo='CREDITO' THEN valor ELSE -valor END)           AS saldo_periodo
        FROM extratos_bancarios
        WHERE conta_id = :cid
          AND DATE_TRUNC('month', data_lancamento) = DATE_TRUNC('month', :mes::date)
    """), {"cid": conta_id, "mes": mes})
    return dict(row.fetchone()._mapping)


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(tags=["Conciliação Bancária"])


def _u(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


@router.get("/conciliacao/conta", summary="Posição da conta bancária")
async def posicao(db: AsyncSession = Depends(get_db)):
    return await get_posicao_bancaria(db)


@router.patch("/conciliacao/conta/{conta_id}", summary="Atualiza dados da conta bancária")
async def atualizar(conta_id: int, dados: ContaBancariaUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    return await atualizar_conta(db, conta_id, dados, _u(request))


@router.get("/conciliacao/extrato", summary="Lista lançamentos do extrato")
async def listar(
    conta_id:  int            = Query(1),
    pagina:    int            = Query(1, ge=1),
    por_pagina:int            = Query(30, ge=1, le=100),
    status:    Optional[str]  = Query(None, description="PENDENTE | CONCILIADO | IGNORADO | DIVERGENTE"),
    tipo:      Optional[str]  = Query(None, description="CREDITO | DEBITO"),
    data_ini:  Optional[date] = Query(None),
    data_fim:  Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await listar_extrato(db, conta_id, pagina, por_pagina, status, tipo, data_ini, data_fim)


@router.post("/conciliacao/extrato", status_code=http_status.HTTP_201_CREATED,
             summary="Digita lançamento do extrato bancário")
async def criar(
    dados:    ExtratoBancarioCreate,
    conta_id: int     = Query(1),
    request:  Request = None,
    db: AsyncSession  = Depends(get_db),
):
    return await criar_lancamento(db, conta_id, dados, _u(request))


@router.get("/conciliacao/extrato/{extrato_id}/sugestoes",
            response_model=list[SugestaoOut],
            summary="Busca sugestões automáticas de conciliação por valor e data")
async def sugestoes(
    extrato_id:       UUID,
    tolerancia_valor: float = Query(0.10, description="Tolerância em R$ (padrão: R$ 0,10)"),
    tolerancia_dias:  int   = Query(3,    description="Tolerância em dias (padrão: 3 dias)"),
    db: AsyncSession = Depends(get_db),
):
    return await buscar_sugestoes(db, extrato_id, tolerancia_valor, tolerancia_dias)


@router.post("/conciliacao/extrato/{extrato_id}/conciliar",
             summary="Confirma conciliação de um lançamento com um registro do sistema")
async def confirmar(
    extrato_id: UUID,
    dados:      ConciliarRequest,
    request:    Request,
    db: AsyncSession = Depends(get_db),
):
    return await conciliar(db, extrato_id, dados, _u(request))


@router.post("/conciliacao/extrato/{extrato_id}/ignorar",
             summary="Marca lançamento como ignorado (transferência entre contas, etc.)")
async def ignorar_lancamento(
    extrato_id: UUID,
    dados:      IgnorarRequest,
    request:    Request,
    db: AsyncSession = Depends(get_db),
):
    return await ignorar(db, extrato_id, dados, _u(request))


@router.post("/conciliacao/extrato/{extrato_id}/divergente",
             summary="Marca lançamento como divergente para investigação")
async def divergente(
    extrato_id: UUID,
    request:    Request,
    db: AsyncSession = Depends(get_db),
):
    return await marcar_divergente(db, extrato_id, _u(request))


@router.get("/conciliacao/resumo", summary="Resumo de conciliação de um mês")
async def resumo(
    mes:      date = Query(...),
    conta_id: int  = Query(1),
    db: AsyncSession = Depends(get_db),
):
    return await resumo_periodo(db, conta_id, mes)
