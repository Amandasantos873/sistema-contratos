"""
Módulo 10 — DRE Gerencial
Service + Router

Alimentado automaticamente pelos módulos 07 e 08.
Oferece visão mensal, acumulada e simplificada para dashboard.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query

from app.database import get_db


# ================================================================
# SCHEMAS
# ================================================================

class DREMensalOut(BaseModel):
    mes:                    date
    # Receita
    receita_asp:            Decimal
    receita_bsp:            Decimal
    receita_bpo:            Decimal
    receita_bruta:          Decimal
    # Deduções
    deducoes_impostos:      Decimal
    receita_liquida:        Decimal
    # Custos
    custo_folha:            Decimal
    custo_beneficios:       Decimal
    custo_fornecedores:     Decimal
    total_custos:           Decimal
    lucro_bruto:            Decimal
    # Despesas operacionais
    desp_administrativa:    Decimal
    desp_comissoes:         Decimal
    desp_outros:            Decimal
    total_desp_operacionais:Decimal
    # Resultados
    ebitda:                 Decimal
    margem_ebitda_pct:      Decimal
    total_despesas:         Decimal
    resultado_liquido:      Decimal
    margem_liquida_pct:     Decimal

class DREAcumuladoOut(BaseModel):
    ano:                    int
    receita_bruta:          Decimal
    deducoes_impostos:      Decimal
    receita_liquida:        Decimal
    total_custos:           Decimal
    lucro_bruto:            Decimal
    total_desp_operacionais:Decimal
    ebitda:                 Decimal
    margem_ebitda_pct:      Decimal
    resultado_liquido:      Decimal
    margem_liquida_pct:     Decimal

class DREDashboardOut(BaseModel):
    mes:               date
    receita_bruta:     Decimal
    total_despesas:    Decimal
    ebitda:            Decimal
    margem_ebitda_pct: Decimal
    resultado_liquido: Decimal
    margem_liquida_pct:Decimal


# ================================================================
# SERVICE
# ================================================================

async def dre_mensal(
    db:          AsyncSession,
    ano:         Optional[int] = None,
    mes_inicio:  Optional[date]= None,
    mes_fim:     Optional[date]= None,
) -> list[DREMensalOut]:
    """Retorna o DRE mês a mês com todas as linhas gerenciais."""
    if ano:
        filtro = "EXTRACT(YEAR FROM mes) = :ano"
        params = {"ano": ano}
    elif mes_inicio and mes_fim:
        filtro = "mes BETWEEN DATE_TRUNC('month',:ini::date) AND DATE_TRUNC('month',:fim::date)"
        params = {"ini": mes_inicio, "fim": mes_fim}
    else:
        # Padrão: ano atual
        filtro = "EXTRACT(YEAR FROM mes) = EXTRACT(YEAR FROM CURRENT_DATE)"
        params = {}

    rows = await db.execute(text(f"SELECT * FROM vw_dre_mensal WHERE {filtro} ORDER BY mes"), params)
    return [DREMensalOut.model_validate(dict(r._mapping)) for r in rows]


async def dre_acumulado(db: AsyncSession, ano: Optional[int] = None) -> list[DREAcumuladoOut]:
    """Retorna o DRE acumulado por ano."""
    filtro = "ano = :ano" if ano else "1=1"
    params = {"ano": ano} if ano else {}
    rows = await db.execute(text(f"SELECT * FROM vw_dre_acumulado_ano WHERE {filtro} ORDER BY ano DESC"), params)
    return [DREAcumuladoOut.model_validate(dict(r._mapping)) for r in rows]


async def dre_dashboard(db: AsyncSession) -> list[DREDashboardOut]:
    """Últimos 6 meses simplificados — para o dashboard."""
    rows = await db.execute(text("SELECT * FROM vw_dre_dashboard ORDER BY mes"))
    return [DREDashboardOut.model_validate(dict(r._mapping)) for r in rows]


async def comparativo_mensal(
    db:  AsyncSession,
    ano: int,
) -> dict:
    """
    Compara cada mês com o mesmo mês do ano anterior.
    Útil para análise de crescimento YoY (Year over Year).
    """
    rows = await db.execute(text("""
        SELECT
            a.mes,
            a.receita_bruta                             AS receita_atual,
            COALESCE(b.receita_bruta, 0)                AS receita_anterior,
            CASE WHEN COALESCE(b.receita_bruta,0) > 0
                 THEN ROUND((a.receita_bruta - b.receita_bruta) / b.receita_bruta * 100, 2)
                 ELSE NULL END                          AS variacao_receita_pct,
            a.ebitda                                    AS ebitda_atual,
            COALESCE(b.ebitda, 0)                       AS ebitda_anterior,
            a.margem_ebitda_pct                         AS margem_atual,
            COALESCE(b.margem_ebitda_pct, 0)            AS margem_anterior
        FROM vw_dre_mensal a
        LEFT JOIN vw_dre_mensal b
            ON DATE_TRUNC('month', b.mes) = DATE_TRUNC('month', a.mes - INTERVAL '1 year')
        WHERE EXTRACT(YEAR FROM a.mes) = :ano
        ORDER BY a.mes
    """), {"ano": ano})
    return {"ano": ano, "comparativo": [dict(r._mapping) for r in rows]}


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(tags=["DRE Gerencial"])


@router.get("/dre/mensal", response_model=list[DREMensalOut],
            summary="DRE gerencial completo mês a mês")
async def mensal(
    ano:        Optional[int]  = Query(None, description="Filtrar por ano (padrão: ano atual)"),
    mes_inicio: Optional[date] = Query(None),
    mes_fim:    Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await dre_mensal(db, ano, mes_inicio, mes_fim)


@router.get("/dre/acumulado", response_model=list[DREAcumuladoOut],
            summary="DRE acumulado por ano")
async def acumulado(
    ano: Optional[int] = Query(None),
    db:  AsyncSession  = Depends(get_db),
):
    return await dre_acumulado(db, ano)


@router.get("/dre/dashboard", response_model=list[DREDashboardOut],
            summary="DRE simplificado — últimos 6 meses para o dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await dre_dashboard(db)


@router.get("/dre/comparativo/{ano}",
            summary="Comparativo YoY — cada mês vs mesmo mês do ano anterior")
async def comparativo(
    ano: int,
    db:  AsyncSession = Depends(get_db),
):
    return await comparativo_mensal(db, ano)
