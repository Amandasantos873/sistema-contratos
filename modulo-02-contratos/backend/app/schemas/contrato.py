from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from app.models.contrato import (
    ModalidadeContrato, StatusContrato, FaseContrato,
    DiaFaturamento, StatusParcelaImpl
)


# ==================================================================
# PRODUTO/SERVIÇO
# ==================================================================

class ProdutoServicoOut(BaseModel):
    id:             int
    modalidade:     ModalidadeContrato
    codigo:         str
    nome:           str
    unidade:        str
    preco_tabela:   Optional[Decimal]
    permite_impl:   bool
    permite_recorr: bool

    model_config = {"from_attributes": True}


# ==================================================================
# PARCELA DE IMPLANTAÇÃO
# ==================================================================

class ParcelaCreate(BaseModel):
    numero_parcela:  int   = Field(..., ge=1)
    valor:           Decimal = Field(..., gt=0)
    data_vencimento: date
    observacoes:     Optional[str] = None

class ParcelaUpdate(BaseModel):
    valor:            Optional[Decimal] = None
    data_vencimento:  Optional[date]    = None
    status:           Optional[StatusParcelaImpl] = None
    data_faturamento: Optional[date]    = None
    data_pagamento:   Optional[date]    = None
    observacoes:      Optional[str]     = None

class ParcelaOut(BaseModel):
    id:               UUID
    contrato_id:      UUID
    numero_parcela:   int
    valor:            Decimal
    data_vencimento:  date
    status:           StatusParcelaImpl
    data_faturamento: Optional[date]
    data_pagamento:   Optional[date]
    observacoes:      Optional[str]

    model_config = {"from_attributes": True}


# ==================================================================
# ITEM DO CONTRATO
# ==================================================================

class ItemCreate(BaseModel):
    produto_id:     int
    quantidade:     Decimal = Field(default=Decimal("1"), gt=0)
    valor_unitario: Decimal = Field(..., gt=0)
    desconto_pct:   Decimal = Field(default=Decimal("0"), ge=0, le=100)
    fase:           FaseContrato
    observacoes:    Optional[str] = None

class ItemUpdate(BaseModel):
    quantidade:     Optional[Decimal] = None
    valor_unitario: Optional[Decimal] = None
    desconto_pct:   Optional[Decimal] = None
    ativo:          Optional[bool]    = None
    observacoes:    Optional[str]     = None

class ItemOut(BaseModel):
    id:             UUID
    contrato_id:    UUID
    produto_id:     int
    produto:        ProdutoServicoOut
    quantidade:     Decimal
    valor_unitario: Decimal
    desconto_pct:   Decimal
    valor_total:    Decimal
    fase:           FaseContrato
    ativo:          bool
    observacoes:    Optional[str]

    model_config = {"from_attributes": True}


# ==================================================================
# CONTRATO
# ==================================================================

class ContratoCreate(BaseModel):
    cliente_id:             UUID
    modalidade:             ModalidadeContrato
    data_assinatura:        date
    data_inicio_impl:       date
    prazo_meses:            int   = Field(..., gt=0)
    dia_faturamento:        DiaFaturamento
    responsavel_comercial:  Optional[str] = None
    responsavel_implantacao:Optional[str] = None
    numero_proposta:        Optional[str] = None
    observacoes:            Optional[str] = None
    itens:                  list[ItemCreate]   = Field(default_factory=list)
    parcelas_impl:          list[ParcelaCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def valida_itens(self):
        if not self.itens:
            raise ValueError("O contrato deve ter ao menos um item.")
        return self

    @model_validator(mode="after")
    def valida_datas(self):
        if self.data_inicio_impl < self.data_assinatura:
            raise ValueError("Data de início da implantação não pode ser anterior à assinatura.")
        return self


class ContratoUpdate(BaseModel):
    responsavel_comercial:   Optional[str] = None
    responsavel_implantacao: Optional[str] = None
    numero_proposta:         Optional[str] = None
    observacoes:             Optional[str] = None
    dia_faturamento:         Optional[DiaFaturamento] = None
    prazo_meses:             Optional[int] = Field(None, gt=0)
    status:                  Optional[StatusContrato] = None


class ContratoGoLive(BaseModel):
    data_goLive: date
    observacoes: Optional[str] = None


class ContratoOut(BaseModel):
    id:                      UUID
    numero:                  str
    cliente_id:              UUID
    modalidade:              ModalidadeContrato
    status:                  StatusContrato
    fase_atual:              FaseContrato
    dia_faturamento:         DiaFaturamento
    data_assinatura:         date
    data_inicio_impl:        date
    data_goLive:             Optional[date]
    data_inicio_recorrencia: Optional[date]
    data_fim_contrato:       Optional[date]
    prazo_meses:             int
    valor_total_impl:        Decimal
    valor_mensal:            Decimal
    responsavel_comercial:   Optional[str]
    responsavel_implantacao: Optional[str]
    numero_proposta:         Optional[str]
    observacoes:             Optional[str]
    criado_em:               datetime
    atualizado_em:           datetime
    itens:                   list[ItemOut]    = []
    parcelas_impl:           list[ParcelaOut] = []

    model_config = {"from_attributes": True}


class ContratoResumoOut(BaseModel):
    id:                  UUID
    numero:              str
    cliente_id:          UUID
    cliente_nome:        str
    modalidade:          ModalidadeContrato
    status:              StatusContrato
    fase_atual:          FaseContrato
    dia_faturamento:     DiaFaturamento
    data_assinatura:     date
    data_goLive:         Optional[date]
    data_fim_contrato:   Optional[date]
    prazo_meses:         int
    valor_total_impl:    Decimal
    valor_mensal:        Decimal
    qtd_parcelas_impl:   int
    qtd_parcelas_pagas:  int
    dias_ate_fim:        Optional[int]
    responsavel_comercial: Optional[str]
    criado_em:           datetime

    model_config = {"from_attributes": True}


# ==================================================================
# PAGINAÇÃO
# ==================================================================

class PaginacaoMeta(BaseModel):
    total:      int
    pagina:     int
    por_pagina: int
    paginas:    int

class ContratoListOut(BaseModel):
    dados: list[ContratoResumoOut]
    meta:  PaginacaoMeta
