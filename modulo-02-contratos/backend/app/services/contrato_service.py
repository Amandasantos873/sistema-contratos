"""
Service do módulo de contratos.
Toda regra de negócio fica aqui.
"""
from uuid import UUID
from math import ceil
from typing import Optional
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.contrato import (
    Contrato, ContratoItem, ContratoParcela, ContratoAditivo, ContratoHistorico,
    ProdutoServico, StatusContrato, FaseContrato, ModalidadeContrato
)
from app.schemas.contrato import (
    ContratoCreate, ContratoUpdate, ContratoGoLive,
    ItemCreate, ItemUpdate,
    ParcelaCreate, ParcelaUpdate,
    ContratoListOut, ContratoResumoOut, PaginacaoMeta
)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

async def _busca_contrato_ou_404(db: AsyncSession, contrato_id: UUID) -> Contrato:
    result = await db.execute(
        select(Contrato)
        .options(
            selectinload(Contrato.itens).selectinload(ContratoItem.produto),
            selectinload(Contrato.parcelas_impl),
            selectinload(Contrato.aditivos),
        )
        .where(Contrato.id == contrato_id)
    )
    contrato = result.scalar_one_or_none()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    return contrato


def _registra_historico(db, contrato_id, campo, anterior, novo, usuario):
    db.add(ContratoHistorico(
        contrato_id    = contrato_id,
        operacao       = "U",
        campo_alterado = campo,
        valor_anterior = str(anterior) if anterior is not None else None,
        valor_novo     = str(novo) if novo is not None else None,
        alterado_por   = usuario,
    ))


# ------------------------------------------------------------------
# PRODUTOS/SERVIÇOS
# ------------------------------------------------------------------

async def listar_produtos(
    db:         AsyncSession,
    modalidade: Optional[ModalidadeContrato] = None,
    fase:       Optional[FaseContrato]       = None,
) -> list[ProdutoServico]:
    q = select(ProdutoServico).where(ProdutoServico.ativo == True)
    if modalidade:
        q = q.where(ProdutoServico.modalidade == modalidade)
    if fase == FaseContrato.IMPLANTACAO:
        q = q.where(ProdutoServico.permite_impl == True)
    elif fase == FaseContrato.RECORRENCIA:
        q = q.where(ProdutoServico.permite_recorr == True)
    result = await db.execute(q.order_by(ProdutoServico.nome))
    return result.scalars().all()


# ------------------------------------------------------------------
# CRIAR CONTRATO
# ------------------------------------------------------------------

async def criar_contrato(
    db:      AsyncSession,
    dados:   ContratoCreate,
    usuario: str,
) -> Contrato:

    # Valida cliente
    from app.models.cliente import Cliente
    cliente = await db.get(Cliente, dados.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    if cliente.status.value not in ("PROSPECTO", "ATIVO"):
        raise HTTPException(status_code=400, detail="Não é possível criar contrato para cliente inativo ou bloqueado.")

    # Valida produtos e fase
    for item in dados.itens:
        produto = await db.get(ProdutoServico, item.produto_id)
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item.produto_id} não encontrado.")
        if produto.modalidade != dados.modalidade:
            raise HTTPException(status_code=400, detail=f"Produto '{produto.nome}' não pertence à modalidade {dados.modalidade}.")
        if item.fase == FaseContrato.IMPLANTACAO and not produto.permite_impl:
            raise HTTPException(status_code=400, detail=f"Produto '{produto.nome}' não permite cobrança em implantação.")
        if item.fase == FaseContrato.RECORRENCIA and not produto.permite_recorr:
            raise HTTPException(status_code=400, detail=f"Produto '{produto.nome}' não permite cobrança recorrente.")

    contrato = Contrato(
        **dados.model_dump(exclude={"itens", "parcelas_impl"}),
        criado_por     = usuario,
        atualizado_por = usuario,
    )
    db.add(contrato)
    await db.flush()

    # Itens
    for item in dados.itens:
        db.add(ContratoItem(contrato_id=contrato.id, **item.model_dump()))

    # Parcelas de implantação
    for parcela in dados.parcelas_impl:
        db.add(ContratoParcela(contrato_id=contrato.id, **parcela.model_dump()))

    # Atualiza status do cliente para ATIVO se ainda for PROSPECTO
    if cliente.status.value == "PROSPECTO":
        from app.models.cliente import StatusCliente
        cliente.status = StatusCliente.ATIVO
        cliente.atualizado_por = usuario

    db.add(ContratoHistorico(
        contrato_id  = contrato.id,
        operacao     = "I",
        campo_alterado = "cadastro",
        valor_novo   = "criado",
        alterado_por = usuario,
    ))

    await db.flush()
    await db.refresh(contrato)
    return contrato


# ------------------------------------------------------------------
# LISTAR CONTRATOS
# ------------------------------------------------------------------

async def listar_contratos(
    db:          AsyncSession,
    pagina:      int = 1,
    por_pagina:  int = 20,
    cliente_id:  Optional[UUID]               = None,
    modalidade:  Optional[ModalidadeContrato] = None,
    status:      Optional[StatusContrato]     = None,
    fase:        Optional[FaseContrato]       = None,
) -> ContratoListOut:

    query = text("""
        SELECT id, numero, cliente_id, cliente_nome, modalidade, status, fase_atual,
               dia_faturamento, data_assinatura, data_goLive, data_fim_contrato,
               prazo_meses, valor_total_impl, valor_mensal, responsavel_comercial,
               qtd_parcelas_impl, qtd_parcelas_pagas, dias_ate_fim, criado_em
        FROM vw_contratos_resumo
        WHERE (:cliente_id IS NULL OR cliente_id = :cliente_id::uuid)
          AND (:modalidade IS NULL OR modalidade = :modalidade)
          AND (:status IS NULL OR status = :status)
          AND (:fase IS NULL OR fase_atual = :fase)
        ORDER BY criado_em DESC
        LIMIT :limit OFFSET :offset
    """)

    count_query = text("""
        SELECT COUNT(*) FROM vw_contratos_resumo
        WHERE (:cliente_id IS NULL OR cliente_id = :cliente_id::uuid)
          AND (:modalidade IS NULL OR modalidade = :modalidade)
          AND (:status IS NULL OR status = :status)
          AND (:fase IS NULL OR fase_atual = :fase)
    """)

    params = {
        "cliente_id": str(cliente_id) if cliente_id else None,
        "modalidade": modalidade.value if modalidade else None,
        "status":     status.value if status else None,
        "fase":       fase.value if fase else None,
        "limit":      por_pagina,
        "offset":     (pagina - 1) * por_pagina,
    }

    total = (await db.execute(count_query, params)).scalar()
    rows  = await db.execute(query, params)
    dados = [ContratoResumoOut.model_validate(dict(r._mapping)) for r in rows]

    return ContratoListOut(
        dados=dados,
        meta=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=ceil(total / por_pagina) if total else 0,
        )
    )


# ------------------------------------------------------------------
# BUSCAR CONTRATO
# ------------------------------------------------------------------

async def buscar_contrato(db: AsyncSession, contrato_id: UUID) -> Contrato:
    return await _busca_contrato_ou_404(db, contrato_id)


# ------------------------------------------------------------------
# ATUALIZAR CONTRATO
# ------------------------------------------------------------------

async def atualizar_contrato(
    db:          AsyncSession,
    contrato_id: UUID,
    dados:       ContratoUpdate,
    usuario:     str,
) -> Contrato:
    contrato = await _busca_contrato_ou_404(db, contrato_id)

    if contrato.status in (StatusContrato.ENCERRADO, StatusContrato.CANCELADO):
        raise HTTPException(status_code=400, detail="Não é possível alterar contrato encerrado ou cancelado.")

    for campo, novo in dados.model_dump(exclude_unset=True).items():
        anterior = getattr(contrato, campo)
        if anterior != novo:
            _registra_historico(db, contrato.id, campo, anterior, novo, usuario)
            setattr(contrato, campo, novo)

    contrato.atualizado_por = usuario
    await db.flush()
    await db.refresh(contrato)
    return contrato


# ------------------------------------------------------------------
# REGISTRAR GO-LIVE
# ------------------------------------------------------------------

async def registrar_goLive(
    db:          AsyncSession,
    contrato_id: UUID,
    dados:       ContratoGoLive,
    usuario:     str,
) -> Contrato:
    contrato = await _busca_contrato_ou_404(db, contrato_id)

    if contrato.data_goLive:
        raise HTTPException(status_code=400, detail="Go-live já registrado para este contrato.")
    if dados.data_goLive < contrato.data_inicio_impl:
        raise HTTPException(status_code=400, detail="Data de go-live não pode ser anterior ao início da implantação.")
    if contrato.status != StatusContrato.ATIVO:
        raise HTTPException(status_code=400, detail="Contrato precisa estar ativo para registrar go-live.")

    _registra_historico(db, contrato.id, "data_goLive", None, str(dados.data_goLive), usuario)
    _registra_historico(db, contrato.id, "fase_atual", "IMPLANTACAO", "RECORRENCIA", usuario)

    contrato.data_goLive = dados.data_goLive
    # As demais datas (data_inicio_recorrencia, data_fim_contrato, fase_atual)
    # são calculadas pelo trigger fn_processa_goLive no banco.
    contrato.atualizado_por = usuario

    await db.flush()
    await db.refresh(contrato)
    return contrato


# ------------------------------------------------------------------
# ITENS
# ------------------------------------------------------------------

async def adicionar_item(
    db:          AsyncSession,
    contrato_id: UUID,
    dados:       ItemCreate,
    usuario:     str,
) -> ContratoItem:
    contrato = await _busca_contrato_ou_404(db, contrato_id)

    if contrato.status in (StatusContrato.ENCERRADO, StatusContrato.CANCELADO):
        raise HTTPException(status_code=400, detail="Não é possível adicionar itens a contrato encerrado ou cancelado.")

    produto = await db.get(ProdutoServico, dados.produto_id)
    if not produto or produto.modalidade != contrato.modalidade:
        raise HTTPException(status_code=400, detail="Produto inválido para a modalidade do contrato.")

    item = ContratoItem(contrato_id=contrato_id, **dados.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def remover_item(
    db:          AsyncSession,
    contrato_id: UUID,
    item_id:     UUID,
    usuario:     str,
) -> None:
    result = await db.execute(
        select(ContratoItem).where(
            ContratoItem.id == item_id,
            ContratoItem.contrato_id == contrato_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    item.ativo = False
    await db.flush()


# ------------------------------------------------------------------
# PARCELAS DE IMPLANTAÇÃO
# ------------------------------------------------------------------

async def adicionar_parcela(
    db:          AsyncSession,
    contrato_id: UUID,
    dados:       ParcelaCreate,
    usuario:     str,
) -> ContratoParcela:
    contrato = await _busca_contrato_ou_404(db, contrato_id)

    if contrato.fase_atual == FaseContrato.RECORRENCIA:
        raise HTTPException(status_code=400, detail="Contrato já está na fase de recorrência.")

    # Verifica número de parcela duplicado
    existente = await db.execute(
        select(ContratoParcela).where(
            ContratoParcela.contrato_id == contrato_id,
            ContratoParcela.numero_parcela == dados.numero_parcela,
        )
    )
    if existente.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Parcela {dados.numero_parcela} já existe.")

    parcela = ContratoParcela(contrato_id=contrato_id, **dados.model_dump())
    db.add(parcela)
    await db.flush()
    await db.refresh(parcela)
    return parcela


async def atualizar_parcela(
    db:          AsyncSession,
    contrato_id: UUID,
    parcela_id:  UUID,
    dados:       ParcelaUpdate,
    usuario:     str,
) -> ContratoParcela:
    result = await db.execute(
        select(ContratoParcela).where(
            ContratoParcela.id == parcela_id,
            ContratoParcela.contrato_id == contrato_id,
        )
    )
    parcela = result.scalar_one_or_none()
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(parcela, campo, valor)

    await db.flush()
    await db.refresh(parcela)
    return parcela


# ------------------------------------------------------------------
# CONTRATOS A FATURAR (para o módulo de faturamento)
# ------------------------------------------------------------------

async def contratos_a_faturar(
    db:             AsyncSession,
    dia_faturamento: str,
) -> list[dict]:
    rows = await db.execute(
        text("""
            SELECT contrato_id, numero, cliente_id, cliente_nome,
                   modalidade, dia_faturamento, valor_mensal, data_fim_contrato
            FROM vw_contratos_a_faturar
            WHERE dia_faturamento = :dia
            ORDER BY cliente_nome
        """),
        {"dia": dia_faturamento}
    )
    return [dict(r._mapping) for r in rows]
