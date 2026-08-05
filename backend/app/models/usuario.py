import uuid
import enum
from sqlalchemy import Column, String, Boolean, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base


class PerfilUsuario(str, enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    COMERCIAL     = "COMERCIAL"
    OPERACIONAL   = "OPERACIONAL"
    FINANCEIRO    = "FINANCEIRO"
    GESTAO        = "GESTAO"


class Usuario(Base):
    __tablename__ = "usuarios"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome          = Column(String(200), nullable=False)
    email         = Column(String(254), nullable=False, unique=True)
    senha_hash    = Column(String(255), nullable=False)
    perfil        = Column(SAEnum(PerfilUsuario, name="perfil_usuario"), nullable=False)
    ativo         = Column(Boolean, nullable=False, default=True)
    ultimo_acesso = Column(DateTime(timezone=True))
    criado_em     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por    = Column(String(100))
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PerfilPermissao(Base):
    __tablename__ = "perfis_permissoes"

    id      = Column(String(50), primary_key=True, autoincrement=True)
    perfil  = Column(SAEnum(PerfilUsuario, name="perfil_usuario"), nullable=False)
    modulo  = Column(String(50), nullable=False)
    ler     = Column(Boolean, nullable=False, default=False)
    criar   = Column(Boolean, nullable=False, default=False)
    editar  = Column(Boolean, nullable=False, default=False)
    excluir = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("perfil", "modulo", name="uq_perfil_modulo"),
    )
