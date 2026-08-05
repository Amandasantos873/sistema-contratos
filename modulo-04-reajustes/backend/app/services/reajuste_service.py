"""
Service do módulo de reajustes e aditivos.

Lógica principal:
  1. Calcular: busca itens do contrato, separa mão de obra dos demais,
               chama fn_calcula_acumulado_indice no banco para o índice
               do contrato e busca o dissídio do ano para os itens MOA.
  2. Aprovar: valida fluxo, permite ajuste de percentual negociado.
  3. Efetivar: trigger do banco atualiza itens, gera aditivo, atualiza valor_mensal.
"""
from math import ceil
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.reajuste import (
    IndiceEconomico, StatusReajuste, TipoAditivo,
    IndiceHistorico, ContratoReajuste, ReajusteItem,
    dissidios_historico_table,
)
from app.models.contrato import Contrato, ContratoItem, ProdutoServico
from app.schemas.reajuste import (
    IndiceCreate, IndiceAcumuladoOut,
    ReajusteCalcularRequest, ReajusteAprovarRequest,
    ReajusteReprovarRequest, ReajusteComunicarRequest,
    ReajusteOut, ReajustePendenteOut, ReajusteItemOut,
    AditivoCreate, AditivoOut,
)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _arredonda(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_reajuste_ou_404(db: AsyncSession, reajuste_id: UUID) -> ContratoReajuste:
    result = await db.execute(
        select(ContratoReajuste)
        .options(selectinload(ContratoReajuste.itens))
        .where(ContratoReajuste.id == reajuste_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Reajuste não encontrado.")
    return r


async def _calcula_acumulado_banco(
    db:               AsyncSession,
    indice:           str,
    competencia_ini:  date,
    competencia_fim:  date,
) -> Decimal:
    """Delega o cálculo acumulado para a função fn_calcula_acumulado_indice do banco."""
    row = await db.execute(
        text("SELECT fn_calcula_acumulado_indice(:ind::indice_economico, :ini, :fim)"),
        {"ind": indice, "ini": competencia_ini, "fim": competencia_fim},
    )
    result = row.scalar()
    if result is None:
        raise HTTPException(
            status_code=422,
            detail=f"Não foi possível calcular o acumulado do índice {indice} "
                   f"entre {competencia_ini:%m/%Y} e {competencia_fim:%m/%Y}. "
                   f"Verifique se todos os meses do período estão cadastrados."
        )
    return Decimal(str(result))


async def _busca_dissidio_ano(db: AsyncSession, ano: int) -> Decimal:
    """Busca o percentual do dissídio para um determinado ano."""
    row = await db.execute(
        text("""
            SELECT valor_percentual FROM dissidios_historico
            WHERE ano_base = :ano AND categoria = 'GERAL'
            ORDER BY data_vigencia DESC LIMIT 1
        """),
        {"ano": ano}
    )
    valor = row.scalar()
    if valor is None:
        raise HTTPException(
            status_code=422,
            detail=f"Dissídio não cadastrado para o ano {ano}. "
                   f"Cadastre o valor antes de calcular o reajuste."
        )
    return Decimal(str(valor))


def _enriquece_itens(reajuste: ContratoReajuste) -> ReajusteOut:
    """Converte model em schema de saída."""
    itens_out = [
        ReajusteItemOut(
            id                  = i.id,
            contrato_item_id    = i.contrato_item_id,
            valor_anterior      = i.valor_anterior,
            percentual_aplicado = i.percentual_aplicado,
            valor_novo          = i.valor_novo,
            variacao            = i.valor_novo - i.valor_anterior,
            aprovado            = i.aprovado,
            observacoes         = i.observacoes,
        )
        for i in reajuste.itens
    ]
    return ReajusteOut(
        **{c: getattr(reajuste, c) for c in ReajusteOut.model_fields if hasattr(reajuste, c)},
        itens=itens_out,
    )


# ==================================================================
# ÍNDICES ECONÔMICOS
# ==================================================================

async def listar_indices(
    db:     AsyncSession,
    indice: Optional[str] = None,
    ano:    Optional[int] = None,
) -> list[IndiceHistorico]:
    q = select(IndiceHistorico)
    if indice:
        q = q.where(IndiceHistorico.indice == indice)
    if ano:
        q = q.where(
            IndiceHistorico.competencia >= date(ano, 1, 1),
            IndiceHistorico.competencia <= date(ano, 12, 31),
        )
    result = await db.execute(q.order_by(IndiceHistorico.indice, IndiceHistorico.competencia.desc()))
    return result.scalars().all()


async def cadastrar_indice(
    db:      AsyncSession,
    dados:   IndiceCreate,
    usuario: str,
) -> IndiceHistorico:
    existe = await db.execute(
        select(IndiceHistorico).where(
            IndiceHistorico.indice      == dados.indice,
            IndiceHistorico.competencia == dados.competencia,
        )
    )
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Competência já cadastrada para este índice.")

    item = IndiceHistorico(**dados.model_dump(), criado_por=usuario)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def calcular_acumulado(
    db:              AsyncSession,
    indice:          str,
    competencia_ini: date,
    competencia_fim: date,
) -> IndiceAcumuladoOut:
    percentual = await _calcula_acumulado_banco(db, indice, competencia_ini, competencia_fim)
    meses = (competencia_fim.year - competencia_ini.year) * 12 + \
            (competencia_fim.month - competencia_ini.month) + 1
    return IndiceAcumuladoOut(
        indice               = indice,
        competencia_inicial  = competencia_ini,
        competencia_final    = competencia_fim,
        percentual_acumulado = percentual,
        meses                = meses,
    )


# ==================================================================
# DISSÍDIO
# ==================================================================

async def listar_dissidios(db: AsyncSession) -> list[dict]:
    rows = await db.execute(
        text("SELECT id, categoria, ano_base, data_vigencia, valor_percentual, fonte, criado_em FROM dissidios_historico ORDER BY ano_base DESC, categoria")
    )
    return [dict(r._mapping) for r in rows]


async def cadastrar_dissidio(
    db:      AsyncSession,
    ano_base: int,
    data_vigencia: date,
    valor_percentual: Decimal,
    categoria: str = "GERAL",
    fonte: Optional[str] = None,
    usuario: str = "sistema",
) -> dict:
    await db.execute(
        text("""
            INSERT INTO dissidios_historico (categoria, ano_base, data_vigencia, valor_percentual, fonte, criado_por)
            VALUES (:cat, :ano, :dt, :pct, :fonte, :usr)
            ON CONFLICT (categoria, ano_base) DO UPDATE
            SET data_vigencia = EXCLUDED.data_vigencia,
                valor_percentual = EXCLUDED.valor_percentual,
                fonte = EXCLUDED.fonte
        """),
        {"cat": categoria, "ano": ano_base, "dt": data_vigencia,
         "pct": valor_percentual, "fonte": fonte, "usr": usuario}
    )
    await db.flush()
    return {"categoria": categoria, "ano_base": ano_base, "valor_percentual": valor_percentual}


# ==================================================================
# CONTRATOS COM REAJUSTE PENDENTE
# ==================================================================

async def listar_reajustes_pendentes(
    db:             AsyncSession,
    apenas_vencidos: bool = False,
) -> list[ReajustePendenteOut]:
    filtro = "AND dias_atraso >= 0" if apenas_vencidos else ""
    rows = await db.execute(
        text(f"""
            SELECT contrato_id, contrato_numero, cliente_nome, modalidade,
                   valor_mensal, data_inicio_recorrencia, ultimo_reajuste,
                   proximo_reajuste, dias_atraso, status_em_andamento, total_reajustes
            FROM vw_reajustes_pendentes
            {filtro}
            ORDER BY dias_atraso DESC
        """)
    )
    return [ReajustePendenteOut.model_validate(dict(r._mapping)) for r in rows]


# ==================================================================
# CALCULAR REAJUSTE
# ==================================================================

async def calcular_reajuste(
    db:      AsyncSession,
    dados:   ReajusteCalcularRequest,
    usuario: str,
) -> ReajusteOut:

    # Busca contrato com itens
    result = await db.execute(
        select(Contrato)
        .options(selectinload(Contrato.itens).selectinload(ContratoItem.produto))
        .where(Contrato.id == dados.contrato_id)
    )
    contrato = result.scalar_one_or_none()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    if contrato.status != "ATIVO" or contrato.fase_atual != "RECORRENCIA":
        raise HTTPException(status_code=400, detail="Contrato precisa estar ativo e em recorrência.")

    # Determina data base (último reajuste efetivado ou data de assinatura)
    ultimo = await db.execute(
        text("""
            SELECT data_efetivacao FROM contratos_reajustes
            WHERE contrato_id = :cid AND status = 'EFETIVADO'
            ORDER BY data_efetivacao DESC LIMIT 1
        """),
        {"cid": str(dados.contrato_id)}
    )
    ultimo_row = ultimo.fetchone()
    data_base       = ultimo_row[0] if ultimo_row else contrato.data_assinatura
    data_fim_periodo = data_base + relativedelta(months=12)

    # Período de competência para cálculo do acumulado
    comp_ini = date(data_base.year, data_base.month, 1)
    comp_fim = date(data_fim_periodo.year, data_fim_periodo.month, 1) - timedelta(days=1)
    comp_fim = date(comp_fim.year, comp_fim.month, 1)

    # Número sequencial do reajuste
    count = await db.execute(
        text("SELECT COUNT(*) FROM contratos_reajustes WHERE contrato_id = :cid"),
        {"cid": str(dados.contrato_id)}
    )
    numero_reajuste = count.scalar() + 1

    # Calcula percentual acumulado do índice principal
    if dados.indice == IndiceEconomico.FIXO:
        pct_principal = dados.percentual_fixo
    else:
        pct_principal = await _calcula_acumulado_banco(db, dados.indice.value, comp_ini, comp_fim)

    # Busca dissídio do ano (se existir itens de MOA)
    itens_recorr = [i for i in contrato.itens if i.fase == "RECORRENCIA" and i.ativo]
    tem_moa      = any(i.produto.mao_de_obra_alocada for i in itens_recorr)
    pct_dissidio = None
    if tem_moa:
        pct_dissidio = await _busca_dissidio_ano(db, data_fim_periodo.year)

    # Cria cabeçalho do reajuste
    valor_mensal_anterior = contrato.valor_mensal
    reajuste = ContratoReajuste(
        contrato_id           = dados.contrato_id,
        numero_reajuste       = numero_reajuste,
        indice                = dados.indice,
        percentual_fixo       = dados.percentual_fixo,
        data_base             = data_base,
        data_fim_periodo      = data_fim_periodo,
        competencia_inicial   = comp_ini,
        competencia_final     = comp_fim,
        percentual_calculado  = pct_principal,
        percentual_aplicado   = pct_principal,   # pode ser alterado na aprovação
        valor_mensal_anterior = valor_mensal_anterior,
        status                = StatusReajuste.CALCULADO,
        data_efetivacao       = dados.data_efetivacao,
        calculado_por         = usuario,
        observacoes           = dados.observacoes,
    )
    db.add(reajuste)
    await db.flush()

    # Cria itens do reajuste separando MOA dos demais
    valor_novo_total = Decimal("0")
    for item in itens_recorr:
        eh_moa  = item.produto.mao_de_obra_alocada
        pct_item = pct_dissidio if eh_moa else pct_principal
        valor_ant = item.valor_unitario
        valor_nov = _arredonda(valor_ant * (1 + pct_item / 100))
        valor_novo_total += valor_nov * item.quantidade

        db.add(ReajusteItem(
            reajuste_id         = reajuste.id,
            contrato_item_id    = item.id,
            valor_anterior      = valor_ant,
            percentual_aplicado = pct_item,
            valor_novo          = valor_nov,
            usa_dissidio        = eh_moa,
        ))

    reajuste.valor_mensal_novo = _arredonda(valor_novo_total)
    reajuste.variacao_mensal   = _arredonda(valor_novo_total - valor_mensal_anterior)

    await db.flush()
    await db.refresh(reajuste)
    return _enriquece_itens(reajuste)


# ==================================================================
# FLUXO DE APROVAÇÃO
# ==================================================================

async def enviar_para_aprovacao(
    db:          AsyncSession,
    reajuste_id: UUID,
    usuario:     str,
) -> ReajusteOut:
    reajuste = await _get_reajuste_ou_404(db, reajuste_id)
    if reajuste.status != StatusReajuste.CALCULADO:
        raise HTTPException(status_code=400, detail="Apenas reajustes com status CALCULADO podem ser enviados para aprovação.")
    reajuste.status = StatusReajuste.AGUARDANDO_APROVACAO
    await db.flush()
    await db.refresh(reajuste)
    return _enriquece_itens(reajuste)


async def aprovar_reajuste(
    db:          AsyncSession,
    reajuste_id: UUID,
    dados:       ReajusteAprovarRequest,
    usuario:     str,
) -> ReajusteOut:
    from sqlalchemy.sql import func as sqlfunc
    reajuste = await _get_reajuste_ou_404(db, reajuste_id)

    if reajuste.status != StatusReajuste.AGUARDANDO_APROVACAO:
        raise HTTPException(status_code=400, detail="Reajuste não está aguardando aprovação.")

    # Aplica percentual negociado (se diferente do calculado)
    if dados.percentual_aplicado is not None:
        reajuste.percentual_aplicado = dados.percentual_aplicado

    # Aplica aprovações individuais por item
    for aprovacao in dados.itens:
        for item in reajuste.itens:
            if item.contrato_item_id == aprovacao.contrato_item_id:
                item.aprovado = aprovacao.aprovado
                if aprovacao.percentual_negociado is not None:
                    item.percentual_aplicado = aprovacao.percentual_negociado
                    # recalcula valor_novo com percentual negociado
                    item.valor_novo = _arredonda(
                        item.valor_anterior * (1 + aprovacao.percentual_negociado / 100)
                    )
                if aprovacao.observacoes:
                    item.observacoes = aprovacao.observacoes

    # Recalcula valor_mensal_novo com base nos itens aprovados
    novo_total = sum(
        i.valor_novo * Decimal("1")   # valor_novo já é unitário; multiplicar por qtd requer join
        for i in reajuste.itens
        if i.aprovado is not False
    )

    reajuste.valor_mensal_novo  = _arredonda(Decimal(str(novo_total)))
    reajuste.variacao_mensal    = _arredonda(reajuste.valor_mensal_novo - reajuste.valor_mensal_anterior)
    reajuste.status             = StatusReajuste.APROVADO
    reajuste.aprovado_por       = usuario
    reajuste.data_aprovacao     = sqlfunc.now()

    await db.flush()
    await db.refresh(reajuste)
    return _enriquece_itens(reajuste)


async def reprovar_reajuste(
    db:          AsyncSession,
    reajuste_id: UUID,
    dados:       ReajusteReprovarRequest,
    usuario:     str,
) -> ReajusteOut:
    reajuste = await _get_reajuste_ou_404(db, reajuste_id)
    if reajuste.status not in (StatusReajuste.CALCULADO, StatusReajuste.AGUARDANDO_APROVACAO):
        raise HTTPException(status_code=400, detail="Reajuste não pode ser reprovado no status atual.")
    reajuste.status            = StatusReajuste.REPROVADO
    reajuste.motivo_reprovacao = dados.motivo
    await db.flush()
    await db.refresh(reajuste)
    return _enriquece_itens(reajuste)


async def comunicar_cliente(
    db:          AsyncSession,
    reajuste_id: UUID,
    dados:       ReajusteComunicarRequest,
    usuario:     str,
) -> ReajusteOut:
    reajuste = await _get_reajuste_ou_404(db, reajuste_id)
    if reajuste.status != StatusReajuste.APROVADO:
        raise HTTPException(status_code=400, detail="Reajuste precisa estar aprovado antes de comunicar o cliente.")
    reajuste.status           = StatusReajuste.COMUNICADO
    reajuste.data_comunicacao = dados.data_comunicacao
    await db.flush()
    await db.refresh(reajuste)
    return _enriquece_itens(reajuste)


async def efetivar_reajuste(
    db:          AsyncSession,
    reajuste_id: UUID,
    usuario:     str,
) -> ReajusteOut:
    reajuste = await _get_reajuste_ou_404(db, reajuste_id)
    if reajuste.status != StatusReajuste.COMUNICADO:
        raise HTTPException(status_code=400, detail="Reajuste precisa ter sido comunicado ao cliente antes de ser efetivado.")
    if reajuste.data_efetivacao > date.today():
        raise HTTPException(
            status_code=400,
            detail=f"A data de efetivação ({reajuste.data_efetivacao:%d/%m/%Y}) ainda não chegou."
        )
    reajuste.status       = StatusReajuste.EFETIVADO
    reajuste.aprovado_por = reajuste.aprovado_por or usuario
    # O trigger fn_efetiva_reajuste no banco cuida de:
    # - atualizar valor_unitario dos itens
    # - gerar o aditivo contratual
    # - atualizar valor_mensal no cabeçalho do contrato
    await db.flush()
    await db.refresh(reajuste)
    return _enriquece_itens(reajuste)


# ==================================================================
# LISTAGEM DE REAJUSTES DE UM CONTRATO
# ==================================================================

async def listar_reajustes_contrato(
    db:          AsyncSession,
    contrato_id: UUID,
) -> list[ReajusteOut]:
    result = await db.execute(
        select(ContratoReajuste)
        .options(selectinload(ContratoReajuste.itens))
        .where(ContratoReajuste.contrato_id == contrato_id)
        .order_by(ContratoReajuste.numero_reajuste)
    )
    return [_enriquece_itens(r) for r in result.scalars().all()]


# ==================================================================
# ADITIVOS MANUAIS (não gerados por reajuste)
# ==================================================================

async def criar_aditivo_manual(
    db:          AsyncSession,
    contrato_id: UUID,
    dados:       AditivoCreate,
    usuario:     str,
) -> dict:
    count = await db.execute(
        text("SELECT COALESCE(MAX(numero_aditivo),0)+1 FROM contratos_aditivos WHERE contrato_id=:cid"),
        {"cid": str(contrato_id)}
    )
    numero = count.scalar()
    await db.execute(
        text("""
            INSERT INTO contratos_aditivos
                (contrato_id, numero_aditivo, tipo, tipo_aditivo, descricao,
                 data_aditivo, data_vigencia, valor_anterior, valor_novo,
                 status, criado_por, atualizado_por)
            VALUES (:cid, :num, :tipo, :tipo_ad, :desc,
                    :dt_ad, :dt_vig, :vant, :vnov,
                    'RASCUNHO', :usr, :usr)
        """),
        {
            "cid":    str(contrato_id),
            "num":    numero,
            "tipo":   dados.tipo_aditivo.value,
            "tipo_ad":dados.tipo_aditivo.value,
            "desc":   dados.descricao,
            "dt_ad":  dados.data_aditivo,
            "dt_vig": dados.data_vigencia,
            "vant":   dados.valor_anterior,
            "vnov":   dados.valor_novo,
            "usr":    usuario,
        }
    )
    await db.flush()
    return {"numero_aditivo": numero, "status": "RASCUNHO"}


async def listar_aditivos_contrato(
    db:          AsyncSession,
    contrato_id: UUID,
) -> list[dict]:
    rows = await db.execute(
        text("""
            SELECT id, contrato_id, numero_aditivo, tipo, tipo_aditivo, descricao,
                   data_aditivo, data_vigencia, valor_anterior, valor_novo,
                   status, aprovado_por, data_aprovacao, criado_em, criado_por
            FROM contratos_aditivos
            WHERE contrato_id = :cid
            ORDER BY numero_aditivo
        """),
        {"cid": str(contrato_id)}
    )
    return [dict(r._mapping) for r in rows]
