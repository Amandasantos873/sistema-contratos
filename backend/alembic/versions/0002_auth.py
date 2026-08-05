"""Migration autenticação — usuários e perfis de acesso

Revision ID: 0002_auth
Revises: 0001_initial
Create Date: 2026-01-02 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_auth"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum de perfis
    op.execute("""
        CREATE TYPE perfil_usuario AS ENUM (
            'ADMINISTRADOR',
            'COMERCIAL',
            'OPERACIONAL',
            'FINANCEIRO',
            'GESTAO'
        )
    """)

    # Tabela de usuários
    op.create_table("usuarios",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("nome",         sa.String(200), nullable=False),
        sa.Column("email",        sa.String(254), nullable=False, unique=True),
        sa.Column("senha_hash",   sa.String(255), nullable=False),
        sa.Column("perfil",       postgresql.ENUM(
                                    "ADMINISTRADOR","COMERCIAL","OPERACIONAL","FINANCEIRO","GESTAO",
                                    name="perfil_usuario", create_type=False
                                  ), nullable=False),
        sa.Column("ativo",        sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ultimo_acesso",sa.TIMESTAMP(timezone=True)),
        sa.Column("criado_em",    sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("criado_por",   sa.String(100)),
        sa.Column("atualizado_em",sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_usuarios_email",  "usuarios", ["email"])
    op.create_index("idx_usuarios_perfil", "usuarios", ["perfil"])
    op.create_index("idx_usuarios_ativo",  "usuarios", ["ativo"])

    # Tabela de permissões por perfil e módulo
    op.create_table("perfis_permissoes",
        sa.Column("id",      sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("perfil",  postgresql.ENUM(
                                "ADMINISTRADOR","COMERCIAL","OPERACIONAL","FINANCEIRO","GESTAO",
                                name="perfil_usuario", create_type=False
                             ), nullable=False),
        sa.Column("modulo",  sa.String(50),  nullable=False),   # clientes, contratos, faturamento...
        sa.Column("ler",     sa.Boolean, nullable=False, server_default="false"),
        sa.Column("criar",   sa.Boolean, nullable=False, server_default="false"),
        sa.Column("editar",  sa.Boolean, nullable=False, server_default="false"),
        sa.Column("excluir", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("perfil","modulo", name="uq_perfil_modulo"),
    )

    # Permissões por perfil
    op.execute("""
        INSERT INTO perfis_permissoes (perfil, modulo, ler, criar, editar, excluir) VALUES
        -- ADMINISTRADOR: acesso total
        ('ADMINISTRADOR','clientes',    true,true,true,true),
        ('ADMINISTRADOR','contratos',   true,true,true,true),
        ('ADMINISTRADOR','produtos',    true,true,true,true),
        ('ADMINISTRADOR','reajustes',   true,true,true,true),
        ('ADMINISTRADOR','faturamento', true,true,true,true),
        ('ADMINISTRADOR','validacao',   true,true,true,true),
        ('ADMINISTRADOR','golive',      true,true,true,true),
        ('ADMINISTRADOR','usuarios',    true,true,true,true),

        -- COMERCIAL: clientes e contratos
        ('COMERCIAL','clientes',    true,true,true,false),
        ('COMERCIAL','contratos',   true,true,true,false),
        ('COMERCIAL','produtos',    true,false,false,false),
        ('COMERCIAL','reajustes',   false,false,false,false),
        ('COMERCIAL','faturamento', false,false,false,false),
        ('COMERCIAL','validacao',   false,false,false,false),
        ('COMERCIAL','golive',      true,true,true,false),
        ('COMERCIAL','usuarios',    false,false,false,false),

        -- OPERACIONAL: go-live e acompanhamento
        ('OPERACIONAL','clientes',    true,false,false,false),
        ('OPERACIONAL','contratos',   true,false,false,false),
        ('OPERACIONAL','produtos',    true,false,false,false),
        ('OPERACIONAL','reajustes',   false,false,false,false),
        ('OPERACIONAL','faturamento', false,false,false,false),
        ('OPERACIONAL','validacao',   false,false,false,false),
        ('OPERACIONAL','golive',      true,true,true,false),
        ('OPERACIONAL','usuarios',    false,false,false,false),

        -- FINANCEIRO: faturamento e reajustes
        ('FINANCEIRO','clientes',    true,false,false,false),
        ('FINANCEIRO','contratos',   true,false,false,false),
        ('FINANCEIRO','produtos',    true,false,false,false),
        ('FINANCEIRO','reajustes',   true,true,true,false),
        ('FINANCEIRO','faturamento', true,true,true,false),
        ('FINANCEIRO','validacao',   true,true,false,false),
        ('FINANCEIRO','golive',      true,false,false,false),
        ('FINANCEIRO','usuarios',    false,false,false,false),

        -- GESTAO: somente visualização
        ('GESTAO','clientes',    true,false,false,false),
        ('GESTAO','contratos',   true,false,false,false),
        ('GESTAO','produtos',    true,false,false,false),
        ('GESTAO','reajustes',   true,false,false,false),
        ('GESTAO','faturamento', true,false,false,false),
        ('GESTAO','validacao',   true,false,false,false),
        ('GESTAO','golive',      true,false,false,false),
        ('GESTAO','usuarios',    false,false,false,false)
    """)


def downgrade() -> None:
    op.drop_table("perfis_permissoes")
    op.drop_table("usuarios")
    op.execute("DROP TYPE IF EXISTS perfil_usuario")
