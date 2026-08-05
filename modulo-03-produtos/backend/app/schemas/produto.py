from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.contrato import ModalidadeContrato, FaseContrato
from app.models.produto import StatusProduto, TipoMovimentacao


# ==================================================================
# PRODUTO/SERVIÇO — CRUD completo
# ==================================================================

class ProdutoCreate(BaseModel):
    modalidade:     ModalidadeContrato
    codigo:         str           = Field(..., max_length=30)
    nome:           str           = Field(..., max_length=200)
    descricao:      Optional[str] = None
    unidade:        str           = Field(default="MÊS", max_length=30)
    permite_impl:   bool          = False
    permite_recorr: bool          = True

class ProdutoUpdate(BaseModel):
    nome:           Optional[str]  = None
    descricao:      Optional[str]  = None
    unidade:        Optional[str]  = None
    permite_impl:   Optional[bool] = None
    permite_recorr: Optional[bool] = None

class ProdutoDescontinuar(BaseModel):
    motivo:          str           = Field(..., min_length=10)
    substituido_por: Optional[int] = None   # id do produto substituto

class ProdutoCatalogoOut(BaseModel):
    """Schema enriquecido para listagem — vem da view vw_produtos_catalogo."""
    id:                    int
    modalidade:            ModalidadeContrato
    codigo:                str
    nome:                  str
    descricao:             Optional[str]
    unidade:               str
    permite_impl:          bool
    permite_recorr:        bool
    status:                StatusProduto
    data_descontinuacao:   Optional[date]
    versao:                int
    criado_em:             datetime
    atualizado_em:         datetime
    contratos_ativos:      int
    valor_medio_praticado: Optional[Decimal]
    substituto_nome:       Optional[str]
    substituto_id:         Optional[int]

    model_config = {"from_attributes": True}

class ProdutoUsoOut(BaseModel):
    """Um contrato que usa este produto — vem da view vw_produto_contratos_uso."""
    contrato_id:      UUID
    contrato_numero:  str
    cliente_nome:     str
    modalidade:       ModalidadeContrato
    contrato_status:  str
    fase_atual:       str
    quantidade:       Decimal
    valor_unitario:   Decimal
    desconto_pct:     Decimal
    valor_total:      Decimal
    item_fase:        FaseContrato
    item_ativo:       bool

    model_config = {"from_attributes": True}


# ==================================================================
# PACOTES MÍNIMOS
# ==================================================================

class PacoteItemCreate(BaseModel):
    produto_id:     int
    quantidade_min: Decimal = Field(default=Decimal("1"), gt=0)
    obrigatorio:    bool    = True
    observacoes:    Optional[str] = None

class PacoteCreate(BaseModel):
    modalidade: ModalidadeContrato
    nome:       str           = Field(..., max_length=150)
    descricao:  Optional[str] = None
    itens:      list[PacoteItemCreate] = Field(default_factory=list)

class PacoteUpdate(BaseModel):
    nome:      Optional[str]  = None
    descricao: Optional[str]  = None
    ativo:     Optional[bool] = None

class PacoteItemOut(BaseModel):
    id:             int
    produto_id:     int
    produto_nome:   str
    produto_codigo: str
    unidade:        str
    quantidade_min: Decimal
    obrigatorio:    bool
    observacoes:    Optional[str]

    model_config = {"from_attributes": True}

class PacoteOut(BaseModel):
    id:         int
    modalidade: ModalidadeContrato
    nome:       str
    descricao:  Optional[str]
    ativo:      bool
    criado_em:  datetime
    itens:      list[PacoteItemOut] = []

    model_config = {"from_attributes": True}


# ==================================================================
# MOVIMENTAÇÃO DE ITEM EM CONTRATO
# ==================================================================

class MovimentacaoCreate(BaseModel):
    contrato_item_id: UUID
    tipo:             TipoMovimentacao
    data_efetivacao:  date
    motivo:           str  = Field(..., min_length=10)
    novo_produto_id:  Optional[int]   = None   # para SUBSTITUICAO
    nova_quantidade:  Optional[Decimal] = None
    novo_valor:       Optional[Decimal] = None

class MovimentacaoOut(BaseModel):
    id:               UUID
    contrato_id:      UUID
    contrato_item_id: UUID
    tipo:             TipoMovimentacao
    data_solicitacao: date
    data_efetivacao:  date
    motivo:           str
    valor_anterior:   Optional[Decimal]
    valor_novo:       Optional[Decimal]
    criado_por:       str
    criado_em:        datetime

    model_config = {"from_attributes": True}


# ==================================================================
# PAGINAÇÃO
# ==================================================================

class PaginacaoMeta(BaseModel):
    total:      int
    pagina:     int
    por_pagina: int
    paginas:    int

class ProdutoListOut(BaseModel):
    dados: list[ProdutoCatalogoOut]
    meta:  PaginacaoMeta
