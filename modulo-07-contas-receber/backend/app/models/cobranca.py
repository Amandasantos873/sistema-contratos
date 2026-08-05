"""
Módulo 07 — Contas a Receber
Models, Schemas e Service em um único arquivo para facilitar a entrega.
"""
# ================================================================
# MODELS
# ================================================================
import uuid, enum
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Any
from sqlalchemy import Column, String, Boolean, Text, Date, Integer, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from pydantic import BaseModel, Field


class FormaRecebimento(str, enum.Enum):
    BOLETO   = "BOLETO"
    PIX      = "PIX"
    TED      = "TED"
    DOC      = "DOC"
    DEPOSITO = "DEPOSITO"
    CARTAO   = "CARTAO"
    OUTROS   = "OUTROS"

class StatusCobranca(str, enum.Enum):
    ABERTA       = "ABERTA"
    RECEBIDA     = "RECEBIDA"
    PARCIAL      = "PARCIAL"
    VENCIDA      = "VENCIDA"
    NEGOCIADA    = "NEGOCIADA"
    CANCELADA    = "CANCELADA"
    INADIMPLENTE = "INADIMPLENTE"

class StatusNegociacao(str, enum.Enum):
    EM_NEGOCIACAO = "EM_NEGOCIACAO"
    APROVADA      = "APROVADA"
    REPROVADA     = "REPROVADA"
    EFETIVADA     = "EFETIVADA"


class Cobranca(Base):
    __tablename__ = "cobrancas"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fatura_id        = Column(UUID(as_uuid=True), ForeignKey("faturas.id",   ondelete="RESTRICT"), nullable=False)
    contrato_id      = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="RESTRICT"), nullable=False)
    cliente_id       = Column(UUID(as_uuid=True), ForeignKey("clientes.id",  ondelete="RESTRICT"), nullable=False)
    numero_cobranca  = Column(String(30), unique=True)
    competencia      = Column(Date, nullable=False)
    data_emissao     = Column(Date, nullable=False)
    data_vencimento  = Column(Date, nullable=False)
    valor_original   = Column(Numeric(15,2), nullable=False)
    valor_juros      = Column(Numeric(15,2), nullable=False, default=0)
    valor_multa      = Column(Numeric(15,2), nullable=False, default=0)
    valor_desconto   = Column(Numeric(15,2), nullable=False, default=0)
    valor_recebido   = Column(Numeric(15,2), nullable=False, default=0)
    status           = Column(SAEnum(StatusCobranca,  name="status_cobranca"),  nullable=False, default=StatusCobranca.ABERTA)
    numero_erp       = Column(String(50))
    numero_nf        = Column(String(30))
    observacoes      = Column(Text)
    criado_em        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por       = Column(String(100), nullable=False)
    atualizado_em    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_por   = Column(String(100), nullable=False)
    recebimentos     = relationship("Recebimento",  back_populates="cobranca", cascade="all, delete-orphan")
    negociacoes      = relationship("Negociacao",   back_populates="cobranca", cascade="all, delete-orphan")


class Recebimento(Base):
    __tablename__ = "recebimentos"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cobranca_id      = Column(UUID(as_uuid=True), ForeignKey("cobrancas.id", ondelete="CASCADE"), nullable=False)
    data_recebimento = Column(Date, nullable=False)
    valor            = Column(Numeric(15,2), nullable=False)
    forma            = Column(SAEnum(FormaRecebimento, name="forma_recebimento"), nullable=False)
    banco            = Column(String(100))
    agencia          = Column(String(20))
    conta            = Column(String(30))
    identificador    = Column(String(100))
    observacoes      = Column(Text)
    criado_em        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por       = Column(String(100), nullable=False)
    cobranca         = relationship("Cobranca", back_populates="recebimentos")


class Negociacao(Base):
    __tablename__ = "negociacoes"
    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cobranca_id        = Column(UUID(as_uuid=True), ForeignKey("cobrancas.id", ondelete="RESTRICT"), nullable=False)
    status             = Column(SAEnum(StatusNegociacao, name="status_negociacao"), nullable=False, default=StatusNegociacao.EM_NEGOCIACAO)
    valor_original     = Column(Numeric(15,2), nullable=False)
    valor_negociado    = Column(Numeric(15,2), nullable=False)
    motivo             = Column(Text, nullable=False)
    condicoes          = Column(Text)
    num_parcelas       = Column(Integer, nullable=False, default=1)
    data_negociacao    = Column(Date, nullable=False)
    data_aprovacao     = Column(Date)
    aprovado_por       = Column(String(100))
    criado_em          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por         = Column(String(100), nullable=False)
    cobranca           = relationship("Cobranca", back_populates="negociacoes")


# ================================================================
# SCHEMAS
# ================================================================

class RecebimentoCreate(BaseModel):
    data_recebimento: date
    valor:            Decimal = Field(..., gt=0)
    forma:            FormaRecebimento
    banco:            Optional[str] = None
    agencia:          Optional[str] = None
    conta:            Optional[str] = None
    identificador:    Optional[str] = None
    observacoes:      Optional[str] = None

class RecebimentoOut(RecebimentoCreate):
    id:        uuid.UUID
    criado_em: datetime
    model_config = {"from_attributes": True}


class NegociacaoCreate(BaseModel):
    valor_negociado: Decimal = Field(..., gt=0)
    motivo:          str     = Field(..., min_length=10)
    condicoes:       Optional[str] = None
    num_parcelas:    int     = Field(default=1, ge=1, le=60)

class NegociacaoOut(BaseModel):
    id:                uuid.UUID
    status:            StatusNegociacao
    valor_original:    Decimal
    valor_negociado:   Decimal
    desconto_concedido:Decimal
    motivo:            str
    num_parcelas:      int
    data_negociacao:   date
    aprovado_por:      Optional[str]
    model_config = {"from_attributes": True}


class CobrancaAtualizarERP(BaseModel):
    numero_erp:  Optional[str] = None
    observacoes: Optional[str] = None

class CobrancaOut(BaseModel):
    id:              uuid.UUID
    numero_cobranca: str
    fatura_id:       uuid.UUID
    contrato_id:     uuid.UUID
    cliente_id:      uuid.UUID
    competencia:     date
    data_emissao:    date
    data_vencimento: date
    valor_original:  Decimal
    valor_juros:     Decimal
    valor_multa:     Decimal
    valor_desconto:  Decimal
    valor_recebido:  Decimal
    status:          StatusCobranca
    numero_erp:      Optional[str]
    numero_nf:       Optional[str]
    observacoes:     Optional[str]
    criado_em:       datetime
    recebimentos:    list[RecebimentoOut]  = []
    negociacoes:     list[NegociacaoOut]   = []
    model_config = {"from_attributes": True}

class CobrancaResumoOut(BaseModel):
    id:              uuid.UUID
    numero_cobranca: str
    cliente_nome:    str
    contrato_numero: str
    modalidade:      str
    competencia:     date
    data_vencimento: date
    valor_original:  Decimal
    valor_recebido:  Decimal
    valor_saldo:     Decimal
    dias_atraso:     int
    faixa_aging:     str
    status:          StatusCobranca
    model_config = {"from_attributes": True}

class AgingResumoOut(BaseModel):
    faixa:           str
    quantidade:      int
    valor_total:     Decimal
    model_config = {"from_attributes": True}
