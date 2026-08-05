import enum
import uuid
from decimal import Decimal
from sqlalchemy import (
    Column, String, Boolean, Text, Date, Integer, Numeric,
    ForeignKey, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base
from app.models.contrato import ModalidadeContrato


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------

class StatusProduto(str, enum.Enum):
    ATIVO          = "ATIVO"
    DESCONTINUADO  = "DESCONTINUADO"
    SUSPENSO       = "SUSPENSO"

class TipoMovimentacao(str, enum.Enum):
    CANCELAMENTO  = "CANCELAMENTO"
    SUSPENSAO     = "SUSPENSAO"
    REATIVACAO    = "REATIVACAO"
    SUBSTITUICAO  = "SUBSTITUICAO"


# ------------------------------------------------------------------
# Pacote mínimo
# ------------------------------------------------------------------

class ProdutoPacote(Base):
    __tablename__ = "produtos_pacotes"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    modalidade  = Column(SAEnum(ModalidadeContrato, name="modalidade_contrato"), nullable=False)
    nome        = Column(String(150), nullable=False)
    descricao   = Column(Text)
    ativo       = Column(Boolean, nullable=False, default=True)
    criado_em   = Column(DateTime(timezone=True), server_default=func.now())
    criado_por  = Column(String(100))

    itens       = relationship("ProdutoPacoteItem", back_populates="pacote", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("modalidade", "nome", name="uq_pacote_nome_modalidade"),
    )


class ProdutoPacoteItem(Base):
    __tablename__ = "produtos_pacotes_itens"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    pacote_id       = Column(Integer, ForeignKey("produtos_pacotes.id", ondelete="CASCADE"), nullable=False)
    produto_id      = Column(Integer, ForeignKey("produtos_servicos.id", ondelete="RESTRICT"), nullable=False)
    quantidade_min  = Column(Numeric(10, 3), nullable=False, default=1)
    obrigatorio     = Column(Boolean, nullable=False, default=True)
    observacoes     = Column(Text)

    pacote          = relationship("ProdutoPacote", back_populates="itens")
    produto         = relationship("ProdutoServico", foreign_keys=[produto_id])

    __table_args__ = (
        UniqueConstraint("pacote_id", "produto_id", name="uq_pacote_produto"),
    )


# ------------------------------------------------------------------
# Movimentação de item em contrato
# ------------------------------------------------------------------

class ContratoItemMovimentacao(Base):
    __tablename__ = "contratos_itens_movimentacoes"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id         = Column(UUID(as_uuid=True), ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    contrato_item_id    = Column(UUID(as_uuid=True), ForeignKey("contratos_itens.id", ondelete="CASCADE"), nullable=False)
    tipo                = Column(SAEnum(TipoMovimentacao, name="tipo_movimentacao"), nullable=False)
    data_solicitacao    = Column(Date, nullable=False, server_default=func.current_date())
    data_efetivacao     = Column(Date, nullable=False)
    motivo              = Column(Text, nullable=False)
    novo_item_id        = Column(UUID(as_uuid=True), ForeignKey("contratos_itens.id"), nullable=True)
    valor_anterior      = Column(Numeric(15, 2))
    valor_novo          = Column(Numeric(15, 2))
    aditivo_id          = Column(UUID(as_uuid=True), ForeignKey("contratos_aditivos.id"), nullable=True)
    criado_por          = Column(String(100), nullable=False)
    criado_em           = Column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------------
# Referência ao model ProdutoServico do módulo 02
# (importado para uso nos relacionamentos dos pacotes)
# ------------------------------------------------------------------
# O model ProdutoServico está em app.models.contrato
# Adicionamos aqui apenas um alias para clareza
from app.models.contrato import ProdutoServico  # noqa: F401, E402
