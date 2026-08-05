"""
Módulo 09 — Fluxo de Caixa
Service + Router

Alimentado automaticamente pelos módulos 07 (Contas a Receber) e 08 (Contas a Pagar).
Nenhum lançamento manual necessário.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.database import get_db


# ================================================================
# SCHEMAS
# ================================================================

class FluxoMensalOut(BaseModel):
    mes:                       date
    entradas_realizadas:       Decimal
    entradas_projetadas:       Decimal
    saidas_realizadas:         Decimal
    saidas_projetadas:         Decimal
    saldo_realizado:           Decimal
    saldo_projetado:           Decimal
    desvio_entradas:           Decimal
    desvio_saidas:             Decimal
    saldo_acumulado_realizado: Decimal
    saldo_acumulado_projetado: Decimal

class FluxoDiarioOut(BaseModel):
    data:          date
    sentido:       str       # ENTRADA | SAIDA
    natureza:      str       # REALIZADO | PROJETADO
    descricao:     str
    categoria:     str
    origem_tipo:   str
    origem_numero: str
    valor:         Decimal

class ResumoFluxoOut(BaseModel):
    """Resumo do mês atual para o dashboard."""
    mes_atual:              date
    entradas_realizadas:    Decimal
    entradas_projetadas:    Decimal
    saidas_realizadas:      Decimal
    saidas_projetadas:      Decimal
    saldo_realizado:        Decimal
    saldo_projetado:        Decimal
    cobertura_dias:         int       # quantos dias o caixa cobre com o saldo projetado


# ================================================================
# SERVICE
# ================================================================

async def listar_fluxo_mensal(
    db:         AsyncSession,
    ano:        Optional[int] = None,
    meses_atras:int = 3,
    meses_frente:int = 3,
) -> list[FluxoMensalOut]:
    """
    Retorna o fluxo mensal projetado x realizado.
    Por padrão: 3 meses anteriores + mês atual + 3 meses à frente.
    """
    if ano:
        params = {"ano": ano}
        filtro = "EXTRACT(YEAR FROM mes) = :ano"
    else:
        params = {"atras": meses_atras, "frente": meses_frente}
        filtro = """
            mes >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month' * :atras
            AND mes <= DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' * :frente
        """

    rows = await db.execute(text(f"""
        SELECT
            f.mes,
            f.entradas_realizadas,
            f.entradas_projetadas,
            f.saidas_realizadas,
            f.saidas_projetadas,
            f.saldo_realizado,
            f.saldo_projetado,
            f.desvio_entradas,
            f.desvio_saidas,
            COALESCE(s.saldo_acumulado_realizado, 0) AS saldo_acumulado_realizado,
            COALESCE(s.saldo_acumulado_projetado, 0) AS saldo_acumulado_projetado
        FROM vw_fluxo_caixa_mensal f
        LEFT JOIN vw_saldo_acumulado s ON s.mes = f.mes
        WHERE {filtro}
        ORDER BY f.mes
    """), params)

    return [FluxoMensalOut.model_validate(dict(r._mapping)) for r in rows]


async def listar_fluxo_diario(
    db:  AsyncSession,
    mes: date,
) -> list[FluxoDiarioOut]:
    """
    Drill-down diário de um mês específico.
    Retorna todas as entradas e saídas realizadas e projetadas do mês.
    """
    rows = await db.execute(text("""
        SELECT data, sentido, natureza, descricao, categoria,
               origem_tipo, origem_numero, valor
        FROM vw_fluxo_caixa_diario
        WHERE DATE_TRUNC('month', data) = DATE_TRUNC('month', :mes::date)
        ORDER BY data, sentido, descricao
    """), {"mes": mes})

    return [FluxoDiarioOut.model_validate(dict(r._mapping)) for r in rows]


async def resumo_mes_atual(db: AsyncSession) -> ResumoFluxoOut:
    """Resumo do mês atual para o painel do dashboard."""
    row = await db.execute(text("""
        SELECT
            mes,
            entradas_realizadas,
            entradas_projetadas,
            saidas_realizadas,
            saidas_projetadas,
            saldo_realizado,
            saldo_projetado
        FROM vw_fluxo_caixa_mensal
        WHERE mes = DATE_TRUNC('month', CURRENT_DATE)
        LIMIT 1
    """))
    dados = row.fetchone()

    if not dados:
        hoje = date.today().replace(day=1)
        return ResumoFluxoOut(
            mes_atual=hoje, entradas_realizadas=0, entradas_projetadas=0,
            saidas_realizadas=0, saidas_projetadas=0,
            saldo_realizado=0, saldo_projetado=0, cobertura_dias=0
        )

    d = dict(dados._mapping)

    # Calcula cobertura: saldo projetado / (saídas projetadas / 30 dias)
    saidas_dia = Decimal(str(d["saidas_projetadas"])) / 30 if d["saidas_projetadas"] else Decimal("1")
    cobertura  = int(Decimal(str(d["saldo_projetado"])) / saidas_dia) if saidas_dia > 0 else 0

    return ResumoFluxoOut(
        mes_atual           = d["mes"],
        entradas_realizadas = d["entradas_realizadas"],
        entradas_projetadas = d["entradas_projetadas"],
        saidas_realizadas   = d["saidas_realizadas"],
        saidas_projetadas   = d["saidas_projetadas"],
        saldo_realizado     = d["saldo_realizado"],
        saldo_projetado     = d["saldo_projetado"],
        cobertura_dias      = max(0, cobertura),
    )


async def fluxo_por_categoria(
    db:  AsyncSession,
    mes: date,
) -> dict:
    """Breakdown por categoria para o mês — usado nos gráficos de composição."""
    entradas = await db.execute(text("""
        SELECT categoria, SUM(valor_realizado) AS realizado, SUM(valor_projetado) AS projetado
        FROM vw_entradas_realizadas WHERE DATE_TRUNC('month', data_realizada) = DATE_TRUNC('month', :mes::date) GROUP BY categoria
        UNION ALL
        SELECT categoria, 0, SUM(valor_projetado) FROM vw_entradas_projetadas WHERE DATE_TRUNC('month', data_prevista) = DATE_TRUNC('month', :mes::date) GROUP BY categoria
    """), {"mes": mes})

    saidas = await db.execute(text("""
        SELECT categoria, SUM(valor_realizado) AS realizado, SUM(valor_projetado) AS projetado
        FROM vw_saidas_realizadas WHERE DATE_TRUNC('month', data_realizada) = DATE_TRUNC('month', :mes::date) GROUP BY categoria
        UNION ALL
        SELECT categoria, 0, SUM(valor_projetado) FROM vw_saidas_projetadas WHERE DATE_TRUNC('month', data_prevista) = DATE_TRUNC('month', :mes::date) GROUP BY categoria
    """), {"mes": mes})

    return {
        "entradas": [dict(r._mapping) for r in entradas],
        "saidas":   [dict(r._mapping) for r in saidas],
    }


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(tags=["Fluxo de Caixa"])


@router.get(
    "/fluxo-caixa/mensal",
    response_model=list[FluxoMensalOut],
    summary="Fluxo de caixa mensal — projetado x realizado"
)
async def mensal(
    ano:          Optional[int] = Query(None,  description="Filtrar por ano (ex: 2026)"),
    meses_atras:  int           = Query(3,     ge=0, le=24),
    meses_frente: int           = Query(3,     ge=0, le=24),
    db: AsyncSession = Depends(get_db),
):
    return await listar_fluxo_mensal(db, ano, meses_atras, meses_frente)


@router.get(
    "/fluxo-caixa/diario",
    response_model=list[FluxoDiarioOut],
    summary="Drill-down diário de um mês — todas as entradas e saídas"
)
async def diario(
    mes: date        = Query(..., description="Qualquer dia do mês desejado (ex: 2026-06-01)"),
    db: AsyncSession = Depends(get_db),
):
    return await listar_fluxo_diario(db, mes)


@router.get(
    "/fluxo-caixa/resumo",
    response_model=ResumoFluxoOut,
    summary="Resumo do mês atual — para o dashboard"
)
async def resumo(db: AsyncSession = Depends(get_db)):
    return await resumo_mes_atual(db)


@router.get(
    "/fluxo-caixa/categorias",
    summary="Breakdown de entradas e saídas por categoria em um mês"
)
async def categorias(
    mes: date        = Query(..., description="Qualquer dia do mês desejado"),
    db: AsyncSession = Depends(get_db),
):
    return await fluxo_por_categoria(db, mes)
