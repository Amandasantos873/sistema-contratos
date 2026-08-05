import uuid
import enum
from sqlalchemy import Column, String, Boolean, Text, Date, Integer, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base


class SeveridadeAlerta(str, enum.Enum):
    CRITICO = "CRITICO"
    ATENCAO = "ATENCAO"
    INFO    = "INFO"

class StatusValidacao(str, enum.Enum):
    APROVADA     = "APROVADA"
    COM_ALERTAS  = "COM_ALERTAS"
    BLOQUEADA    = "BLOQUEADA"
    JUSTIFICADA  = "JUSTIFICADA"

class StatusAlerta(str, enum.Enum):
    ABERTO      = "ABERTO"
    JUSTIFICADO = "JUSTIFICADO"
    RESOLVIDO   = "RESOLVIDO"
    IGNORADO    = "IGNORADO"


class FaturaValidacao(Base):
    __tablename__ = "faturas_validacoes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fatura_id       = Column(UUID(as_uuid=True), ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False)
    status          = Column(SAEnum(StatusValidacao, name="status_validacao"), nullable=False)
    total_criticos  = Column(Integer, nullable=False, default=0)
    total_atencao   = Column(Integer, nullable=False, default=0)
    total_info      = Column(Integer, nullable=False, default=0)
    executado_em    = Column(DateTime(timezone=True), server_default=func.now())
    executado_por   = Column(String(100), nullable=False)
    analise_ia      = Column(JSONB)
    analise_ia_em   = Column(DateTime(timezone=True))

    alertas         = relationship("FaturaAlerta", back_populates="validacao", cascade="all, delete-orphan")


class FaturaAlerta(Base):
    __tablename__ = "faturas_alertas"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validacao_id     = Column(UUID(as_uuid=True), ForeignKey("faturas_validacoes.id", ondelete="CASCADE"), nullable=False)
    fatura_id        = Column(UUID(as_uuid=True), ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False)
    codigo           = Column(String(20), ForeignKey("codigos_alerta.codigo"), nullable=False)
    severidade       = Column(SAEnum(SeveridadeAlerta, name="severidade_alerta"), nullable=False)
    detalhe          = Column(Text, nullable=False)
    item_referencia  = Column(UUID(as_uuid=True))
    valor_esperado   = Column(Numeric(15, 2))
    valor_encontrado = Column(Numeric(15, 2))
    status           = Column(SAEnum(StatusAlerta, name="status_alerta"), nullable=False, default=StatusAlerta.ABERTO)
    justificativa    = Column(Text)
    justificado_por  = Column(String(100))
    justificado_em   = Column(DateTime(timezone=True))
    criado_em        = Column(DateTime(timezone=True), server_default=func.now())

    validacao        = relationship("FaturaValidacao", back_populates="alertas")


class AvisoPrevioCancelamento(Base):
    __tablename__ = "aviso_previo_cancelamento"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_item_id    = Column(UUID(as_uuid=True), ForeignKey("contratos_itens.id", ondelete="CASCADE"), nullable=False)
    data_solicitacao    = Column(Date, nullable=False)
    prazo_vigencia_dias = Column(Integer, nullable=False, default=30)
    data_fim_vigencia   = Column(Date, nullable=False)
    motivo              = Column(Text, nullable=False)
    status              = Column(String(20), nullable=False, default="ATIVO")
    criado_por          = Column(String(100), nullable=False)
    criado_em           = Column(DateTime(timezone=True), server_default=func.now())
