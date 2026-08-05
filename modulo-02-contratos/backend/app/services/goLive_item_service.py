"""
Extensão do service de contratos — go-live por item individual.
Adicionar ao arquivo app/services/contrato_service.py existente.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.contrato import Contrato, ContratoItem, FaseContrato


# ==================================================================
# GO-LIVE POR ITEM
# ==================================================================

async def registrar_goLive_item(
    db:                    AsyncSession,
    contrato_id:           UUID,
    item_id:               UUID,
    data_goLive_item:      date,
    confirmado_por:        str,
) -> ContratoItem:
    """
    Registra o go-live de um item específico do contrato.
    O trigger fn_registra_goLive_item cuida de:
      - Atualizar status_item → ATIVO
      - Preencher data_inicio_faturamento
      - Se todos os itens recorrentes tiverem go-live, preencher o go-live do contrato
    """
    result = await db.execute(
        select(ContratoItem).where(
            ContratoItem.id          == item_id,
            ContratoItem.contrato_id == contrato_id,
            ContratoItem.fase        == FaseContrato.RECORRENCIA,
            ContratoItem.ativo       == True,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item recorrente não encontrado neste contrato.")

    if item.data_goLive_item:
        raise HTTPException(status_code=400, detail="Go-live já registrado para este item.")

    if data_goLive_item < item.contrato.data_inicio_impl if hasattr(item, "contrato") else False:
        raise HTTPException(status_code=400, detail="Data de go-live não pode ser anterior ao início da implantação.")

    item.data_goLive_item       = data_goLive_item
    item.goLive_confirmado_por  = confirmado_por
    # O trigger cuida do resto

    await db.flush()
    await db.refresh(item)
    return item


async def registrar_goLive_lote(
    db:           AsyncSession,
    contrato_id:  UUID,
    data_goLive:  date,
    usuario:      str,
    item_ids:     Optional[list[UUID]] = None,
) -> list[ContratoItem]:
    """
    Registra go-live para múltiplos itens de uma vez.
    Se item_ids for None, aplica a todos os itens recorrentes sem go-live.
    """
    query = select(ContratoItem).where(
        ContratoItem.contrato_id    == contrato_id,
        ContratoItem.fase           == FaseContrato.RECORRENCIA,
        ContratoItem.ativo          == True,
        ContratoItem.data_goLive_item == None,
    )
    if item_ids:
        query = query.where(ContratoItem.id.in_(item_ids))

    result = await db.execute(query)
    itens  = result.scalars().all()

    if not itens:
        raise HTTPException(status_code=404, detail="Nenhum item pendente de go-live encontrado.")

    for item in itens:
        item.data_goLive_item      = data_goLive
        item.goLive_confirmado_por = usuario

    await db.flush()
    for item in itens:
        await db.refresh(item)
    return itens


async def listar_itens_aguardando_goLive(
    db:          AsyncSession,
    contrato_id: Optional[UUID] = None,
) -> list[dict]:
    """Lista itens recorrentes ainda em implantação aguardando go-live."""
    filtro = "AND contrato_id = :cid" if contrato_id else ""
    rows = await db.execute(
        text(f"""
            SELECT item_id, contrato_id, contrato_numero, cliente_nome,
                   modalidade, produto_nome, valor_total,
                   data_inicio_impl, goLive_contrato, data_goLive_item,
                   status_item, dias_em_implantacao
            FROM vw_itens_aguardando_goLive
            {filtro}
            ORDER BY dias_em_implantacao DESC
        """),
        {"cid": str(contrato_id)} if contrato_id else {}
    )
    return [dict(r._mapping) for r in rows]


async def listar_itens_faturamento(
    db:              AsyncSession,
    dia_faturamento: str,
    competencia:     date,
) -> list[dict]:
    """
    Retorna itens elegíveis para faturamento em uma data de apuração específica.
    Considera apenas itens com data_inicio_faturamento <= competencia.
    Usado pelo Módulo 05.
    """
    rows = await db.execute(
        text("""
            SELECT item_id, contrato_id, contrato_numero, cliente_id, cliente_nome,
                   modalidade, dia_faturamento, produto_id, produto_nome,
                   produto_unidade, quantidade, valor_unitario, desconto_pct,
                   valor_total, data_inicio_faturamento
            FROM vw_itens_a_faturar
            WHERE dia_faturamento = :dia
              AND data_inicio_faturamento <= :competencia
            ORDER BY cliente_nome, produto_nome
        """),
        {"dia": dia_faturamento, "competencia": competencia}
    )
    return [dict(r._mapping) for r in rows]
