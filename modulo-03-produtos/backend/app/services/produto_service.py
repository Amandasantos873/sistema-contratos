"""
Service do módulo de produtos e serviços.
Gerencia catálogo, pacotes mínimos e movimentações de itens em contratos.
"""
from math import ceil
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.contrato import ProdutoServico, ContratoItem, Contrato, FaseContrato
from app.models.produto import (
    StatusProduto, TipoMovimentacao,
    ProdutoPacote, ProdutoPacoteItem, ContratoItemMovimentacao
)
from app.schemas.produto import (
    ProdutoCreate, ProdutoUpdate, ProdutoDescontinuar,
    PacoteCreate, PacoteUpdate, PacoteItemCreate,
    MovimentacaoCreate,
    ProdutoCatalogoOut, ProdutoUsoOut, ProdutoListOut, PaginacaoMeta,
)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

async def _get_produto_ou_404(db: AsyncSession, produto_id: int) -> ProdutoServico:
    p = await db.get(ProdutoServico, produto_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return p


# ==================================================================
# CATÁLOGO — CRUD
# ==================================================================

async def listar_produtos(
    db:         AsyncSession,
    pagina:     int = 1,
    por_pagina: int = 30,
    modalidade: Optional[str] = None,
    status:     Optional[str] = None,
    busca:      Optional[str] = None,
) -> ProdutoListOut:

    query = text("""
        SELECT id, modalidade, codigo, nome, descricao, unidade,
               permite_impl, permite_recorr, status, data_descontinuacao,
               versao, criado_em, atualizado_em,
               contratos_ativos, valor_medio_praticado,
               substituto_nome, substituto_id
        FROM vw_produtos_catalogo
        WHERE (:modalidade IS NULL OR modalidade = :modalidade)
          AND (:status     IS NULL OR status     = :status)
          AND (:busca      IS NULL OR (
              unaccent(lower(nome))   ILIKE unaccent(lower('%' || :busca || '%'))
              OR lower(codigo)        ILIKE lower('%' || :busca || '%')
          ))
        ORDER BY modalidade, nome
        LIMIT :limit OFFSET :offset
    """)

    count_q = text("""
        SELECT COUNT(*) FROM vw_produtos_catalogo
        WHERE (:modalidade IS NULL OR modalidade = :modalidade)
          AND (:status     IS NULL OR status     = :status)
          AND (:busca      IS NULL OR (
              unaccent(lower(nome))   ILIKE unaccent(lower('%' || :busca || '%'))
              OR lower(codigo)        ILIKE lower('%' || :busca || '%')
          ))
    """)

    params = {
        "modalidade": modalidade,
        "status":     status,
        "busca":      busca,
        "limit":      por_pagina,
        "offset":     (pagina - 1) * por_pagina,
    }

    total = (await db.execute(count_q, params)).scalar()
    rows  = await db.execute(query, params)
    dados = [ProdutoCatalogoOut.model_validate(dict(r._mapping)) for r in rows]

    return ProdutoListOut(
        dados=dados,
        meta=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=ceil(total / por_pagina) if total else 0,
        )
    )


async def buscar_produto(db: AsyncSession, produto_id: int) -> ProdutoCatalogoOut:
    row = await db.execute(
        text("""
            SELECT id, modalidade, codigo, nome, descricao, unidade,
                   permite_impl, permite_recorr, status, data_descontinuacao,
                   versao, criado_em, atualizado_em,
                   contratos_ativos, valor_medio_praticado,
                   substituto_nome, substituto_id
            FROM vw_produtos_catalogo
            WHERE id = :id
        """),
        {"id": produto_id}
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return ProdutoCatalogoOut.model_validate(dict(r._mapping))


async def criar_produto(
    db:      AsyncSession,
    dados:   ProdutoCreate,
    usuario: str,
) -> ProdutoServico:
    # Verifica código duplicado na mesma modalidade
    existe = await db.execute(
        select(ProdutoServico).where(
            ProdutoServico.modalidade == dados.modalidade,
            ProdutoServico.codigo     == dados.codigo,
        )
    )
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Código '{dados.codigo}' já existe para a modalidade {dados.modalidade}.")

    produto = ProdutoServico(
        **dados.model_dump(),
        status      = StatusProduto.ATIVO,
        criado_por  = usuario,
        atualizado_por = usuario,
    )
    db.add(produto)
    await db.flush()
    await db.refresh(produto)
    return produto


async def atualizar_produto(
    db:         AsyncSession,
    produto_id: int,
    dados:      ProdutoUpdate,
    usuario:    str,
) -> ProdutoServico:
    produto = await _get_produto_ou_404(db, produto_id)

    if produto.status == StatusProduto.DESCONTINUADO:
        raise HTTPException(status_code=400, detail="Produto descontinuado não pode ser editado.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)

    produto.atualizado_por = usuario
    await db.flush()
    await db.refresh(produto)
    return produto


async def descontinuar_produto(
    db:         AsyncSession,
    produto_id: int,
    dados:      ProdutoDescontinuar,
    usuario:    str,
) -> ProdutoServico:
    produto = await _get_produto_ou_404(db, produto_id)

    if produto.status == StatusProduto.DESCONTINUADO:
        raise HTTPException(status_code=400, detail="Produto já está descontinuado.")

    # Verifica contratos ativos (o banco também valida via trigger)
    count = await db.execute(
        text("""
            SELECT COUNT(DISTINCT ci.contrato_id)
            FROM contratos_itens ci
            JOIN contratos c ON c.id = ci.contrato_id
            WHERE ci.produto_id = :pid
              AND ci.ativo = TRUE
              AND c.status IN ('ATIVO','SUSPENSO')
        """),
        {"pid": produto_id}
    )
    qtd_contratos = count.scalar()
    if qtd_contratos > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Produto está em uso em {qtd_contratos} contrato(s) ativo(s). "
                   f"Encerre ou substitua o item nos contratos antes de descontinuar."
        )

    produto.status               = StatusProduto.DESCONTINUADO
    produto.motivo_descontinuacao = dados.motivo
    produto.substituido_por      = dados.substituido_por
    produto.atualizado_por       = usuario
    await db.flush()
    await db.refresh(produto)
    return produto


async def reativar_produto(
    db:         AsyncSession,
    produto_id: int,
    usuario:    str,
) -> ProdutoServico:
    produto = await _get_produto_ou_404(db, produto_id)

    if produto.status == StatusProduto.ATIVO:
        raise HTTPException(status_code=400, detail="Produto já está ativo.")

    produto.status                = StatusProduto.ATIVO
    produto.data_descontinuacao   = None
    produto.motivo_descontinuacao = None
    produto.atualizado_por        = usuario
    await db.flush()
    await db.refresh(produto)
    return produto


async def uso_do_produto(
    db:         AsyncSession,
    produto_id: int,
    apenas_ativos: bool = True,
) -> list[ProdutoUsoOut]:
    filtro_status = "AND c.status IN ('ATIVO','SUSPENSO') AND ci.ativo = TRUE" if apenas_ativos else ""
    rows = await db.execute(
        text(f"""
            SELECT contrato_id, contrato_numero, cliente_nome, modalidade,
                   contrato_status, fase_atual, quantidade, valor_unitario,
                   desconto_pct, valor_total, item_fase, item_ativo
            FROM vw_produto_contratos_uso
            WHERE produto_id = :pid
            {filtro_status}
            ORDER BY cliente_nome
        """),
        {"pid": produto_id}
    )
    return [ProdutoUsoOut.model_validate(dict(r._mapping)) for r in rows]


# ==================================================================
# PACOTES MÍNIMOS
# ==================================================================

async def listar_pacotes(
    db:         AsyncSession,
    modalidade: Optional[str] = None,
) -> list[ProdutoPacote]:
    q = select(ProdutoPacote).options(
        selectinload(ProdutoPacote.itens).selectinload(ProdutoPacoteItem.produto)
    )
    if modalidade:
        q = q.where(ProdutoPacote.modalidade == modalidade)
    result = await db.execute(q.order_by(ProdutoPacote.modalidade, ProdutoPacote.nome))
    return result.scalars().all()


async def criar_pacote(
    db:      AsyncSession,
    dados:   PacoteCreate,
    usuario: str,
) -> ProdutoPacote:
    pacote = ProdutoPacote(
        modalidade  = dados.modalidade,
        nome        = dados.nome,
        descricao   = dados.descricao,
        criado_por  = usuario,
    )
    db.add(pacote)
    await db.flush()

    for item in dados.itens:
        # Valida que produto pertence à modalidade
        produto = await db.get(ProdutoServico, item.produto_id)
        if not produto or produto.modalidade != dados.modalidade:
            raise HTTPException(status_code=400, detail=f"Produto {item.produto_id} inválido para modalidade {dados.modalidade}.")
        db.add(ProdutoPacoteItem(pacote_id=pacote.id, **item.model_dump()))

    await db.flush()
    await db.refresh(pacote)
    return pacote


async def atualizar_pacote(
    db:        AsyncSession,
    pacote_id: int,
    dados:     PacoteUpdate,
    usuario:   str,
) -> ProdutoPacote:
    pacote = await db.get(ProdutoPacote, pacote_id)
    if not pacote:
        raise HTTPException(status_code=404, detail="Pacote não encontrado.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(pacote, campo, valor)
    await db.flush()
    await db.refresh(pacote)
    return pacote


# ==================================================================
# MOVIMENTAÇÃO DE ITEM EM CONTRATO
# ==================================================================

async def registrar_movimentacao(
    db:          AsyncSession,
    contrato_id: UUID,
    dados:       MovimentacaoCreate,
    usuario:     str,
) -> ContratoItemMovimentacao:

    # Valida item pertence ao contrato
    result = await db.execute(
        select(ContratoItem).where(
            ContratoItem.id         == dados.contrato_item_id,
            ContratoItem.contrato_id == contrato_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado no contrato.")

    # Valida contrato ativo
    contrato = await db.get(Contrato, contrato_id)
    if contrato.status not in ("ATIVO", "SUSPENSO"):
        raise HTTPException(status_code=400, detail="Contrato precisa estar ativo ou suspenso para registrar movimentação.")

    valor_anterior = item.valor_unitario
    novo_item_id   = None

    if dados.tipo == TipoMovimentacao.CANCELAMENTO:
        item.ativo = False

    elif dados.tipo == TipoMovimentacao.SUSPENSAO:
        item.ativo = False

    elif dados.tipo == TipoMovimentacao.REATIVACAO:
        item.ativo = True

    elif dados.tipo == TipoMovimentacao.SUBSTITUICAO:
        if not dados.novo_produto_id:
            raise HTTPException(status_code=400, detail="Substituição exige novo_produto_id.")
        # Desativa item antigo
        item.ativo = False
        # Cria novo item
        novo_produto = await db.get(ProdutoServico, dados.novo_produto_id)
        if not novo_produto or novo_produto.modalidade != contrato.modalidade:
            raise HTTPException(status_code=400, detail="Produto substituto inválido para a modalidade do contrato.")

        novo_item = ContratoItem(
            contrato_id    = contrato_id,
            produto_id     = dados.novo_produto_id,
            quantidade     = dados.nova_quantidade or item.quantidade,
            valor_unitario = dados.novo_valor or item.valor_unitario,
            desconto_pct   = item.desconto_pct,
            fase           = item.fase,
        )
        db.add(novo_item)
        await db.flush()
        novo_item_id = novo_item.id

    mov = ContratoItemMovimentacao(
        contrato_id      = contrato_id,
        contrato_item_id = dados.contrato_item_id,
        tipo             = dados.tipo,
        data_efetivacao  = dados.data_efetivacao,
        motivo           = dados.motivo,
        novo_item_id     = novo_item_id,
        valor_anterior   = valor_anterior,
        valor_novo       = dados.novo_valor,
        criado_por       = usuario,
    )
    db.add(mov)
    await db.flush()
    await db.refresh(mov)
    return mov


async def listar_movimentacoes_contrato(
    db:          AsyncSession,
    contrato_id: UUID,
) -> list[ContratoItemMovimentacao]:
    result = await db.execute(
        select(ContratoItemMovimentacao)
        .where(ContratoItemMovimentacao.contrato_id == contrato_id)
        .order_by(ContratoItemMovimentacao.criado_em.desc())
    )
    return result.scalars().all()
