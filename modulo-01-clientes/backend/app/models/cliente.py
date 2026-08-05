import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Text, DateTime,
    ForeignKey, Integer, Enum as SAEnum, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
import enum


# ------------------------------------------------------------------
# Enums Python (espelham os tipos do PostgreSQL)
# ------------------------------------------------------------------

class TipoPessoa(str, enum.Enum):
    PF = "PF"
    PJ = "PJ"

class PorteEmpresa(str, enum.Enum):
    MEI      = "MEI"
    MICRO    = "MICRO"
    PEQUENO  = "PEQUENO"
    MEDIO    = "MEDIO"
    GRANDE   = "GRANDE"

class StatusCliente(str, enum.Enum):
    PROSPECTO = "PROSPECTO"
    ATIVO     = "ATIVO"
    INATIVO   = "INATIVO"
    BLOQUEADO = "BLOQUEADO"

class TipoEndereco(str, enum.Enum):
    MATRIZ    = "MATRIZ"
    FILIAL    = "FILIAL"
    COBRANCA  = "COBRANCA"
    ENTREGA   = "ENTREGA"

class TipoContato(str, enum.Enum):
    FINANCEIRO = "FINANCEIRO"
    CONTRATO   = "CONTRATO"
    TECNICO    = "TECNICO"
    COMERCIAL  = "COMERCIAL"
    OUTRO      = "OUTRO"


# ------------------------------------------------------------------
# Segmento
# ------------------------------------------------------------------

class Segmento(Base):
    __tablename__ = "segmentos"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    nome      = Column(String(100), nullable=False, unique=True)
    descricao = Column(Text)
    ativo     = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    clientes  = relationship("Cliente", back_populates="segmento")


# ------------------------------------------------------------------
# Cliente
# ------------------------------------------------------------------

class Cliente(Base):
    __tablename__ = "clientes"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_pessoa         = Column(SAEnum(TipoPessoa, name="tipo_pessoa"), nullable=False)

    # PJ
    razao_social        = Column(String(200))
    nome_fantasia       = Column(String(200))
    cnpj                = Column(String(14), unique=True)
    inscricao_estadual  = Column(String(20))
    inscricao_municipal = Column(String(20))

    # PF
    nome_completo       = Column(String(200))
    cpf                 = Column(String(11), unique=True)

    # Classificação
    segmento_id         = Column(Integer, ForeignKey("segmentos.id", ondelete="SET NULL"))
    porte               = Column(SAEnum(PorteEmpresa, name="porte_empresa"))
    origem              = Column(String(100))
    observacoes         = Column(Text)

    # Status
    status              = Column(SAEnum(StatusCliente, name="status_cliente"), nullable=False, default=StatusCliente.PROSPECTO)
    motivo_inativacao   = Column(Text)
    inativado_em        = Column(DateTime(timezone=True))
    inativado_por       = Column(String(100))

    # Auditoria
    criado_em           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por          = Column(String(100), nullable=False)
    atualizado_em       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    atualizado_por      = Column(String(100), nullable=False)

    # Relacionamentos
    segmento            = relationship("Segmento", back_populates="clientes")
    enderecos           = relationship("ClienteEndereco", back_populates="cliente", cascade="all, delete-orphan")
    contatos            = relationship("ClienteContato",  back_populates="cliente", cascade="all, delete-orphan")
    historico           = relationship("ClienteHistorico", back_populates="cliente", cascade="all, delete-orphan")


# ------------------------------------------------------------------
# Endereço
# ------------------------------------------------------------------

class ClienteEndereco(Base):
    __tablename__ = "clientes_enderecos"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id   = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    tipo         = Column(SAEnum(TipoEndereco, name="tipo_endereco"), nullable=False, default=TipoEndereco.MATRIZ)
    principal    = Column(Boolean, nullable=False, default=False)

    cep          = Column(String(8), nullable=False)
    logradouro   = Column(String(200), nullable=False)
    numero       = Column(String(20), nullable=False)
    complemento  = Column(String(100))
    bairro       = Column(String(100), nullable=False)
    cidade       = Column(String(100), nullable=False)
    uf           = Column(String(2), nullable=False)
    ibge_codigo  = Column(String(7))

    ativo        = Column(Boolean, nullable=False, default=True)
    criado_em    = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em= Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cliente      = relationship("Cliente", back_populates="enderecos")


# ------------------------------------------------------------------
# Contato
# ------------------------------------------------------------------

class ClienteContato(Base):
    __tablename__ = "clientes_contatos"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id    = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)

    nome          = Column(String(200), nullable=False)
    cargo         = Column(String(100))
    departamento  = Column(String(100))
    email         = Column(String(254))
    telefone      = Column(String(20))
    whatsapp      = Column(String(20))
    linkedin      = Column(String(200))

    is_financeiro = Column(Boolean, nullable=False, default=False)
    is_contrato   = Column(Boolean, nullable=False, default=False)
    is_tecnico    = Column(Boolean, nullable=False, default=False)
    is_comercial  = Column(Boolean, nullable=False, default=False)

    principal     = Column(Boolean, nullable=False, default=False)
    ativo         = Column(Boolean, nullable=False, default=True)
    observacoes   = Column(Text)

    criado_em     = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cliente       = relationship("Cliente", back_populates="contatos")


# ------------------------------------------------------------------
# Histórico de auditoria
# ------------------------------------------------------------------

class ClienteHistorico(Base):
    __tablename__ = "clientes_historico"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id     = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    operacao       = Column(String(1), nullable=False)
    campo_alterado = Column(String(100))
    valor_anterior = Column(Text)
    valor_novo     = Column(Text)
    alterado_por   = Column(String(100), nullable=False)
    alterado_em    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_origem      = Column(INET)
    motivo         = Column(Text)

    cliente        = relationship("Cliente", back_populates="historico")
