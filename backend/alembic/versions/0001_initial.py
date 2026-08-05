"""Migration inicial — cria todas as tabelas do sistema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ================================================================
    # EXTENSÕES
    # ================================================================
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "unaccent"')

    # ================================================================
    # ENUMS
    # ================================================================
    op.execute("CREATE TYPE tipo_pessoa          AS ENUM ('PF','PJ')")
    op.execute("CREATE TYPE porte_empresa        AS ENUM ('MEI','MICRO','PEQUENO','MEDIO','GRANDE')")
    op.execute("CREATE TYPE status_cliente       AS ENUM ('PROSPECTO','ATIVO','INATIVO','BLOQUEADO')")
    op.execute("CREATE TYPE tipo_endereco        AS ENUM ('MATRIZ','FILIAL','COBRANCA','ENTREGA')")
    op.execute("CREATE TYPE modalidade_contrato  AS ENUM ('ASP','BSP','BPO')")
    op.execute("CREATE TYPE status_contrato      AS ENUM ('PROPOSTA','ATIVO','SUSPENSO','ENCERRADO','CANCELADO')")
    op.execute("CREATE TYPE fase_contrato        AS ENUM ('IMPLANTACAO','RECORRENCIA')")
    op.execute("CREATE TYPE dia_faturamento      AS ENUM ('DIA_01','DIA_15','DIA_25')")
    op.execute("CREATE TYPE status_parcela_impl  AS ENUM ('PENDENTE','FATURADA','PAGA','CANCELADA')")
    op.execute("CREATE TYPE status_contrato_item AS ENUM ('IMPLANTACAO','ATIVO','SUSPENSO','CANCELADO')")
    op.execute("CREATE TYPE status_produto       AS ENUM ('ATIVO','DESCONTINUADO','SUSPENSO')")
    op.execute("CREATE TYPE tipo_movimentacao    AS ENUM ('CANCELAMENTO','SUSPENSAO','REATIVACAO','SUBSTITUICAO')")
    op.execute("CREATE TYPE indice_economico     AS ENUM ('INPC','IPCA','IGPM','FIXO','DISSIDIO')")
    op.execute("CREATE TYPE status_reajuste      AS ENUM ('CALCULADO','AGUARDANDO_APROVACAO','APROVADO','REPROVADO','COMUNICADO','EFETIVADO','CANCELADO')")
    op.execute("CREATE TYPE tipo_aditivo         AS ENUM ('REAJUSTE','PRAZO','ESCOPO','RESCISAO','OUTROS')")
    op.execute("CREATE TYPE status_fatura        AS ENUM ('RASCUNHO','APURADA','EMITIDA','ENVIADA','PAGA','CANCELADA','INADIMPLENTE')")
    op.execute("CREATE TYPE tipo_documento_fat   AS ENUM ('RPS','NFS_E','BOLETO','BOLETIM_MEDICAO','DESCRITIVO')")
    op.execute("CREATE TYPE status_documento     AS ENUM ('PENDENTE','EMITIDO','ENVIADO','CANCELADO','ERRO')")
    op.execute("CREATE TYPE tipo_vinculo_folha   AS ENUM ('CLT','AUTONOMO','ESTAGIARIO','SOCIO','DIRETOR','COOPERADO','OUTROS')")
    op.execute("CREATE TYPE severidade_alerta    AS ENUM ('CRITICO','ATENCAO','INFO')")
    op.execute("CREATE TYPE status_validacao     AS ENUM ('APROVADA','COM_ALERTAS','BLOQUEADA','JUSTIFICADA')")
    op.execute("CREATE TYPE status_alerta        AS ENUM ('ABERTO','JUSTIFICADO','RESOLVIDO','IGNORADO')")

    # ================================================================
    # MÓDULO 01 — CLIENTES
    # ================================================================
    op.create_table("segmentos",
        sa.Column("id",        sa.Integer,     primary_key=True, autoincrement=True),
        sa.Column("nome",      sa.String(100), nullable=False, unique=True),
        sa.Column("descricao", sa.Text),
        sa.Column("ativo",     sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table("clientes",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tipo_pessoa",         postgresql.ENUM("PF","PJ", name="tipo_pessoa", create_type=False), nullable=False),
        sa.Column("razao_social",        sa.String(200)),
        sa.Column("nome_fantasia",       sa.String(200)),
        sa.Column("cnpj",                sa.String(14),  unique=True),
        sa.Column("inscricao_estadual",  sa.String(20)),
        sa.Column("inscricao_municipal", sa.String(20)),
        sa.Column("nome_completo",       sa.String(200)),
        sa.Column("cpf",                 sa.String(11),  unique=True),
        sa.Column("segmento_id",         sa.Integer,     sa.ForeignKey("segmentos.id", ondelete="SET NULL")),
        sa.Column("porte",               postgresql.ENUM("MEI","MICRO","PEQUENO","MEDIO","GRANDE", name="porte_empresa", create_type=False)),
        sa.Column("origem",              sa.String(100)),
        sa.Column("observacoes",         sa.Text),
        sa.Column("status",              postgresql.ENUM("PROSPECTO","ATIVO","INATIVO","BLOQUEADO", name="status_cliente", create_type=False), nullable=False, server_default="PROSPECTO"),
        sa.Column("motivo_inativacao",   sa.Text),
        sa.Column("inativado_em",        sa.TIMESTAMP(timezone=True)),
        sa.Column("inativado_por",       sa.String(100)),
        sa.Column("criado_em",           sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("criado_por",          sa.String(100), nullable=False),
        sa.Column("atualizado_em",       sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("atualizado_por",      sa.String(100), nullable=False),
    )
    op.create_table("clientes_enderecos",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("cliente_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo",         postgresql.ENUM("MATRIZ","FILIAL","COBRANCA","ENTREGA", name="tipo_endereco", create_type=False), nullable=False, server_default="MATRIZ"),
        sa.Column("principal",    sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cep",          sa.String(8),   nullable=False),
        sa.Column("logradouro",   sa.String(200), nullable=False),
        sa.Column("numero",       sa.String(20),  nullable=False),
        sa.Column("complemento",  sa.String(100)),
        sa.Column("bairro",       sa.String(100), nullable=False),
        sa.Column("cidade",       sa.String(100), nullable=False),
        sa.Column("uf",           sa.String(2),   nullable=False),
        sa.Column("ibge_codigo",  sa.String(7)),
        sa.Column("ativo",        sa.Boolean, nullable=False, server_default="true"),
        sa.Column("criado_em",    sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("atualizado_em",sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table("clientes_contatos",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("cliente_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome",          sa.String(200), nullable=False),
        sa.Column("cargo",         sa.String(100)),
        sa.Column("departamento",  sa.String(100)),
        sa.Column("email",         sa.String(254)),
        sa.Column("telefone",      sa.String(20)),
        sa.Column("whatsapp",      sa.String(20)),
        sa.Column("linkedin",      sa.String(200)),
        sa.Column("is_financeiro", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_contrato",   sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_tecnico",    sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_comercial",  sa.Boolean, nullable=False, server_default="false"),
        sa.Column("principal",     sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ativo",         sa.Boolean, nullable=False, server_default="true"),
        sa.Column("observacoes",   sa.Text),
        sa.Column("criado_em",     sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("atualizado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table("clientes_historico",
        sa.Column("id",             sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("cliente_id",     postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operacao",       sa.String(1),   nullable=False),
        sa.Column("campo_alterado", sa.String(100)),
        sa.Column("valor_anterior", sa.Text),
        sa.Column("valor_novo",     sa.Text),
        sa.Column("alterado_por",   sa.String(100), nullable=False),
        sa.Column("alterado_em",    sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("ip_origem",      postgresql.INET),
        sa.Column("motivo",         sa.Text),
    )

    # ================================================================
    # MÓDULO 02 — CONTRATOS
    # ================================================================
    op.create_table("produtos_servicos",
        sa.Column("id",               sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("modalidade",       postgresql.ENUM("ASP","BSP","BPO", name="modalidade_contrato", create_type=False), nullable=False),
        sa.Column("codigo",           sa.String(30),  nullable=False),
        sa.Column("nome",             sa.String(200), nullable=False),
        sa.Column("descricao",        sa.Text),
        sa.Column("unidade",          sa.String(30),  nullable=False, server_default="MÊS"),
        sa.Column("preco_tabela",     sa.Numeric(15,2)),
        sa.Column("permite_impl",     sa.Boolean, nullable=False, server_default="false"),
        sa.Column("permite_recorr",   sa.Boolean, nullable=False, server_default="true"),
        sa.Column("mao_de_obra_alocada", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status",           postgresql.ENUM("ATIVO","DESCONTINUADO","SUSPENSO", name="status_produto", create_type=False), nullable=False, server_default="ATIVO"),
        sa.Column("data_descontinuacao", sa.Date),
        sa.Column("motivo_descontinuacao", sa.Text),
        sa.Column("substituido_por",  sa.Integer, sa.ForeignKey("produtos_servicos.id")),
        sa.Column("versao",           sa.Integer, nullable=False, server_default="1"),
        sa.Column("ativo",            sa.Boolean, nullable=False, server_default="true"),
        sa.Column("criado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("criado_por",       sa.String(100)),
        sa.Column("atualizado_em",    sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("atualizado_por",   sa.String(100)),
        sa.UniqueConstraint("modalidade","codigo", name="uq_produto_codigo"),
    )
    op.create_table("contratos",
        sa.Column("id",                      postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("numero",                  sa.String(30),  unique=True),
        sa.Column("cliente_id",              postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("modalidade",              postgresql.ENUM("ASP","BSP","BPO", name="modalidade_contrato", create_type=False), nullable=False),
        sa.Column("data_assinatura",         sa.Date, nullable=False),
        sa.Column("data_inicio_impl",        sa.Date, nullable=False),
        sa.Column("data_goLive",             sa.Date),
        sa.Column("data_inicio_recorrencia", sa.Date),
        sa.Column("prazo_meses",             sa.Integer, nullable=False),
        sa.Column("data_fim_contrato",       sa.Date),
        sa.Column("data_renovacao",          sa.Date),
        sa.Column("dia_faturamento",         postgresql.ENUM("DIA_01","DIA_15","DIA_25", name="dia_faturamento", create_type=False), nullable=False),
        sa.Column("fase_atual",              postgresql.ENUM("IMPLANTACAO","RECORRENCIA", name="fase_contrato", create_type=False), nullable=False, server_default="IMPLANTACAO"),
        sa.Column("status",                  postgresql.ENUM("PROPOSTA","ATIVO","SUSPENSO","ENCERRADO","CANCELADO", name="status_contrato", create_type=False), nullable=False, server_default="PROPOSTA"),
        sa.Column("valor_total_impl",        sa.Numeric(15,2), nullable=False, server_default="0"),
        sa.Column("valor_mensal",            sa.Numeric(15,2), nullable=False, server_default="0"),
        sa.Column("responsavel_comercial",   sa.String(100)),
        sa.Column("responsavel_implantacao", sa.String(100)),
        sa.Column("numero_proposta",         sa.String(50)),
        sa.Column("observacoes",             sa.Text),
        sa.Column("criado_em",               sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("criado_por",              sa.String(100), nullable=False),
        sa.Column("atualizado_em",           sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("atualizado_por",          sa.String(100), nullable=False),
    )
    op.create_table("contratos_itens",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contrato_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("produto_id",           sa.Integer, sa.ForeignKey("produtos_servicos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade",           sa.Numeric(10,3), nullable=False, server_default="1"),
        sa.Column("valor_unitario",       sa.Numeric(15,2), nullable=False),
        sa.Column("desconto_pct",         sa.Numeric(5,2),  nullable=False, server_default="0"),
        sa.Column("fase",                 postgresql.ENUM("IMPLANTACAO","RECORRENCIA", name="fase_contrato", create_type=False), nullable=False),
        sa.Column("status_item",          postgresql.ENUM("IMPLANTACAO","ATIVO","SUSPENSO","CANCELADO", name="status_contrato_item", create_type=False), nullable=False, server_default="IMPLANTACAO"),
        sa.Column("data_goLive_item",     sa.Date),
        sa.Column("data_inicio_faturamento", sa.Date),
        sa.Column("goLive_confirmado_por",   sa.String(100)),
        sa.Column("goLive_confirmado_em",    sa.TIMESTAMP(timezone=True)),
        sa.Column("ativo",                sa.Boolean, nullable=False, server_default="true"),
        sa.Column("observacoes",          sa.Text),
        sa.Column("criado_em",            sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("atualizado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table("contratos_parcelas_implantacao",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contrato_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("numero_parcela",   sa.Integer, nullable=False),
        sa.Column("valor",            sa.Numeric(15,2), nullable=False),
        sa.Column("data_vencimento",  sa.Date, nullable=False),
        sa.Column("status",           postgresql.ENUM("PENDENTE","FATURADA","PAGA","CANCELADA", name="status_parcela_impl", create_type=False), nullable=False, server_default="PENDENTE"),
        sa.Column("data_faturamento", sa.Date),
        sa.Column("data_pagamento",   sa.Date),
        sa.Column("observacoes",      sa.Text),
        sa.Column("criado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("atualizado_em",    sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("contrato_id","numero_parcela", name="uq_parcela_contrato"),
    )
    op.create_table("contratos_aditivos",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contrato_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("numero_aditivo", sa.Integer, nullable=False),
        sa.Column("tipo",           sa.String(50),  nullable=False),
        sa.Column("tipo_aditivo",   postgresql.ENUM("REAJUSTE","PRAZO","ESCOPO","RESCISAO","OUTROS", name="tipo_aditivo", create_type=False)),
        sa.Column("descricao",      sa.Text, nullable=False),
        sa.Column("data_aditivo",   sa.Date, nullable=False),
        sa.Column("data_vigencia",  sa.Date, nullable=False),
        sa.Column("valor_anterior", sa.Numeric(15,2)),
        sa.Column("valor_novo",     sa.Numeric(15,2)),
        sa.Column("status",         sa.String(30), nullable=False, server_default="RASCUNHO"),
        sa.Column("aprovado_por",   sa.String(100)),
        sa.Column("data_aprovacao", sa.Date),
        sa.Column("arquivo_url",    sa.String(500)),
        sa.Column("criado_em",      sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("criado_por",     sa.String(100), nullable=False),
        sa.Column("atualizado_em",  sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("atualizado_por", sa.String(100)),
        sa.UniqueConstraint("contrato_id","numero_aditivo", name="uq_aditivo_contrato"),
    )
    op.create_table("contratos_historico",
        sa.Column("id",             sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("contrato_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operacao",       sa.String(1),   nullable=False),
        sa.Column("campo_alterado", sa.String(100)),
        sa.Column("valor_anterior", sa.Text),
        sa.Column("valor_novo",     sa.Text),
        sa.Column("alterado_por",   sa.String(100), nullable=False),
        sa.Column("alterado_em",    sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("motivo",         sa.Text),
    )

    # ================================================================
    # MÓDULO 03 — PRODUTOS (tabelas adicionais)
    # ================================================================
    op.create_table("produtos_pacotes",
        sa.Column("id",         sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("modalidade", postgresql.ENUM("ASP","BSP","BPO", name="modalidade_contrato", create_type=False), nullable=False),
        sa.Column("nome",       sa.String(150), nullable=False),
        sa.Column("descricao",  sa.Text),
        sa.Column("ativo",      sa.Boolean, nullable=False, server_default="true"),
        sa.Column("criado_em",  sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("criado_por", sa.String(100)),
        sa.UniqueConstraint("modalidade","nome", name="uq_pacote_nome_modalidade"),
    )
    op.create_table("produtos_pacotes_itens",
        sa.Column("id",             sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pacote_id",      sa.Integer, sa.ForeignKey("produtos_pacotes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("produto_id",     sa.Integer, sa.ForeignKey("produtos_servicos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade_min", sa.Numeric(10,3), nullable=False, server_default="1"),
        sa.Column("obrigatorio",    sa.Boolean, nullable=False, server_default="true"),
        sa.Column("observacoes",    sa.Text),
        sa.UniqueConstraint("pacote_id","produto_id", name="uq_pacote_produto"),
    )
    op.create_table("contratos_itens_movimentacoes",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contrato_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contrato_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_itens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo",             postgresql.ENUM("CANCELAMENTO","SUSPENSAO","REATIVACAO","SUBSTITUICAO", name="tipo_movimentacao", create_type=False), nullable=False),
        sa.Column("data_solicitacao", sa.Date, nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("data_efetivacao",  sa.Date, nullable=False),
        sa.Column("motivo",           sa.Text, nullable=False),
        sa.Column("novo_item_id",     postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_itens.id")),
        sa.Column("valor_anterior",   sa.Numeric(15,2)),
        sa.Column("valor_novo",       sa.Numeric(15,2)),
        sa.Column("aditivo_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_aditivos.id")),
        sa.Column("criado_por",       sa.String(100), nullable=False),
        sa.Column("criado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # ================================================================
    # MÓDULO 04 — REAJUSTES
    # ================================================================
    op.create_table("dissidios_historico",
        sa.Column("id",               sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("categoria",        sa.String(100), nullable=False, server_default="GERAL"),
        sa.Column("ano_base",         sa.Integer, nullable=False),
        sa.Column("data_vigencia",    sa.Date, nullable=False),
        sa.Column("valor_percentual", sa.Numeric(8,4), nullable=False),
        sa.Column("fonte",            sa.String(200)),
        sa.Column("criado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("criado_por",       sa.String(100)),
        sa.UniqueConstraint("categoria","ano_base", name="uq_dissidio_categoria_ano"),
    )
    op.create_table("indices_economicos_historico",
        sa.Column("id",               sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("indice",           postgresql.ENUM("INPC","IPCA","IGPM","FIXO","DISSIDIO", name="indice_economico", create_type=False), nullable=False),
        sa.Column("competencia",      sa.Date, nullable=False),
        sa.Column("valor_percentual", sa.Numeric(8,4), nullable=False),
        sa.Column("fonte",            sa.String(100)),
        sa.Column("criado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("criado_por",       sa.String(100)),
        sa.UniqueConstraint("indice","competencia", name="uq_indice_competencia"),
    )
    op.create_table("contratos_reajustes",
        sa.Column("id",                     postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contrato_id",            postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("numero_reajuste",        sa.Integer, nullable=False),
        sa.Column("indice",                 postgresql.ENUM("INPC","IPCA","IGPM","FIXO","DISSIDIO", name="indice_economico", create_type=False), nullable=False),
        sa.Column("percentual_fixo",        sa.Numeric(8,4)),
        sa.Column("data_base",              sa.Date, nullable=False),
        sa.Column("data_fim_periodo",       sa.Date, nullable=False),
        sa.Column("competencia_inicial",    sa.Date, nullable=False),
        sa.Column("competencia_final",      sa.Date, nullable=False),
        sa.Column("percentual_calculado",   sa.Numeric(8,4)),
        sa.Column("percentual_aplicado",    sa.Numeric(8,4)),
        sa.Column("valor_mensal_anterior",  sa.Numeric(15,2), nullable=False),
        sa.Column("valor_mensal_novo",      sa.Numeric(15,2)),
        sa.Column("variacao_mensal",        sa.Numeric(15,2)),
        sa.Column("status",                 postgresql.ENUM("CALCULADO","AGUARDANDO_APROVACAO","APROVADO","REPROVADO","COMUNICADO","EFETIVADO","CANCELADO", name="status_reajuste", create_type=False), nullable=False, server_default="CALCULADO"),
        sa.Column("data_calculo",           sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("calculado_por",          sa.String(100), nullable=False),
        sa.Column("data_aprovacao",         sa.TIMESTAMP(timezone=True)),
        sa.Column("aprovado_por",           sa.String(100)),
        sa.Column("motivo_reprovacao",      sa.Text),
        sa.Column("data_comunicacao",       sa.Date),
        sa.Column("data_efetivacao",        sa.Date, nullable=False),
        sa.Column("observacoes",            sa.Text),
        sa.Column("aditivo_id",             postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_aditivos.id")),
        sa.Column("criado_em",              sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("atualizado_em",          sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("contrato_id","numero_reajuste", name="uq_reajuste_numero"),
    )
    op.create_table("contratos_reajustes_itens",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("reajuste_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_reajustes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contrato_item_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_itens.id",    ondelete="RESTRICT"), nullable=False),
        sa.Column("valor_anterior",      sa.Numeric(15,2), nullable=False),
        sa.Column("percentual_aplicado", sa.Numeric(8,4),  nullable=False),
        sa.Column("valor_novo",          sa.Numeric(15,2), nullable=False),
        sa.Column("usa_dissidio",        sa.Boolean, nullable=False, server_default="false"),
        sa.Column("aprovado",            sa.Boolean),
        sa.Column("observacoes",         sa.Text),
    )

    # ================================================================
    # MÓDULO 05 — FATURAMENTO
    # ================================================================
    op.create_table("faixas_volumetria",
        sa.Column("id",              sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("produto_id",      sa.Integer, sa.ForeignKey("produtos_servicos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_vinculo",    postgresql.ENUM("CLT","AUTONOMO","ESTAGIARIO","SOCIO","DIRETOR","COOPERADO","OUTROS", name="tipo_vinculo_folha", create_type=False), nullable=False),
        sa.Column("faixa_de",        sa.Integer, nullable=False),
        sa.Column("faixa_ate",       sa.Integer),
        sa.Column("valor_unitario",  sa.Numeric(15,4), nullable=False),
        sa.Column("ativo",           sa.Boolean, nullable=False, server_default="true"),
        sa.Column("vigencia_inicio", sa.Date, nullable=False),
        sa.Column("vigencia_fim",    sa.Date),
        sa.Column("criado_em",       sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("criado_por",      sa.String(100)),
    )
    op.create_table("faturas",
        sa.Column("id",                 postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contrato_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("numero_fatura",      sa.String(30), unique=True),
        sa.Column("competencia",        sa.Date, nullable=False),
        sa.Column("dia_apuracao",       postgresql.ENUM("DIA_01","DIA_15","DIA_25", name="dia_faturamento", create_type=False), nullable=False),
        sa.Column("data_apuracao",      sa.Date, nullable=False),
        sa.Column("data_vencimento",    sa.Date, nullable=False),
        sa.Column("status",             postgresql.ENUM("RASCUNHO","APURADA","EMITIDA","ENVIADA","PAGA","CANCELADA","INADIMPLENTE", name="status_fatura", create_type=False), nullable=False, server_default="RASCUNHO"),
        sa.Column("valor_servicos",     sa.Numeric(15,2), nullable=False, server_default="0"),
        sa.Column("valor_volumetria",   sa.Numeric(15,2), nullable=False, server_default="0"),
        sa.Column("valor_pago",         sa.Numeric(15,2)),
        sa.Column("data_pagamento",     sa.Date),
        sa.Column("descricao_nf",       sa.Text),
        sa.Column("numero_nf",          sa.String(30)),
        sa.Column("serie_nf",           sa.String(10)),
        sa.Column("codigo_verificacao", sa.String(50)),
        sa.Column("data_emissao_nf",    sa.Date),
        sa.Column("observacoes",        sa.Text),
        sa.Column("criado_em",          sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("criado_por",         sa.String(100), nullable=False),
        sa.Column("atualizado_em",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("atualizado_por",     sa.String(100), nullable=False),
        sa.UniqueConstraint("contrato_id","competencia", name="uq_fatura_contrato_competencia"),
    )
    op.create_table("faturas_itens",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("fatura_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contrato_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_itens.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("produto_id",       sa.Integer, sa.ForeignKey("produtos_servicos.id"), nullable=False),
        sa.Column("descricao",        sa.String(300), nullable=False),
        sa.Column("quantidade",       sa.Numeric(10,3), nullable=False, server_default="1"),
        sa.Column("valor_unitario",   sa.Numeric(15,4), nullable=False),
        sa.Column("desconto_pct",     sa.Numeric(5,2),  nullable=False, server_default="0"),
        sa.Column("eh_volumetria",    sa.Boolean, nullable=False, server_default="false"),
        sa.Column("observacoes",      sa.Text),
    )
    op.create_table("faturas_volumetrias",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("fatura_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contrato_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_itens.id"), nullable=False),
        sa.Column("tipo_vinculo",     postgresql.ENUM("CLT","AUTONOMO","ESTAGIARIO","SOCIO","DIRETOR","COOPERADO","OUTROS", name="tipo_vinculo_folha", create_type=False), nullable=False),
        sa.Column("quantidade",       sa.Integer, nullable=False),
        sa.Column("valor_unitario",   sa.Numeric(15,4), nullable=False),
        sa.Column("fonte",            sa.String(100), server_default="INTEGRACAO_FOLHA"),
        sa.Column("competencia_folha",sa.Date),
        sa.Column("criado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table("faturas_documentos",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("fatura_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo",            postgresql.ENUM("RPS","NFS_E","BOLETO","BOLETIM_MEDICAO","DESCRITIVO", name="tipo_documento_fat", create_type=False), nullable=False),
        sa.Column("status",          postgresql.ENUM("PENDENTE","EMITIDO","ENVIADO","CANCELADO","ERRO", name="status_documento", create_type=False), nullable=False, server_default="PENDENTE"),
        sa.Column("numero",          sa.String(50)),
        sa.Column("url",             sa.String(500)),
        sa.Column("payload_envio",   postgresql.JSONB),
        sa.Column("payload_retorno", postgresql.JSONB),
        sa.Column("mensagem_erro",   sa.Text),
        sa.Column("emitido_em",      sa.TIMESTAMP(timezone=True)),
        sa.Column("emitido_por",     sa.String(100)),
        sa.Column("criado_em",       sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # ================================================================
    # MÓDULO 06 — VALIDAÇÃO
    # ================================================================
    op.create_table("codigos_alerta",
        sa.Column("codigo",               sa.String(20), primary_key=True),
        sa.Column("descricao",            sa.String(200), nullable=False),
        sa.Column("severidade",           postgresql.ENUM("CRITICO","ATENCAO","INFO", name="severidade_alerta", create_type=False), nullable=False),
        sa.Column("requer_justificativa", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ativo",                sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_table("faturas_validacoes",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("fatura_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status",         postgresql.ENUM("APROVADA","COM_ALERTAS","BLOQUEADA","JUSTIFICADA", name="status_validacao", create_type=False), nullable=False),
        sa.Column("total_criticos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_atencao",  sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_info",     sa.Integer, nullable=False, server_default="0"),
        sa.Column("executado_em",   sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("executado_por",  sa.String(100), nullable=False),
        sa.Column("analise_ia",     postgresql.JSONB),
        sa.Column("analise_ia_em",  sa.TIMESTAMP(timezone=True)),
    )
    op.create_table("faturas_alertas",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("validacao_id",     postgresql.UUID(as_uuid=True), sa.ForeignKey("faturas_validacoes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fatura_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("faturas.id",            ondelete="CASCADE"), nullable=False),
        sa.Column("codigo",           sa.String(20), sa.ForeignKey("codigos_alerta.codigo"), nullable=False),
        sa.Column("severidade",       postgresql.ENUM("CRITICO","ATENCAO","INFO", name="severidade_alerta", create_type=False), nullable=False),
        sa.Column("detalhe",          sa.Text, nullable=False),
        sa.Column("item_referencia",  postgresql.UUID(as_uuid=True)),
        sa.Column("valor_esperado",   sa.Numeric(15,2)),
        sa.Column("valor_encontrado", sa.Numeric(15,2)),
        sa.Column("status",           postgresql.ENUM("ABERTO","JUSTIFICADO","RESOLVIDO","IGNORADO", name="status_alerta", create_type=False), nullable=False, server_default="ABERTO"),
        sa.Column("justificativa",    sa.Text),
        sa.Column("justificado_por",  sa.String(100)),
        sa.Column("justificado_em",   sa.TIMESTAMP(timezone=True)),
        sa.Column("criado_em",        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_table("aviso_previo_cancelamento",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contrato_item_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("contratos_itens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_solicitacao",    sa.Date, nullable=False),
        sa.Column("prazo_vigencia_dias", sa.Integer, nullable=False, server_default="30"),
        sa.Column("data_fim_vigencia",   sa.Date, nullable=False),
        sa.Column("motivo",              sa.Text, nullable=False),
        sa.Column("status",              sa.String(20), nullable=False, server_default="ATIVO"),
        sa.Column("criado_por",          sa.String(100), nullable=False),
        sa.Column("criado_em",           sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # ================================================================
    # ÍNDICES PRINCIPAIS
    # ================================================================
    op.create_index("idx_clientes_status",       "clientes",            ["status"])
    op.create_index("idx_contratos_cliente_id",  "contratos",           ["cliente_id"])
    op.create_index("idx_contratos_status",      "contratos",           ["status"])
    op.create_index("idx_contratos_fase_atual",  "contratos",           ["fase_atual"])
    op.create_index("idx_contratos_dia_fat",     "contratos",           ["dia_faturamento"])
    op.create_index("idx_itens_contrato_id",     "contratos_itens",     ["contrato_id"])
    op.create_index("idx_itens_status_item",     "contratos_itens",     ["status_item"])
    op.create_index("idx_itens_data_fat",        "contratos_itens",     ["data_inicio_faturamento"])
    op.create_index("idx_faturas_contrato_id",   "faturas",             ["contrato_id"])
    op.create_index("idx_faturas_competencia",   "faturas",             ["competencia"])
    op.create_index("idx_faturas_status",        "faturas",             ["status"])
    op.create_index("idx_alertas_fatura",        "faturas_alertas",     ["fatura_id"])
    op.create_index("idx_alertas_status",        "faturas_alertas",     ["status"])
    op.create_index("idx_reajustes_contrato_id", "contratos_reajustes", ["contrato_id"])
    op.create_index("idx_reajustes_status",      "contratos_reajustes", ["status"])

    # Dados iniciais — códigos de alerta
    op.execute("""
        INSERT INTO codigos_alerta (codigo, descricao, severidade, requer_justificativa) VALUES
        ('VAL001','Valor faturado diferente do valor contratado','CRITICO',true),
        ('VAL002','Item faturado sem go-live confirmado','CRITICO',true),
        ('VAL003','Fatura gerada fora da data de apuração do contrato','ATENCAO',true),
        ('VAL004','Reajuste aplicado sem aprovação interna','CRITICO',true),
        ('VAL005','Contrato vencido ou encerrado — vigência expirada','CRITICO',true),
        ('VAL006','Volumetria faturada sem integração de folha recebida','ATENCAO',true),
        ('VAL007','Produto cancelado sendo faturado após data de cancelamento','CRITICO',true),
        ('VAL008','Produto em aviso prévio com prazo de vigência vencido','CRITICO',true),
        ('VAL009','Volumetria com variação acima de 20% em relação ao mês anterior','ATENCAO',true),
        ('VAL010','Fatura duplicada para a mesma competência','CRITICO',true),
        ('VAL011','Cliente bloqueado ou inativo com fatura em aberto','ATENCAO',false),
        ('VAL012','Desconto aplicado não consta no contrato','ATENCAO',true)
    """)

    # Sequências
    op.execute("CREATE SEQUENCE IF NOT EXISTS seq_contrato_numero START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS seq_fatura_numero  START 1")


def downgrade() -> None:
    # Remove na ordem inversa das dependências
    for tabela in [
        "aviso_previo_cancelamento","faturas_alertas","faturas_validacoes","codigos_alerta",
        "faturas_documentos","faturas_volumetrias","faturas_itens","faturas","faixas_volumetria",
        "contratos_reajustes_itens","contratos_reajustes",
        "indices_economicos_historico","dissidios_historico",
        "contratos_itens_movimentacoes","produtos_pacotes_itens","produtos_pacotes",
        "contratos_historico","contratos_aditivos","contratos_parcelas_implantacao",
        "contratos_itens","contratos","produtos_servicos",
        "clientes_historico","clientes_contatos","clientes_enderecos","clientes","segmentos",
    ]:
        op.drop_table(tabela)

    for seq in ["seq_contrato_numero","seq_fatura_numero"]:
        op.execute(f"DROP SEQUENCE IF EXISTS {seq}")

    for enum in [
        "tipo_pessoa","porte_empresa","status_cliente","tipo_endereco",
        "modalidade_contrato","status_contrato","fase_contrato","dia_faturamento",
        "status_parcela_impl","status_contrato_item","status_produto","tipo_movimentacao",
        "indice_economico","status_reajuste","tipo_aditivo",
        "status_fatura","tipo_documento_fat","status_documento","tipo_vinculo_folha",
        "severidade_alerta","status_validacao","status_alerta",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
