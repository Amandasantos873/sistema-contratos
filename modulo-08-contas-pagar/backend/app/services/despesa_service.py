"""
Módulo 08 — Contas a Pagar
Models, Schemas, Service e Router
"""
# ================================================================
# MODELS
# ================================================================
import uuid, enum
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, Text, Date, Integer, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from pydantic import BaseModel, Field
from math import ceil
from uuid import UUID as PUUID
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status as http_status


class StatusDespesa(str, enum.Enum):
    LANCADA               = "LANCADA"
    AGUARDANDO_APROVACAO  = "AGUARDANDO_APROVACAO"
    APROVADA              = "APROVADA"
    PAGA                  = "PAGA"
    CONCILIADA            = "CONCILIADA"
    CANCELADA             = "CANCELADA"
    REPROVADA             = "REPROVADA"

class TipoDespesa(str, enum.Enum):
    FORNECEDOR    = "FORNECEDOR"
    FOLHA         = "FOLHA"
    BENEFICIO     = "BENEFICIO"
    IMPOSTO       = "IMPOSTO"
    ADMINISTRATIVA= "ADMINISTRATIVA"
    COMISSAO      = "COMISSAO"
    OUTROS        = "OUTROS"

class FormaPagamentoCP(str, enum.Enum):
    TED              = "TED"
    PIX              = "PIX"
    BOLETO           = "BOLETO"
    CHEQUE           = "CHEQUE"
    DEBITO_AUTOMATICO= "DEBITO_AUTOMATICO"
    OUTROS           = "OUTROS"

class StatusAprovacaoCP(str, enum.Enum):
    PENDENTE  = "PENDENTE"
    APROVADO  = "APROVADO"
    REPROVADO = "REPROVADO"


class CentroCusto(Base):
    __tablename__ = "centros_custo"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    codigo      = Column(String(20),  nullable=False, unique=True)
    nome        = Column(String(150), nullable=False)
    descricao   = Column(Text)
    responsavel = Column(String(150))
    ativo       = Column(Boolean, nullable=False, default=True)
    criado_em   = Column(DateTime(timezone=True), server_default=func.now())
    criado_por  = Column(String(100))


class CategoriaDespesa(Base):
    __tablename__ = "categorias_despesa"
    id                   = Column(Integer, primary_key=True, autoincrement=True)
    tipo                 = Column(SAEnum(TipoDespesa, name="tipo_despesa"), nullable=False)
    subtipo              = Column(String(30))
    nome                 = Column(String(150), nullable=False)
    descricao            = Column(Text)
    requer_aprovacao     = Column(Boolean, nullable=False, default=True)
    limite_sem_aprovacao = Column(Numeric(15,2))
    ativo                = Column(Boolean, nullable=False, default=True)
    criado_em            = Column(DateTime(timezone=True), server_default=func.now())


class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razao_social  = Column(String(200), nullable=False)
    nome_fantasia = Column(String(200))
    cnpj_cpf      = Column(String(14),  unique=True)
    email         = Column(String(254))
    telefone      = Column(String(20))
    banco         = Column(String(100))
    agencia       = Column(String(20))
    conta         = Column(String(30))
    pix_chave     = Column(String(150))
    observacoes   = Column(Text)
    ativo         = Column(Boolean, nullable=False, default=True)
    criado_em     = Column(DateTime(timezone=True), server_default=func.now())
    criado_por    = Column(String(100))


class Despesa(Base):
    __tablename__ = "despesas"
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_despesa      = Column(String(30), unique=True)
    categoria_id        = Column(Integer,    ForeignKey("categorias_despesa.id"), nullable=False)
    centro_custo_id     = Column(Integer,    ForeignKey("centros_custo.id"),      nullable=False)
    fornecedor_id       = Column(UUID(as_uuid=True), ForeignKey("fornecedores.id"))
    descricao           = Column(String(300), nullable=False)
    competencia         = Column(Date, nullable=False)
    data_lancamento     = Column(Date, nullable=False)
    data_vencimento     = Column(Date, nullable=False)
    valor               = Column(Numeric(15,2), nullable=False)
    status              = Column(SAEnum(StatusDespesa, name="status_despesa"), nullable=False, default=StatusDespesa.LANCADA)
    aprovador1_id       = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    aprovador1_status   = Column(SAEnum(StatusAprovacaoCP, name="status_aprovacao_cp"))
    aprovador1_em       = Column(DateTime(timezone=True))
    aprovador1_obs      = Column(Text)
    aprovador2_id       = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    aprovador2_status   = Column(SAEnum(StatusAprovacaoCP, name="status_aprovacao_cp"))
    aprovador2_em       = Column(DateTime(timezone=True))
    aprovador2_obs      = Column(Text)
    data_pagamento      = Column(Date)
    valor_pago          = Column(Numeric(15,2))
    forma_pagamento     = Column(SAEnum(FormaPagamentoCP, name="forma_pagamento_cp"))
    banco_pagamento     = Column(String(100))
    identificador_pag   = Column(String(100))
    conciliado          = Column(Boolean, nullable=False, default=False)
    conciliado_em       = Column(DateTime(timezone=True))
    conciliado_por      = Column(String(100))
    numero_documento    = Column(String(50))
    observacoes         = Column(Text)
    criado_em           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por          = Column(String(100), nullable=False)
    atualizado_em       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_por      = Column(String(100), nullable=False)


# ================================================================
# SCHEMAS
# ================================================================

class CentroCustoOut(BaseModel):
    id:         int
    codigo:     str
    nome:       str
    responsavel:Optional[str]
    model_config = {"from_attributes": True}

class CategoriaOut(BaseModel):
    id:                   int
    tipo:                 TipoDespesa
    subtipo:              Optional[str]
    nome:                 str
    requer_aprovacao:     bool
    limite_sem_aprovacao: Optional[Decimal]
    model_config = {"from_attributes": True}

class FornecedorCreate(BaseModel):
    razao_social:  str = Field(..., min_length=3)
    nome_fantasia: Optional[str] = None
    cnpj_cpf:      Optional[str] = None
    email:         Optional[str] = None
    telefone:      Optional[str] = None
    banco:         Optional[str] = None
    agencia:       Optional[str] = None
    conta:         Optional[str] = None
    pix_chave:     Optional[str] = None
    observacoes:   Optional[str] = None

class FornecedorOut(FornecedorCreate):
    id:        PUUID
    ativo:     bool
    criado_em: datetime
    model_config = {"from_attributes": True}

class DespesaCreate(BaseModel):
    categoria_id:    int
    centro_custo_id: int
    fornecedor_id:   Optional[PUUID] = None
    descricao:       str = Field(..., min_length=5, max_length=300)
    competencia:     date
    data_vencimento: date
    valor:           Decimal = Field(..., gt=0)
    numero_documento:Optional[str] = None
    observacoes:     Optional[str] = None

class DespesaAprovar(BaseModel):
    aprovador: int = Field(..., ge=1, le=2, description="1 = primeiro aprovador, 2 = segundo aprovador")
    decisao:   StatusAprovacaoCP
    observacao:Optional[str] = None

class DespesaPagar(BaseModel):
    data_pagamento:   date
    valor_pago:       Decimal = Field(..., gt=0)
    forma_pagamento:  FormaPagamentoCP
    banco_pagamento:  Optional[str] = None
    identificador_pag:Optional[str] = None

class DespesaOut(BaseModel):
    id:               PUUID
    numero_despesa:   str
    descricao:        str
    competencia:      date
    data_vencimento:  date
    valor:            Decimal
    valor_pago:       Optional[Decimal]
    status:           StatusDespesa
    conciliado:       bool
    categoria_tipo:   str
    categoria_nome:   str
    centro_custo_codigo: str
    centro_custo_nome:   str
    fornecedor_nome:  Optional[str]
    dias_atraso:      int
    criado_por:       str
    criado_em:        datetime
    model_config = {"from_attributes": True}


# ================================================================
# SERVICE
# ================================================================

async def listar_despesas(
    db:              AsyncSession,
    pagina:          int = 1,
    por_pagina:      int = 20,
    status:          Optional[str]  = None,
    tipo:            Optional[str]  = None,
    centro_custo_id: Optional[int]  = None,
    competencia:     Optional[date] = None,
    em_atraso:       bool = False,
) -> dict:
    params = {
        "status":          status,
        "tipo":            tipo,
        "centro_custo_id": centro_custo_id,
        "competencia":     competencia,
        "em_atraso":       em_atraso,
        "limit":           por_pagina,
        "offset":          (pagina-1)*por_pagina,
    }
    filtro = """
        (:status IS NULL OR status = :status::status_despesa)
        AND (:tipo IS NULL OR categoria_tipo = :tipo)
        AND (:centro_custo_id IS NULL OR centro_custo_id = :centro_custo_id)
        AND (:competencia IS NULL OR competencia = :competencia)
        AND (:em_atraso = FALSE OR dias_atraso > 0)
        AND status != 'CANCELADA'
    """
    rows  = await db.execute(text(f"SELECT * FROM vw_despesas_resumo WHERE {filtro} ORDER BY data_vencimento, descricao LIMIT :limit OFFSET :offset"), params)
    total = (await db.execute(text(f"SELECT COUNT(*) FROM vw_despesas_resumo WHERE {filtro}"), params)).scalar()
    dados = [DespesaOut.model_validate(dict(r._mapping)) for r in rows]
    return {"dados": dados, "meta": {"total": total, "pagina": pagina, "por_pagina": por_pagina, "paginas": ceil(total/por_pagina) if total else 0}}


async def criar_despesa(db: AsyncSession, dados: DespesaCreate, usuario: str) -> Despesa:
    cat = await db.get(CategoriaDespesa, dados.categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    # Define status inicial: se não requer aprovação ou valor abaixo do limite, vai direto para APROVADA
    status_inicial = StatusDespesa.LANCADA
    if cat.requer_aprovacao:
        if cat.limite_sem_aprovacao and dados.valor <= cat.limite_sem_aprovacao:
            status_inicial = StatusDespesa.APROVADA
        else:
            status_inicial = StatusDespesa.AGUARDANDO_APROVACAO

    d = Despesa(
        **dados.model_dump(),
        data_lancamento = date.today(),
        status          = status_inicial,
        criado_por      = usuario,
        atualizado_por  = usuario,
    )
    db.add(d)
    await db.flush()
    await db.refresh(d)
    return d


async def aprovar_despesa(db: AsyncSession, despesa_id: PUUID, dados: DespesaAprovar, usuario_id: PUUID, usuario: str) -> Despesa:
    d = await db.get(Despesa, despesa_id)
    if not d:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    if d.status not in (StatusDespesa.AGUARDANDO_APROVACAO, StatusDespesa.LANCADA):
        raise HTTPException(status_code=400, detail=f"Despesa com status '{d.status.value}' não pode ser aprovada.")

    agora = datetime.now()
    if dados.aprovador == 1:
        if d.aprovador1_id and d.aprovador1_id != usuario_id:
            raise HTTPException(status_code=403, detail="Outro aprovador já registrou o primeiro voto.")
        d.aprovador1_id     = usuario_id
        d.aprovador1_status = dados.decisao
        d.aprovador1_em     = agora
        d.aprovador1_obs    = dados.observacao
    else:
        if d.aprovador2_id and d.aprovador2_id != usuario_id:
            raise HTTPException(status_code=403, detail="Outro aprovador já registrou o segundo voto.")
        d.aprovador2_id     = usuario_id
        d.aprovador2_status = dados.decisao
        d.aprovador2_em     = agora
        d.aprovador2_obs    = dados.observacao

    # Avança status (o trigger faz no banco, aqui replicamos na sessão)
    if StatusAprovacaoCP.REPROVADO in (d.aprovador1_status, d.aprovador2_status):
        d.status = StatusDespesa.REPROVADA
    elif d.aprovador1_status == StatusAprovacaoCP.APROVADO and d.aprovador2_status == StatusAprovacaoCP.APROVADO:
        d.status = StatusDespesa.APROVADA

    d.atualizado_por = usuario
    await db.flush()
    return d


async def pagar_despesa(db: AsyncSession, despesa_id: PUUID, dados: DespesaPagar, usuario: str) -> Despesa:
    d = await db.get(Despesa, despesa_id)
    if not d:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    if d.status != StatusDespesa.APROVADA:
        raise HTTPException(status_code=400, detail="Somente despesas APROVADAS podem ser pagas.")

    d.data_pagamento    = dados.data_pagamento
    d.valor_pago        = dados.valor_pago
    d.forma_pagamento   = dados.forma_pagamento
    d.banco_pagamento   = dados.banco_pagamento
    d.identificador_pag = dados.identificador_pag
    d.status            = StatusDespesa.PAGA
    d.atualizado_por    = usuario
    await db.flush()
    return d


async def conciliar_despesa(db: AsyncSession, despesa_id: PUUID, usuario: str) -> Despesa:
    d = await db.get(Despesa, despesa_id)
    if not d:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    if d.status != StatusDespesa.PAGA:
        raise HTTPException(status_code=400, detail="Somente despesas PAGAS podem ser conciliadas.")
    d.conciliado    = True
    d.conciliado_em = datetime.now()
    d.conciliado_por= usuario
    d.status        = StatusDespesa.CONCILIADA
    d.atualizado_por= usuario
    await db.flush()
    return d


async def cancelar_despesa(db: AsyncSession, despesa_id: PUUID, usuario: str) -> Despesa:
    d = await db.get(Despesa, despesa_id)
    if not d:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    if d.status in (StatusDespesa.PAGA, StatusDespesa.CONCILIADA):
        raise HTTPException(status_code=400, detail="Despesas pagas ou conciliadas não podem ser canceladas.")
    d.status       = StatusDespesa.CANCELADA
    d.atualizado_por = usuario
    await db.flush()
    return d


async def resumo_por_categoria(db: AsyncSession, competencia: Optional[date] = None) -> list:
    params = {"competencia": competencia}
    filtro = "(:competencia IS NULL OR mes = DATE_TRUNC('month', :competencia::date))"
    rows = await db.execute(text(f"""
        SELECT mes, categoria_tipo, categoria_nome, centro_custo_codigo, centro_custo_nome,
               quantidade, total_lancado, total_pago
        FROM vw_despesas_por_categoria
        WHERE {filtro}
        ORDER BY mes DESC, total_lancado DESC
    """), params)
    return [dict(r._mapping) for r in rows]


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(tags=["Contas a Pagar"])


def _usuario(request: Request) -> str:
    return request.headers.get("X-Usuario", "sistema")

def _usuario_id(request: Request) -> PUUID:
    uid = request.headers.get("X-Usuario-Id")
    if not uid:
        raise HTTPException(status_code=401, detail="Header X-Usuario-Id obrigatório.")
    return PUUID(uid)


@router.get("/centros-custo", response_model=list[CentroCustoOut], summary="Lista centros de custo")
async def listar_centros(db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        r = await db.execute(select(CentroCusto).where(CentroCusto.ativo == True).order_by(CentroCusto.nome))
        return r.scalars().all()

@router.get("/categorias-despesa", response_model=list[CategoriaOut], summary="Lista categorias de despesa")
async def listar_categorias(db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        r = await db.execute(select(CategoriaDespesa).where(CategoriaDespesa.ativo == True).order_by(CategoriaDespesa.tipo, CategoriaDespesa.nome))
        return r.scalars().all()

@router.get("/fornecedores", response_model=list[FornecedorOut], summary="Lista fornecedores")
async def listar_fornecedores(db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        r = await db.execute(select(Fornecedor).where(Fornecedor.ativo == True).order_by(Fornecedor.razao_social))
        return r.scalars().all()

@router.post("/fornecedores", response_model=FornecedorOut, status_code=http_status.HTTP_201_CREATED, summary="Cadastra fornecedor")
async def criar_fornecedor(dados: FornecedorCreate, request: Request, db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        f = Fornecedor(**dados.model_dump(), criado_por=_usuario(request))
        db.add(f); await db.flush(); await db.refresh(f); return f

@router.get("/contas-pagar", summary="Lista despesas com filtros")
async def listar(
    pagina:          int           = Query(1, ge=1),
    por_pagina:      int           = Query(20, ge=1, le=100),
    status:          Optional[str] = Query(None),
    tipo:            Optional[str] = Query(None),
    centro_custo_id: Optional[int] = Query(None),
    competencia:     Optional[date]= Query(None),
    em_atraso:       bool          = Query(False),
    db: AsyncSession = Depends(lambda: None),
):
    from app.database import get_db
    async for db in get_db():
        return await listar_despesas(db, pagina, por_pagina, status, tipo, centro_custo_id, competencia, em_atraso)

@router.post("/contas-pagar", status_code=http_status.HTTP_201_CREATED, summary="Lança nova despesa")
async def criar(dados: DespesaCreate, request: Request, db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        return await criar_despesa(db, dados, _usuario(request))

@router.patch("/contas-pagar/{despesa_id}/aprovar", summary="Registra voto de aprovação ou reprovação")
async def aprovar(despesa_id: PUUID, dados: DespesaAprovar, request: Request, db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        return await aprovar_despesa(db, despesa_id, dados, _usuario_id(request), _usuario(request))

@router.patch("/contas-pagar/{despesa_id}/pagar", summary="Registra pagamento da despesa")
async def pagar(despesa_id: PUUID, dados: DespesaPagar, request: Request, db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        return await pagar_despesa(db, despesa_id, dados, _usuario(request))

@router.patch("/contas-pagar/{despesa_id}/conciliar", summary="Marca despesa como conciliada")
async def conciliar(despesa_id: PUUID, request: Request, db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        return await conciliar_despesa(db, despesa_id, _usuario(request))

@router.delete("/contas-pagar/{despesa_id}", status_code=http_status.HTTP_204_NO_CONTENT, summary="Cancela despesa")
async def cancelar(despesa_id: PUUID, request: Request, db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        await cancelar_despesa(db, despesa_id, _usuario(request))

@router.get("/contas-pagar/resumo/categoria", summary="Resumo de despesas por categoria e centro de custo")
async def resumo(competencia: Optional[date] = Query(None), db: AsyncSession = Depends(lambda: None)):
    from app.database import get_db
    async for db in get_db():
        return await resumo_por_categoria(db, competencia)
