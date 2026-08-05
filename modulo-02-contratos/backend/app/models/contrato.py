import uuid
import enum
from datetime import date
from decimal import Decimal
from sqlalchemy import (
    Column, String, Boolean, Text, Date, Integer, Numeric,
    ForeignKey, Enum as SAEnum, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------

class ModalidadeContrato(str, enum.Enum):
    ASP = "ASP"
    BSP = "BSP"
    BPO = "BPO"

class StatusContrato(str, enum.Enum):
    PROPOSTA   = "PROPOSTA"
    ATIVO      = "ATIVO"
    SUSPENSO   = "SUSPENSO"
    ENCERRADO  = "ENCERRADO"
    CANCELADO  = "CANCELADO"

class FaseContrato(str, enum.Enum):
    IMPLANTACAO = "IMPLANTACAO"
    RECORRENCIA = "RECORRENCIA"

class DiaFaturamento(str, enum.Enum):
    DIA_01 = "DIA_01"
    DIA_15 = "DIA_15"
    DIA_25 = "DIA_25"

class StatusParcelaImpl(str, enum.Enum):
    PENDENTE   = "PENDENTE"
    FATURADA   = "FATURADA"
    PAGA       = "PAGA"
    CANCELADA  = "CANCELADA"


# ------------------------------------------------------------------
# Produto/Serviço
# ------------------------------------------------------------------

class ProdutoServico(Base):
    __tablename__ = "produtos_servicos"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    modalidade      = Column(SAEnum(ModalidadeContrato, name="modalidade_contrato"), nullable=False)
    codigo          = Column(String(30), nullable=False)
    nome            = Column(String(200), nullable=False)
    descricao       = Column(Text)
    unidade         = Column(String(30), nullable=False, default="MÊS")
    preco_tabela    = Column(Numeric(15, 2))
    permite_impl    = Column(Boolean, nullable=False, default=False)
    permite_recorr  = Column(Boolean, nullable=False, default=True)
    ativo           = Column(Boolean, nullable=False, default=True)
    criado_em       = Column(DateTime(timezone=True), server_default=func.now())

    itens           = relationship("ContratoItem", back_populates="produto")


# ------------------------------------------------------------------
# Contrato
# ------------------------------------------------------------------

class Contrato(Base):
    __tablename__ = "contratos"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero                  = Column(String(30), unique=True)
    cliente_id              = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    modalidade              = Column(SAEnum(ModalidadeContrato, name="modalidade_contrato"), nullable=False)

    data_assinatura         = Column(Date, nullable=False)
    data_inicio_impl        = Column(Date, nullable=False)
    data_goLive             = Column(Date)
    data_inicio_recorrencia = Column(Date)
    prazo_meses             = Column(Integer, nullable=False)
    data_fim_contrato       = Column(Date)
    data_renovacao          = Column(Date)

    dia_faturamento         = Column(SAEnum(DiaFaturamento, name="dia_faturamento"), nullable=False)
    fase_atual              = Column(SAEnum(FaseContrato, name="fase_contrato"), nullable=False, default=FaseContrato.IMPLANTACAO)
    status                  = Column(SAEnum(StatusContrato, name="status_contrato"), nullable=False, default=StatusContrato.PROPOSTA)

    valor_total_impl        = Column(Numeric(15, 2), nullable=False, default=0)
    valor_mensal            = Column(Numeric(15, 2), nullable=False, default=0)

    responsavel_comercial   = Column(String(100))
    responsavel_implantacao = Column(String(100))
    numero_proposta         = Column(String(50))
    observacoes             = Column(Text)

    criado_em               = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por              = Column(String(100), nullable=False)
    atualizado_em           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_por          = Column(String(100), nullable=False)

    itens                   = relationship("ContratoItem", back_populates="contrato", cascade="all, delete-orphan")
    parcelas_impl           = relationship("ContratoParcela", back_populates="contrato", cascade="all, delete-orphan", order_by="ContratoParcela.numero_parcela")
    aditivos                = relationship("ContratoAditivo", back_populates="contrato", cascade="all, delete-orphan")
    historico               = relationship("ContratoHistorico", back_populates="contrato", cascade="all, delete-orphan")


# ------------------------------------------------------------------
# Item do contrato
# ------------------------------------------------------------------

class ContratoItem(Base):
    __tablename__ = "contratos_itens"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id     = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    produto_id      = Column(Integer, ForeignKey("produtos_servicos.id", ondelete="RESTRICT"), nullable=False)
    quantidade      = Column(Numeric(10, 3), nullable=False, default=1)
    valor_unitario  = Column(Numeric(15, 2), nullable=False)
    desconto_pct    = Column(Numeric(5, 2), nullable=False, default=0)
    fase            = Column(SAEnum(FaseContrato, name="fase_contrato"), nullable=False)
    ativo           = Column(Boolean, nullable=False, default=True)
    observacoes     = Column(Text)
    criado_em       = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em   = Column(DateTime(timezone=True), server_default=func.now())

    contrato        = relationship("Contrato", back_populates="itens")
    produto         = relationship("ProdutoServico", back_populates="itens")

    @property
    def valor_total(self) -> Decimal:
        return round(self.quantidade * self.valor_unitario * (1 - self.desconto_pct / 100), 2)


# ------------------------------------------------------------------
# Parcela de implantação
# ------------------------------------------------------------------

class ContratoParcela(Base):
    __tablename__ = "contratos_parcelas_implantacao"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id      = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    numero_parcela   = Column(Integer, nullable=False)
    valor            = Column(Numeric(15, 2), nullable=False)
    data_vencimento  = Column(Date, nullable=False)
    status           = Column(SAEnum(StatusParcelaImpl, name="status_parcela_impl"), nullable=False, default=StatusParcelaImpl.PENDENTE)
    data_faturamento = Column(Date)
    data_pagamento   = Column(Date)
    observacoes      = Column(Text)
    criado_em        = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em    = Column(DateTime(timezone=True), server_default=func.now())

    contrato         = relationship("Contrato", back_populates="parcelas_impl")


# ------------------------------------------------------------------
# Aditivo
# ------------------------------------------------------------------

class ContratoAditivo(Base):
    __tablename__ = "contratos_aditivos"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id     = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    numero_aditivo  = Column(Integer, nullable=False)
    tipo            = Column(String(50), nullable=False)
    descricao       = Column(Text, nullable=False)
    data_aditivo    = Column(Date, nullable=False)
    data_vigencia   = Column(Date, nullable=False)
    valor_anterior  = Column(Numeric(15, 2))
    valor_novo      = Column(Numeric(15, 2))
    criado_em       = Column(DateTime(timezone=True), server_default=func.now())
    criado_por      = Column(String(100), nullable=False)

    contrato        = relationship("Contrato", back_populates="aditivos")


# ------------------------------------------------------------------
# Histórico
# ------------------------------------------------------------------

class ContratoHistorico(Base):
    __tablename__ = "contratos_historico"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    contrato_id     = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    operacao        = Column(String(1), nullable=False)
    campo_alterado  = Column(String(100))
    valor_anterior  = Column(Text)
    valor_novo      = Column(Text)
    alterado_por    = Column(String(100), nullable=False)
    alterado_em     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    motivo          = Column(Text)

    contrato        = relationship("Contrato", back_populates="historico")
