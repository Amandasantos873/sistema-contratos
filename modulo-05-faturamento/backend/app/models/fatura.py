import uuid
import enum
from sqlalchemy import (
    Column, String, Boolean, Text, Date, Integer, Numeric,
    ForeignKey, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base


class StatusFatura(str, enum.Enum):
    RASCUNHO    = "RASCUNHO"
    APURADA     = "APURADA"
    EMITIDA     = "EMITIDA"
    ENVIADA     = "ENVIADA"
    PAGA        = "PAGA"
    CANCELADA   = "CANCELADA"
    INADIMPLENTE= "INADIMPLENTE"

class TipoDocumentoFat(str, enum.Enum):
    RPS              = "RPS"
    NFS_E            = "NFS_E"
    BOLETO           = "BOLETO"
    BOLETIM_MEDICAO  = "BOLETIM_MEDICAO"
    DESCRITIVO       = "DESCRITIVO"

class StatusDocumento(str, enum.Enum):
    PENDENTE  = "PENDENTE"
    EMITIDO   = "EMITIDO"
    ENVIADO   = "ENVIADO"
    CANCELADO = "CANCELADO"
    ERRO      = "ERRO"

class TipoVinculoFolha(str, enum.Enum):
    CLT        = "CLT"
    AUTONOMO   = "AUTONOMO"
    ESTAGIARIO = "ESTAGIARIO"
    SOCIO      = "SOCIO"
    DIRETOR    = "DIRETOR"
    COOPERADO  = "COOPERADO"
    OUTROS     = "OUTROS"


class FaixaVolumetria(Base):
    __tablename__ = "faixas_volumetria"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    produto_id      = Column(Integer, ForeignKey("produtos_servicos.id", ondelete="CASCADE"), nullable=False)
    tipo_vinculo    = Column(SAEnum(TipoVinculoFolha, name="tipo_vinculo_folha"), nullable=False)
    faixa_de        = Column(Integer, nullable=False)
    faixa_ate       = Column(Integer)
    valor_unitario  = Column(Numeric(15, 4), nullable=False)
    ativo           = Column(Boolean, nullable=False, default=True)
    vigencia_inicio = Column(Date, nullable=False)
    vigencia_fim    = Column(Date)
    criado_em       = Column(DateTime(timezone=True), server_default=func.now())
    criado_por      = Column(String(100))


class Fatura(Base):
    __tablename__ = "faturas"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id         = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="RESTRICT"), nullable=False)
    numero_fatura       = Column(String(30), unique=True)
    competencia         = Column(Date, nullable=False)
    dia_apuracao        = Column(SAEnum("dia_faturamento", name="dia_faturamento"), nullable=False)
    data_apuracao       = Column(Date, nullable=False)
    data_vencimento     = Column(Date, nullable=False)
    status              = Column(SAEnum(StatusFatura, name="status_fatura"), nullable=False, default=StatusFatura.RASCUNHO)

    valor_servicos      = Column(Numeric(15, 2), nullable=False, default=0)
    valor_volumetria    = Column(Numeric(15, 2), nullable=False, default=0)
    valor_pago          = Column(Numeric(15, 2))
    data_pagamento      = Column(Date)

    descricao_nf        = Column(Text)
    numero_nf           = Column(String(30))
    serie_nf            = Column(String(10))
    codigo_verificacao  = Column(String(50))
    data_emissao_nf     = Column(Date)

    observacoes         = Column(Text)
    criado_em           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por          = Column(String(100), nullable=False)
    atualizado_em       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_por      = Column(String(100), nullable=False)

    itens               = relationship("FaturaItem",       back_populates="fatura", cascade="all, delete-orphan")
    volumetrias         = relationship("FaturaVolumetria", back_populates="fatura", cascade="all, delete-orphan")
    documentos          = relationship("FaturaDocumento",  back_populates="fatura", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("contrato_id", "competencia", name="uq_fatura_contrato_competencia"),
    )


class FaturaItem(Base):
    __tablename__ = "faturas_itens"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fatura_id           = Column(UUID(as_uuid=True), ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False)
    contrato_item_id    = Column(UUID(as_uuid=True), ForeignKey("contratos_itens.id", ondelete="RESTRICT"), nullable=False)
    produto_id          = Column(Integer, ForeignKey("produtos_servicos.id"), nullable=False)
    descricao           = Column(String(300), nullable=False)
    quantidade          = Column(Numeric(10, 3), nullable=False, default=1)
    valor_unitario      = Column(Numeric(15, 4), nullable=False)
    desconto_pct        = Column(Numeric(5, 2), nullable=False, default=0)
    eh_volumetria       = Column(Boolean, nullable=False, default=False)
    observacoes         = Column(Text)

    fatura              = relationship("Fatura", back_populates="itens")


class FaturaVolumetria(Base):
    __tablename__ = "faturas_volumetrias"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fatura_id           = Column(UUID(as_uuid=True), ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False)
    contrato_item_id    = Column(UUID(as_uuid=True), ForeignKey("contratos_itens.id"), nullable=False)
    tipo_vinculo        = Column(SAEnum(TipoVinculoFolha, name="tipo_vinculo_folha"), nullable=False)
    quantidade          = Column(Integer, nullable=False)
    valor_unitario      = Column(Numeric(15, 4), nullable=False)
    fonte               = Column(String(100), default="INTEGRACAO_FOLHA")
    competencia_folha   = Column(Date)
    criado_em           = Column(DateTime(timezone=True), server_default=func.now())

    fatura              = relationship("Fatura", back_populates="volumetrias")


class FaturaDocumento(Base):
    __tablename__ = "faturas_documentos"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fatura_id       = Column(UUID(as_uuid=True), ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False)
    tipo            = Column(SAEnum(TipoDocumentoFat, name="tipo_documento_fat"), nullable=False)
    status          = Column(SAEnum(StatusDocumento, name="status_documento"), nullable=False, default=StatusDocumento.PENDENTE)
    numero          = Column(String(50))
    url             = Column(String(500))
    payload_envio   = Column(JSONB)
    payload_retorno = Column(JSONB)
    mensagem_erro   = Column(Text)
    emitido_em      = Column(DateTime(timezone=True))
    emitido_por     = Column(String(100))
    criado_em       = Column(DateTime(timezone=True), server_default=func.now())

    fatura          = relationship("Fatura", back_populates="documentos")
