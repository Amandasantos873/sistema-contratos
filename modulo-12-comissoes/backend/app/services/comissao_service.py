"""
Módulo 12 — Comissões
Service + Router

Fluxo: Registrada → Aguardando Aprovação → Aprovada → Paga
Uma comissão por contrato indicado por parceiro.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from math import ceil

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status as http_status
from pydantic import BaseModel, Field

from app.database import get_db


# ================================================================
# SCHEMAS
# ================================================================

class ParceiroCreate(BaseModel):
    nome:              str = Field(..., min_length=3)
    tipo_pessoa:       str = Field(default="PF", pattern="^(PF|PJ)$")
    cpf_cnpj:          Optional[str] = None
    email:             Optional[str] = None
    telefone:          Optional[str] = None
    banco:             Optional[str] = None
    agencia:           Optional[str] = None
    conta:             Optional[str] = None
    pix_chave:         Optional[str] = None
    valor_fixo_padrao: Optional[Decimal] = None
    observacoes:       Optional[str] = None

class ParceiroOut(ParceiroCreate):
    id:        UUID
    ativo:     bool
    criado_em: datetime
    model_config = {"from_attributes": True}

class ComissaoCreate(BaseModel):
    parceiro_id:   UUID
    contrato_id:   UUID
    tipo_calculo:  str      = Field(default="FIXO", pattern="^(FIXO|PERCENTUAL)$")
    percentual:    Optional[Decimal] = None
    valor_base:    Optional[Decimal] = None
    valor_comissao:Decimal  = Field(..., gt=0)
    motivo:        str      = Field(..., min_length=5)
    observacoes:   Optional[str] = None

class ComissaoAprovar(BaseModel):
    decisao:           str  = Field(..., pattern="^(APROVADA|REPROVADA)$")
    motivo_reprovacao: Optional[str] = None

class ComissaoPagar(BaseModel):
    data_pagamento:  date
    forma_pagamento: str
    identificador_pag:Optional[str] = None

class ComissaoOut(BaseModel):
    id:               UUID
    numero_comissao:  str
    parceiro_nome:    str
    parceiro_documento:Optional[str]
    pix_chave:        Optional[str]
    contrato_numero:  str
    cliente_nome:     str
    modalidade:       str
    data_assinatura:  date
    tipo_calculo:     str
    percentual:       Optional[Decimal]
    valor_base:       Optional[Decimal]
    valor_comissao:   Decimal
    status:           str
    data_registro:    date
    motivo:           Optional[str]
    aprovado_por:     Optional[str]
    data_aprovacao:   Optional[date]
    data_pagamento:   Optional[date]
    forma_pagamento:  Optional[str]
    criado_em:        datetime
    model_config = {"from_attributes": True}


# ================================================================
# SERVICE
# ================================================================

async def listar_parceiros(db: AsyncSession) -> list:
    rows = await db.execute(text(
        "SELECT * FROM parceiros WHERE ativo=TRUE ORDER BY nome"
    ))
    return [dict(r._mapping) for r in rows]


async def criar_parceiro(db: AsyncSession, dados: ParceiroCreate, usuario: str) -> dict:
    result = await db.execute(text("""
        INSERT INTO parceiros
            (nome, tipo_pessoa, cpf_cnpj, email, telefone, banco, agencia,
             conta, pix_chave, valor_fixo_padrao, observacoes, criado_por)
        VALUES
            (:nome, :tp, :doc, :email, :tel, :banco, :ag,
             :conta, :pix, :vfp, :obs, :usuario)
        RETURNING *
    """), {
        "nome": dados.nome, "tp": dados.tipo_pessoa, "doc": dados.cpf_cnpj,
        "email": dados.email, "tel": dados.telefone, "banco": dados.banco,
        "ag": dados.agencia, "conta": dados.conta, "pix": dados.pix_chave,
        "vfp": dados.valor_fixo_padrao, "obs": dados.observacoes, "usuario": usuario,
    })
    await db.flush()
    return dict(result.fetchone()._mapping)


async def listar_comissoes(
    db:        AsyncSession,
    pagina:    int = 1,
    por_pagina:int = 20,
    status:    Optional[str] = None,
    parceiro_id:Optional[UUID] = None,
) -> dict:
    params = {
        "status":      status,
        "parceiro_id": str(parceiro_id) if parceiro_id else None,
        "limit":       por_pagina,
        "offset":      (pagina - 1) * por_pagina,
    }
    filtro = """
        (:status      IS NULL OR status       = :status::status_comissao)
        AND (:parceiro_id IS NULL OR parceiro_id = :parceiro_id::uuid)
    """
    rows  = await db.execute(text(f"SELECT * FROM vw_comissoes_resumo WHERE {filtro} LIMIT :limit OFFSET :offset"), params)
    total = (await db.execute(text(f"SELECT COUNT(*) FROM vw_comissoes_resumo WHERE {filtro}"), params)).scalar()
    dados = [dict(r._mapping) for r in rows]
    return {
        "dados": dados,
        "meta": {"total": total, "pagina": pagina, "por_pagina": por_pagina,
                 "paginas": ceil(total / por_pagina) if total else 0}
    }


async def criar_comissao(db: AsyncSession, dados: ComissaoCreate, usuario: str) -> dict:
    # Verifica se já existe comissão para este contrato
    existe = await db.execute(
        text("SELECT id FROM comissoes WHERE contrato_id = :cid"),
        {"cid": str(dados.contrato_id)}
    )
    if existe.scalar():
        raise HTTPException(status_code=409, detail="Já existe uma comissão registrada para este contrato.")

    result = await db.execute(text("""
        INSERT INTO comissoes
            (parceiro_id, contrato_id, tipo_calculo, percentual, valor_base,
             valor_comissao, motivo, status, observacoes, criado_por, atualizado_por)
        VALUES
            (:pid, :cid, :tc, :pct, :vb,
             :vc, :motivo, 'AGUARDANDO_APROVACAO', :obs, :usuario, :usuario)
        RETURNING *
    """), {
        "pid": str(dados.parceiro_id), "cid": str(dados.contrato_id),
        "tc": dados.tipo_calculo, "pct": dados.percentual, "vb": dados.valor_base,
        "vc": dados.valor_comissao, "motivo": dados.motivo,
        "obs": dados.observacoes, "usuario": usuario,
    })
    await db.flush()
    return dict(result.fetchone()._mapping)


async def aprovar_comissao(
    db:          AsyncSession,
    comissao_id: UUID,
    dados:       ComissaoAprovar,
    usuario:     str,
) -> dict:
    row = await db.execute(
        text("SELECT status FROM comissoes WHERE id = :id"),
        {"id": str(comissao_id)}
    )
    status_atual = row.scalar()
    if not status_atual:
        raise HTTPException(status_code=404, detail="Comissão não encontrada.")
    if status_atual != "AGUARDANDO_APROVACAO":
        raise HTTPException(status_code=400, detail=f"Comissão com status '{status_atual}' não pode ser aprovada.")

    novo_status = dados.decisao
    await db.execute(text("""
        UPDATE comissoes SET
            status             = :status::status_comissao,
            aprovado_por       = :usuario,
            data_aprovacao     = CURRENT_DATE,
            motivo_reprovacao  = :motivo_rep,
            atualizado_em      = NOW(),
            atualizado_por     = :usuario
        WHERE id = :id
    """), {
        "status": novo_status, "usuario": usuario,
        "motivo_rep": dados.motivo_reprovacao, "id": str(comissao_id)
    })
    await db.flush()
    return {"comissao_id": str(comissao_id), "status": novo_status}


async def pagar_comissao(
    db:          AsyncSession,
    comissao_id: UUID,
    dados:       ComissaoPagar,
    usuario:     str,
) -> dict:
    row = await db.execute(
        text("SELECT status, valor_comissao, parceiro_id FROM comissoes WHERE id = :id"),
        {"id": str(comissao_id)}
    )
    com = row.fetchone()
    if not com:
        raise HTTPException(status_code=404, detail="Comissão não encontrada.")
    if com.status != "APROVADA":
        raise HTTPException(status_code=400, detail="Somente comissões APROVADAS podem ser pagas.")

    # Gera despesa no módulo 08 automaticamente
    desp_result = await db.execute(text("""
        INSERT INTO despesas
            (categoria_id, centro_custo_id, descricao, competencia,
             data_vencimento, valor, status, criado_por, atualizado_por)
        SELECT
            cd.id,
            cc.id,
            'Comissão por indicação — ' || p.nome,
            DATE_TRUNC('month', CURRENT_DATE),
            :data_pag,
            c.valor_comissao,
            'APROVADA',
            :usuario,
            :usuario
        FROM comissoes c
        JOIN parceiros p ON p.id = c.parceiro_id
        CROSS JOIN categorias_despesa cd
        CROSS JOIN centros_custo cc
        WHERE c.id = :cid
          AND cd.tipo = 'COMISSAO' AND cd.ativo = TRUE
          AND cc.codigo = 'COMERC'
        LIMIT 1
        RETURNING id
    """), {"data_pag": dados.data_pagamento, "usuario": usuario, "cid": str(comissao_id)})

    despesa_id = desp_result.scalar()

    await db.execute(text("""
        UPDATE comissoes SET
            status            = 'PAGA',
            data_pagamento    = :data_pag,
            forma_pagamento   = :forma,
            identificador_pag = :ident,
            despesa_id        = :despesa_id,
            atualizado_em     = NOW(),
            atualizado_por    = :usuario
        WHERE id = :id
    """), {
        "data_pag": dados.data_pagamento, "forma": dados.forma_pagamento,
        "ident": dados.identificador_pag, "despesa_id": str(despesa_id) if despesa_id else None,
        "usuario": usuario, "id": str(comissao_id)
    })
    await db.flush()
    return {"comissao_id": str(comissao_id), "status": "PAGA", "despesa_id": str(despesa_id) if despesa_id else None}


async def resumo_comissoes(db: AsyncSession) -> dict:
    row = await db.execute(text("""
        SELECT
            COUNT(*)                                                        AS total,
            COUNT(CASE WHEN status='AGUARDANDO_APROVACAO' THEN 1 END)      AS aguardando,
            COUNT(CASE WHEN status='APROVADA'             THEN 1 END)      AS aprovadas,
            COUNT(CASE WHEN status='PAGA'                 THEN 1 END)      AS pagas,
            COALESCE(SUM(CASE WHEN status='APROVADA' THEN valor_comissao ELSE 0 END), 0) AS valor_aprovado,
            COALESCE(SUM(CASE WHEN status='PAGA'     THEN valor_comissao ELSE 0 END), 0) AS valor_pago
        FROM comissoes WHERE status != 'CANCELADA'
    """))
    return dict(row.fetchone()._mapping)


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(tags=["Comissões"])


def _u(r: Request) -> str:
    return r.headers.get("X-Usuario", "sistema")


@router.get("/parceiros", summary="Lista parceiros indicadores")
async def listar_p(db: AsyncSession = Depends(get_db)):
    return await listar_parceiros(db)


@router.post("/parceiros", status_code=http_status.HTTP_201_CREATED, summary="Cadastra parceiro")
async def criar_p(dados: ParceiroCreate, request: Request, db: AsyncSession = Depends(get_db)):
    return await criar_parceiro(db, dados, _u(request))


@router.get("/comissoes/resumo", summary="Resumo geral de comissões")
async def resumo(db: AsyncSession = Depends(get_db)):
    return await resumo_comissoes(db)


@router.get("/comissoes", summary="Lista comissões")
async def listar(
    pagina:      int           = Query(1, ge=1),
    por_pagina:  int           = Query(20, ge=1, le=100),
    status:      Optional[str] = Query(None),
    parceiro_id: Optional[UUID]= Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await listar_comissoes(db, pagina, por_pagina, status, parceiro_id)


@router.post("/comissoes", status_code=http_status.HTTP_201_CREATED, summary="Registra comissão por indicação")
async def criar(dados: ComissaoCreate, request: Request, db: AsyncSession = Depends(get_db)):
    return await criar_comissao(db, dados, _u(request))


@router.patch("/comissoes/{comissao_id}/aprovar", summary="Aprova ou reprova comissão")
async def aprovar(comissao_id: UUID, dados: ComissaoAprovar, request: Request, db: AsyncSession = Depends(get_db)):
    return await aprovar_comissao(db, comissao_id, dados, _u(request))


@router.patch("/comissoes/{comissao_id}/pagar", summary="Registra pagamento e gera despesa no módulo 08")
async def pagar(comissao_id: UUID, dados: ComissaoPagar, request: Request, db: AsyncSession = Depends(get_db)):
    return await pagar_comissao(db, comissao_id, dados, _u(request))
