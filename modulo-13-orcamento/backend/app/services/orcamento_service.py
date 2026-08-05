"""
Módulo 13 — Orçamento x Realizado
Service + Router

Fluxo:
  1. Criar orçamento anual
  2. Definir meta anual de receita por modalidade → distribuída em 12 meses
  3. Definir meta anual de despesa por categoria → distribuída em 12 meses
  4. Ajustar meses individualmente se necessário
  5. Ativar orçamento
  6. Acompanhar orçado × realizado mês a mês
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.database import get_db


# ================================================================
# SCHEMAS
# ================================================================

class OrcamentoCreate(BaseModel):
    ano:       int   = Field(..., ge=2024, le=2030)
    descricao: Optional[str] = None

class OrcamentoOut(BaseModel):
    id:        int
    ano:       int
    descricao: Optional[str]
    status:    str
    model_config = {"from_attributes": True}

class MetaReceitaAnual(BaseModel):
    modalidade:   str   = Field(..., pattern="^(ASP|BSP|BPO|TOTAL)$")
    valor_anual:  Decimal = Field(..., gt=0)

class MetaDespesaAnual(BaseModel):
    categoria_id:    int
    centro_custo_id: int
    valor_anual:     Decimal = Field(..., gt=0)

class AjusteMensal(BaseModel):
    """Ajuste de um mês específico após a distribuição anual."""
    mes:         date
    valor_orcado:Decimal = Field(..., ge=0)

class OrcadoRealizadoOut(BaseModel):
    mes:             date
    valor_orcado:    Decimal
    valor_realizado: Decimal
    desvio:          Decimal
    atingimento_pct: Decimal
    model_config = {"from_attributes": True}


# ================================================================
# SERVICE
# ================================================================

async def criar_orcamento(db: AsyncSession, dados: OrcamentoCreate, usuario: str) -> dict:
    existe = await db.execute(text("SELECT id FROM orcamentos WHERE ano = :ano"), {"ano": dados.ano})
    if existe.scalar():
        raise HTTPException(status_code=409, detail=f"Já existe um orçamento para {dados.ano}.")
    result = await db.execute(text("""
        INSERT INTO orcamentos (ano, descricao, criado_por, atualizado_por)
        VALUES (:ano, :desc, :usuario, :usuario)
        RETURNING id, ano, descricao, status
    """), {"ano": dados.ano, "desc": dados.descricao, "usuario": usuario})
    await db.flush()
    return dict(result.fetchone()._mapping)


async def listar_orcamentos(db: AsyncSession) -> list:
    rows = await db.execute(text("SELECT * FROM orcamentos ORDER BY ano DESC"))
    return [dict(r._mapping) for r in rows]


async def ativar_orcamento(db: AsyncSession, orcamento_id: int, usuario: str) -> dict:
    # Desativa qualquer outro ativo do mesmo ano
    orc = await db.execute(text("SELECT ano FROM orcamentos WHERE id = :id"), {"id": orcamento_id})
    ano = orc.scalar()
    if not ano:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    await db.execute(text("""
        UPDATE orcamentos SET status='ENCERRADO', atualizado_por=:u, atualizado_em=NOW()
        WHERE ano=:ano AND status='ATIVO' AND id != :id
    """), {"ano": ano, "id": orcamento_id, "u": usuario})
    await db.execute(text("""
        UPDATE orcamentos SET status='ATIVO', atualizado_por=:u, atualizado_em=NOW()
        WHERE id=:id
    """), {"id": orcamento_id, "u": usuario})
    await db.flush()
    return {"orcamento_id": orcamento_id, "status": "ATIVO"}


async def definir_meta_receita(
    db: AsyncSession, orcamento_id: int, dados: MetaReceitaAnual, usuario: str
) -> dict:
    orc = await db.execute(text("SELECT ano FROM orcamentos WHERE id=:id"), {"id": orcamento_id})
    ano = orc.scalar()
    if not ano:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    await db.execute(text("""
        SELECT fn_distribuir_meta_receita(:oid, :mod, :val, :ano, :usuario)
    """), {"oid": orcamento_id, "mod": dados.modalidade, "val": dados.valor_anual, "ano": ano, "usuario": usuario})
    await db.flush()
    return {"orcamento_id": orcamento_id, "modalidade": dados.modalidade,
            "valor_anual": str(dados.valor_anual), "meses_gerados": 12}


async def definir_meta_despesa(
    db: AsyncSession, orcamento_id: int, dados: MetaDespesaAnual, usuario: str
) -> dict:
    orc = await db.execute(text("SELECT ano FROM orcamentos WHERE id=:id"), {"id": orcamento_id})
    ano = orc.scalar()
    if not ano:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    await db.execute(text("""
        SELECT fn_distribuir_meta_despesa(:oid, :cat, :cc, :val, :ano, :usuario)
    """), {"oid": orcamento_id, "cat": dados.categoria_id, "cc": dados.centro_custo_id,
           "val": dados.valor_anual, "ano": ano, "usuario": usuario})
    await db.flush()
    return {"orcamento_id": orcamento_id, "categoria_id": dados.categoria_id,
            "valor_anual": str(dados.valor_anual), "meses_gerados": 12}


async def ajustar_mes_receita(
    db: AsyncSession, orcamento_id: int, modalidade: str, dados: AjusteMensal, usuario: str
) -> dict:
    await db.execute(text("""
        UPDATE orcamento_receitas SET
            valor_orcado  = :valor,
            atualizado_em = NOW(),
            atualizado_por= :usuario
        WHERE orcamento_id = :oid AND modalidade = :mod
          AND DATE_TRUNC('month', mes) = DATE_TRUNC('month', :mes::date)
    """), {"valor": dados.valor_orcado, "usuario": usuario,
           "oid": orcamento_id, "mod": modalidade, "mes": dados.mes})
    await db.flush()
    return {"status": "ajustado"}


async def ajustar_mes_despesa(
    db: AsyncSession, orcamento_id: int, categoria_id: int,
    centro_custo_id: int, dados: AjusteMensal, usuario: str
) -> dict:
    await db.execute(text("""
        UPDATE orcamento_despesas SET
            valor_orcado  = :valor,
            atualizado_em = NOW(),
            atualizado_por= :usuario
        WHERE orcamento_id = :oid AND categoria_id = :cat
          AND centro_custo_id = :cc
          AND DATE_TRUNC('month', mes) = DATE_TRUNC('month', :mes::date)
    """), {"valor": dados.valor_orcado, "usuario": usuario, "oid": orcamento_id,
           "cat": categoria_id, "cc": centro_custo_id, "mes": dados.mes})
    await db.flush()
    return {"status": "ajustado"}


async def orcado_vs_realizado_receita(
    db: AsyncSession, ano: int, modalidade: Optional[str] = None
) -> list:
    filtro = "ano = :ano AND (:mod IS NULL OR modalidade = :mod)"
    rows = await db.execute(text(f"""
        SELECT mes, modalidade, valor_orcado, valor_realizado, desvio, atingimento_pct
        FROM vw_orcado_vs_realizado_receita
        WHERE {filtro} ORDER BY mes, modalidade
    """), {"ano": ano, "mod": modalidade})
    return [dict(r._mapping) for r in rows]


async def orcado_vs_realizado_despesa(
    db: AsyncSession, ano: int, tipo: Optional[str] = None
) -> list:
    filtro = "ano = :ano AND (:tipo IS NULL OR categoria_tipo = :tipo)"
    rows = await db.execute(text(f"""
        SELECT mes, categoria_tipo, categoria_nome, centro_custo_nome,
               valor_orcado, valor_realizado, desvio, atingimento_pct
        FROM vw_orcado_vs_realizado_despesa
        WHERE {filtro} ORDER BY mes, categoria_tipo, categoria_nome
    """), {"ano": ano, "tipo": tipo})
    return [dict(r._mapping) for r in rows]


async def resumo_anual(db: AsyncSession, ano: Optional[int] = None) -> list:
    filtro = "ano = :ano" if ano else "1=1"
    params = {"ano": ano} if ano else {}
    rows = await db.execute(text(f"SELECT * FROM vw_resumo_anual_orcamento WHERE {filtro}"), params)
    return [dict(r._mapping) for r in rows]


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(tags=["Orçamento x Realizado"])


def _u(r: Request) -> str:
    return r.headers.get("X-Usuario", "sistema")


@router.get("/orcamentos", summary="Lista orçamentos anuais")
async def listar(db: AsyncSession = Depends(get_db)):
    return await listar_orcamentos(db)


@router.post("/orcamentos", status_code=201, summary="Cria orçamento anual")
async def criar(dados: OrcamentoCreate, request: Request, db: AsyncSession = Depends(get_db)):
    return await criar_orcamento(db, dados, _u(request))


@router.patch("/orcamentos/{orcamento_id}/ativar", summary="Ativa o orçamento")
async def ativar(orcamento_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    return await ativar_orcamento(db, orcamento_id, _u(request))


@router.post("/orcamentos/{orcamento_id}/receita",
             summary="Define meta anual de receita por modalidade — distribui em 12 meses")
async def meta_receita(orcamento_id: int, dados: MetaReceitaAnual, request: Request, db: AsyncSession = Depends(get_db)):
    return await definir_meta_receita(db, orcamento_id, dados, _u(request))


@router.post("/orcamentos/{orcamento_id}/despesa",
             summary="Define meta anual de despesa por categoria — distribui em 12 meses")
async def meta_despesa(orcamento_id: int, dados: MetaDespesaAnual, request: Request, db: AsyncSession = Depends(get_db)):
    return await definir_meta_despesa(db, orcamento_id, dados, _u(request))


@router.patch("/orcamentos/{orcamento_id}/receita/{modalidade}/ajuste",
              summary="Ajusta meta de um mês específico de receita")
async def ajuste_receita(orcamento_id: int, modalidade: str, dados: AjusteMensal, request: Request, db: AsyncSession = Depends(get_db)):
    return await ajustar_mes_receita(db, orcamento_id, modalidade, dados, _u(request))


@router.patch("/orcamentos/{orcamento_id}/despesa/{categoria_id}/{centro_custo_id}/ajuste",
              summary="Ajusta meta de um mês específico de despesa")
async def ajuste_despesa(orcamento_id: int, categoria_id: int, centro_custo_id: int, dados: AjusteMensal, request: Request, db: AsyncSession = Depends(get_db)):
    return await ajustar_mes_despesa(db, orcamento_id, categoria_id, centro_custo_id, dados, _u(request))


@router.get("/orcamentos/realizado/receita", summary="Orçado × Realizado de receita por mês")
async def realizado_receita(
    ano:       int            = Query(...),
    modalidade:Optional[str]  = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await orcado_vs_realizado_receita(db, ano, modalidade)


@router.get("/orcamentos/realizado/despesa", summary="Orçado × Realizado de despesa por mês")
async def realizado_despesa(
    ano:  int           = Query(...),
    tipo: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await orcado_vs_realizado_despesa(db, ano, tipo)


@router.get("/orcamentos/resumo", summary="Resumo anual consolidado")
async def resumo(
    ano: Optional[int] = Query(None),
    db:  AsyncSession  = Depends(get_db),
):
    return await resumo_anual(db, ano)
