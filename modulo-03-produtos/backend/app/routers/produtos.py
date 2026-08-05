from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.produto import (
    ProdutoCreate, ProdutoUpdate, ProdutoDescontinuar,
    ProdutoCatalogoOut, ProdutoUsoOut, ProdutoListOut,
    PacoteCreate, PacoteUpdate, PacoteOut,
    MovimentacaoCreate, MovimentacaoOut,
)
from app.services import produto_service as svc

router = APIRouter(tags=["Produtos e Serviços"])


def get_usuario_atual(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")


# ==================================================================
# CATÁLOGO
# ==================================================================

@router.get(
    "/produtos",
    response_model=ProdutoListOut,
    summary="Lista catálogo com filtros, busca e métricas de uso",
)
async def listar_produtos(
    pagina:     int            = Query(1, ge=1),
    por_pagina: int            = Query(30, ge=1, le=100),
    modalidade: Optional[str]  = Query(None),
    status:     Optional[str]  = Query(None, description="ATIVO | DESCONTINUADO | SUSPENSO"),
    busca:      Optional[str]  = Query(None),
    db:         AsyncSession   = Depends(get_db),
):
    return await svc.listar_produtos(db, pagina, por_pagina, modalidade, status, busca)


@router.get(
    "/produtos/{produto_id}",
    response_model=ProdutoCatalogoOut,
    summary="Detalhe do produto com métricas de uso",
)
async def buscar_produto(produto_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.buscar_produto(db, produto_id)


@router.post(
    "/produtos",
    response_model=ProdutoCatalogoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria produto/serviço no catálogo",
)
async def criar_produto(
    dados:   ProdutoCreate,
    db:      AsyncSession = Depends(get_db),
    usuario: str          = Depends(get_usuario_atual),
):
    produto = await svc.criar_produto(db, dados, usuario)
    return await svc.buscar_produto(db, produto.id)


@router.patch(
    "/produtos/{produto_id}",
    response_model=ProdutoCatalogoOut,
    summary="Atualiza dados do produto",
)
async def atualizar_produto(
    produto_id: int,
    dados:      ProdutoUpdate,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    await svc.atualizar_produto(db, produto_id, dados, usuario)
    return await svc.buscar_produto(db, produto_id)


@router.patch(
    "/produtos/{produto_id}/descontinuar",
    response_model=ProdutoCatalogoOut,
    summary="Descontinua produto (bloqueia se houver contratos ativos)",
)
async def descontinuar_produto(
    produto_id: int,
    dados:      ProdutoDescontinuar,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    await svc.descontinuar_produto(db, produto_id, dados, usuario)
    return await svc.buscar_produto(db, produto_id)


@router.patch(
    "/produtos/{produto_id}/reativar",
    response_model=ProdutoCatalogoOut,
    summary="Reativa produto descontinuado ou suspenso",
)
async def reativar_produto(
    produto_id: int,
    db:         AsyncSession = Depends(get_db),
    usuario:    str          = Depends(get_usuario_atual),
):
    await svc.reativar_produto(db, produto_id, usuario)
    return await svc.buscar_produto(db, produto_id)


@router.get(
    "/produtos/{produto_id}/uso",
    response_model=list[ProdutoUsoOut],
    summary="Contratos que utilizam este produto",
)
async def uso_do_produto(
    produto_id:    int,
    apenas_ativos: bool         = Query(True),
    db:            AsyncSession = Depends(get_db),
):
    return await svc.uso_do_produto(db, produto_id, apenas_ativos)


# ==================================================================
# PACOTES MÍNIMOS
# ==================================================================

@router.get(
    "/pacotes",
    response_model=list[PacoteOut],
    summary="Lista pacotes mínimos por modalidade",
)
async def listar_pacotes(
    modalidade: Optional[str] = Query(None),
    db:         AsyncSession  = Depends(get_db),
):
    return await svc.listar_pacotes(db, modalidade)


@router.post(
    "/pacotes",
    response_model=PacoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria pacote mínimo",
)
async def criar_pacote(
    dados:   PacoteCreate,
    db:      AsyncSession = Depends(get_db),
    usuario: str          = Depends(get_usuario_atual),
):
    return await svc.criar_pacote(db, dados, usuario)


@router.patch(
    "/pacotes/{pacote_id}",
    response_model=PacoteOut,
    summary="Atualiza pacote mínimo",
)
async def atualizar_pacote(
    pacote_id: int,
    dados:     PacoteUpdate,
    db:        AsyncSession = Depends(get_db),
    usuario:   str          = Depends(get_usuario_atual),
):
    return await svc.atualizar_pacote(db, pacote_id, dados, usuario)


# ==================================================================
# MOVIMENTAÇÕES EM CONTRATOS
# ==================================================================

@router.post(
    "/contratos/{contrato_id}/movimentacoes",
    response_model=MovimentacaoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registra cancelamento, suspensão, reativação ou substituição de item",
)
async def registrar_movimentacao(
    contrato_id: UUID,
    dados:       MovimentacaoCreate,
    db:          AsyncSession = Depends(get_db),
    usuario:     str          = Depends(get_usuario_atual),
):
    return await svc.registrar_movimentacao(db, contrato_id, dados, usuario)


@router.get(
    "/contratos/{contrato_id}/movimentacoes",
    response_model=list[MovimentacaoOut],
    summary="Histórico de movimentações de itens do contrato",
)
async def listar_movimentacoes(
    contrato_id: UUID,
    db:          AsyncSession = Depends(get_db),
):
    return await svc.listar_movimentacoes_contrato(db, contrato_id)
