import uuid
import enum
from decimal import Decimal
from sqlalchemy import (
    Column, String, Boolean, Text, Date, Integer, Numeric,
    ForeignKey, Enum as SAEnum, UniqueConstraint, Table
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base
from app.models.contrato import ProdutoServico  # noqa: F401


# ------------------------------------------------------------------
# Adiciona campo ao ProdutoServico (declarado no módulo 02)
# ------------------------------------------------------------------
if not hasattr(ProdutoServico, "mao_de_obra_alocada"):
    ProdutoServico.mao_de_obra_alocada = Column(Boolean, nullable=False, default=False, server_default="false")


# ------------------------------------------------------------------
# Tabela dissidios_historico (acesso via SQL raw no service)
# ------------------------------------------------------------------
dissidios_historico_table = Table(
    "dissidios_historico",
    Base.metadata,
    Column("id",               Integer, primary_key=True, autoincrement=True),
    Column("categoria",        String(100), nullable=False, default="GERAL"),
    Column("ano_base",         Integer, nullable=False),
    Column("data_vigencia",    Date, nullable=False),
    Column("valor_percentual", Numeric(8, 4), nullable=False),
    Column("fonte",            String(200)),
    Column("criado_em",        TIMESTAMPTZ, server_default=func.now()),
    Column("criado_por",       String(100)),
    extend_existing=True,
)


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------

class IndiceEconomico(str, enum.Enum):
    INPC     = "INPC"
    IPCA     = "IPCA"
    IGPM     = "IGPM"
    FIXO     = "FIXO"
    DISSIDIO = "DISSIDIO"

class StatusReajuste(str, enum.Enum):
    CALCULADO             = "CALCULADO"
    AGUARDANDO_APROVACAO  = "AGUARDANDO_APROVACAO"
    APROVADO              = "APROVADO"
    REPROVADO             = "REPROVADO"
    COMUNICADO            = "COMUNICADO"
    EFETIVADO             = "EFETIVADO"
    CANCELADO             = "CANCELADO"

class TipoAditivo(str, enum.Enum):
    REAJUSTE  = "REAJUSTE"
    PRAZO     = "PRAZO"
    ESCOPO    = "ESCOPO"
    RESCISAO  = "RESCISAO"
    OUTROS    = "OUTROS"


# ------------------------------------------------------------------
# Histórico de índices econômicos
# ------------------------------------------------------------------

class IndiceHistorico(Base):
    __tablename__ = "indices_economicos_historico"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    indice           = Column(SAEnum(IndiceEconomico, name="indice_economico"), nullable=False)
    competencia      = Column(Date, nullable=False)
    valor_percentual = Column(Numeric(8, 4), nullable=False)
    fonte            = Column(String(100))
    criado_em        = Column(DateTime(timezone=True), server_default=func.now())
    criado_por       = Column(String(100))

    __table_args__ = (
        UniqueConstraint("indice", "competencia", name="uq_indice_competencia"),
    )


# ------------------------------------------------------------------
# Reajuste de contrato
# ------------------------------------------------------------------

class ContratoReajuste(Base):
    __tablename__ = "contratos_reajustes"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id            = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="RESTRICT"), nullable=False)
    numero_reajuste        = Column(Integer, nullable=False)

    indice                 = Column(SAEnum(IndiceEconomico, name="indice_economico"), nullable=False)
    percentual_fixo        = Column(Numeric(8, 4))
    data_base              = Column(Date, nullable=False)
    data_fim_periodo       = Column(Date, nullable=False)
    competencia_inicial    = Column(Date, nullable=False)
    competencia_final      = Column(Date, nullable=False)

    percentual_calculado   = Column(Numeric(8, 4))
    percentual_aplicado    = Column(Numeric(8, 4))

    valor_mensal_anterior  = Column(Numeric(15, 2), nullable=False)
    valor_mensal_novo      = Column(Numeric(15, 2))
    variacao_mensal        = Column(Numeric(15, 2))

    status                 = Column(SAEnum(StatusReajuste, name="status_reajuste"), nullable=False, default=StatusReajuste.CALCULADO)
    data_calculo           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    calculado_por          = Column(String(100), nullable=False)
    data_aprovacao         = Column(DateTime(timezone=True))
    aprovado_por           = Column(String(100))
    motivo_reprovacao      = Column(Text)
    data_comunicacao       = Column(Date)
    data_efetivacao        = Column(Date, nullable=False)
    observacoes            = Column(Text)
    aditivo_id             = Column(UUID(as_uuid=True), ForeignKey("contratos_aditivos.id"), nullable=True)

    criado_em              = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em          = Column(DateTime(timezone=True), server_default=func.now())

    itens                  = relationship("ReajusteItem", back_populates="reajuste", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("contrato_id", "numero_reajuste", name="uq_reajuste_numero"),
    )


# ------------------------------------------------------------------
# Item do reajuste
# ------------------------------------------------------------------

class ReajusteItem(Base):
    __tablename__ = "contratos_reajustes_itens"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reajuste_id         = Column(UUID(as_uuid=True), ForeignKey("contratos_reajustes.id", ondelete="CASCADE"), nullable=False)
    contrato_item_id    = Column(UUID(as_uuid=True), ForeignKey("contratos_itens.id", ondelete="RESTRICT"), nullable=False)
    valor_anterior      = Column(Numeric(15, 2), nullable=False)
    percentual_aplicado = Column(Numeric(8, 4), nullable=False)
    valor_novo          = Column(Numeric(15, 2), nullable=False)
    usa_dissidio        = Column(Boolean, nullable=False, default=False)
    aprovado            = Column(Boolean)
    observacoes         = Column(Text)

    reajuste            = relationship("ContratoReajuste", back_populates="itens")
