"""
Service do módulo de clientes.
Toda regra de negócio fica aqui — o router apenas valida entrada/saída.
"""
from uuid import UUID
from math import ceil
from typing import Optional

import httpx
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.cliente import (
    Cliente, ClienteEndereco, ClienteContato, ClienteHistorico,
    StatusCliente, TipoPessoa
)
from app.schemas.cliente import (
    ClienteCreate, ClienteUpdate, ClienteInativar,
    EnderecoCreate, EnderecoUpdate,
    ContatoCreate, ContatoUpdate,
    ClienteListOut, ClienteResumoOut, PaginacaoMeta
)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

async def _busca_cliente_ou_404(db: AsyncSession, cliente_id: UUID) -> Cliente:
    result = await db.execute(
        select(Cliente)
        .options(
            selectinload(Cliente.enderecos),
            selectinload(Cliente.contatos),
            selectinload(Cliente.segmento),
        )
        .where(Cliente.id == cliente_id)
    )
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return cliente


def _registra_historico(
    db: AsyncSession,
    cliente_id: UUID,
    operacao: str,
    campo: str,
    anterior,
    novo,
    usuario: str,
    ip: Optional[str] = None,
):
    hist = ClienteHistorico(
        cliente_id     = cliente_id,
        operacao       = operacao,
        campo_alterado = campo,
        valor_anterior = str(anterior) if anterior is not None else None,
        valor_novo     = str(novo) if novo is not None else None,
        alterado_por   = usuario,
        ip_origem      = ip,
    )
    db.add(hist)


async def _consulta_cep(cep: str) -> dict:
    """Consulta ViaCEP para autocompletar endereço."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"https://viacep.com.br/ws/{cep}/json/")
            if r.status_code == 200:
                data = r.json()
                if not data.get("erro"):
                    return data
    except Exception:
        pass
    return {}


# ------------------------------------------------------------------
# SEGMENTOS
# ------------------------------------------------------------------

async def listar_segmentos(db: AsyncSession):
    from app.models.cliente import Segmento
    result = await db.execute(
        select(Segmento).where(Segmento.ativo == True).order_by(Segmento.nome)
    )
    return result.scalars().all()


# ------------------------------------------------------------------
# CRIAR CLIENTE
# ------------------------------------------------------------------

async def criar_cliente(
    db:      AsyncSession,
    dados:   ClienteCreate,
    usuario: str,
    ip:      Optional[str] = None,
) -> Cliente:

    # Verifica duplicidade de CNPJ/CPF
    if dados.cnpj:
        existe = await db.execute(select(Cliente).where(Cliente.cnpj == dados.cnpj))
        if existe.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="CNPJ já cadastrado.")
    if dados.cpf:
        existe = await db.execute(select(Cliente).where(Cliente.cpf == dados.cpf))
        if existe.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="CPF já cadastrado.")

    cliente = Cliente(
        **dados.model_dump(exclude={"enderecos", "contatos"}),
        criado_por     = usuario,
        atualizado_por = usuario,
    )
    db.add(cliente)
    await db.flush()  # obtém o UUID antes de inserir dependentes

    # Endereços
    for end in dados.enderecos:
        db.add(ClienteEndereco(cliente_id=cliente.id, **end.model_dump()))

    # Contatos
    for con in dados.contatos:
        db.add(ClienteContato(cliente_id=cliente.id, **con.model_dump()))

    # Histórico
    _registra_historico(db, cliente.id, "I", "cadastro", None, "criado", usuario, ip)

    await db.flush()
    await db.refresh(cliente)
    return cliente


# ------------------------------------------------------------------
# LISTAR CLIENTES (paginado + filtros)
# ------------------------------------------------------------------

async def listar_clientes(
    db:         AsyncSession,
    pagina:     int = 1,
    por_pagina: int = 20,
    busca:      Optional[str] = None,
    status:     Optional[StatusCliente] = None,
    segmento_id:Optional[int] = None,
    tipo_pessoa:Optional[TipoPessoa] = None,
) -> ClienteListOut:

    # Usa a view vw_clientes_resumo para listagem eficiente
    query = text("""
        SELECT
            id, tipo_pessoa, nome_principal, nome_fantasia, documento,
            segmento, porte, status, cidade_uf,
            contato_financeiro, email_financeiro, criado_em
        FROM vw_clientes_resumo
        WHERE (:status IS NULL OR status = :status)
          AND (:segmento_id IS NULL OR segmento_id = :segmento_id)
          AND (:tipo_pessoa IS NULL OR tipo_pessoa = :tipo_pessoa)
          AND (:busca IS NULL OR (
              unaccent(lower(nome_principal)) ILIKE unaccent(lower('%' || :busca || '%'))
              OR unaccent(lower(nome_fantasia)) ILIKE unaccent(lower('%' || :busca || '%'))
              OR documento LIKE '%' || :busca || '%'
          ))
        ORDER BY nome_principal
        LIMIT :limit OFFSET :offset
    """)

    count_query = text("""
        SELECT COUNT(*) FROM vw_clientes_resumo
        WHERE (:status IS NULL OR status = :status)
          AND (:segmento_id IS NULL OR segmento_id = :segmento_id)
          AND (:tipo_pessoa IS NULL OR tipo_pessoa = :tipo_pessoa)
          AND (:busca IS NULL OR (
              unaccent(lower(nome_principal)) ILIKE unaccent(lower('%' || :busca || '%'))
              OR unaccent(lower(nome_fantasia)) ILIKE unaccent(lower('%' || :busca || '%'))
              OR documento LIKE '%' || :busca || '%'
          ))
    """)

    params = {
        "status":       status.value if status else None,
        "segmento_id":  segmento_id,
        "tipo_pessoa":  tipo_pessoa.value if tipo_pessoa else None,
        "busca":        busca,
        "limit":        por_pagina,
        "offset":       (pagina - 1) * por_pagina,
    }

    total_result = await db.execute(count_query, params)
    total = total_result.scalar()

    rows = await db.execute(query, params)
    dados = [ClienteResumoOut.model_validate(dict(r._mapping)) for r in rows]

    return ClienteListOut(
        dados=dados,
        meta=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=ceil(total / por_pagina) if total else 0,
        )
    )


# ------------------------------------------------------------------
# BUSCAR CLIENTE POR ID
# ------------------------------------------------------------------

async def buscar_cliente(db: AsyncSession, cliente_id: UUID) -> Cliente:
    return await _busca_cliente_ou_404(db, cliente_id)


# ------------------------------------------------------------------
# ATUALIZAR CLIENTE
# ------------------------------------------------------------------

async def atualizar_cliente(
    db:         AsyncSession,
    cliente_id: UUID,
    dados:      ClienteUpdate,
    usuario:    str,
    ip:         Optional[str] = None,
) -> Cliente:
    cliente = await _busca_cliente_ou_404(db, cliente_id)

    alteracoes = dados.model_dump(exclude_unset=True)
    for campo, novo_valor in alteracoes.items():
        anterior = getattr(cliente, campo)
        if anterior != novo_valor:
            _registra_historico(db, cliente.id, "U", campo, anterior, novo_valor, usuario, ip)
            setattr(cliente, campo, novo_valor)

    cliente.atualizado_por = usuario
    await db.flush()
    await db.refresh(cliente)
    return cliente


# ------------------------------------------------------------------
# INATIVAR CLIENTE
# ------------------------------------------------------------------

async def inativar_cliente(
    db:         AsyncSession,
    cliente_id: UUID,
    dados:      ClienteInativar,
    usuario:    str,
    ip:         Optional[str] = None,
) -> Cliente:
    cliente = await _busca_cliente_ou_404(db, cliente_id)

    if cliente.status == StatusCliente.INATIVO:
        raise HTTPException(status_code=400, detail="Cliente já está inativo.")

    # Verificação de contratos ativos será adicionada no módulo de contratos.
    # Por ora, apenas bloqueia se houver contratos (stub).
    _registra_historico(
        db, cliente.id, "U", "status",
        cliente.status.value, StatusCliente.INATIVO.value,
        usuario, ip
    )
    _registra_historico(
        db, cliente.id, "U", "motivo_inativacao",
        None, dados.motivo, usuario, ip
    )

    cliente.status            = StatusCliente.INATIVO
    cliente.motivo_inativacao = dados.motivo
    cliente.atualizado_por    = usuario

    await db.flush()
    await db.refresh(cliente)
    return cliente


# ------------------------------------------------------------------
# ENDEREÇOS
# ------------------------------------------------------------------

async def adicionar_endereco(
    db:         AsyncSession,
    cliente_id: UUID,
    dados:      EnderecoCreate,
    usuario:    str,
) -> ClienteEndereco:
    await _busca_cliente_ou_404(db, cliente_id)

    # Se for marcado como principal, desmarca os outros do mesmo tipo
    if dados.principal:
        await db.execute(
            text("""
                UPDATE clientes_enderecos
                SET principal = FALSE
                WHERE cliente_id = :cid AND tipo = :tipo AND principal = TRUE
            """),
            {"cid": str(cliente_id), "tipo": dados.tipo.value}
        )

    end = ClienteEndereco(cliente_id=cliente_id, **dados.model_dump())
    db.add(end)
    await db.flush()
    await db.refresh(end)
    return end


async def atualizar_endereco(
    db:          AsyncSession,
    cliente_id:  UUID,
    endereco_id: UUID,
    dados:       EnderecoUpdate,
    usuario:     str,
) -> ClienteEndereco:
    result = await db.execute(
        select(ClienteEndereco).where(
            ClienteEndereco.id == endereco_id,
            ClienteEndereco.cliente_id == cliente_id,
        )
    )
    end = result.scalar_one_or_none()
    if not end:
        raise HTTPException(status_code=404, detail="Endereço não encontrado.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(end, campo, valor)

    await db.flush()
    await db.refresh(end)
    return end


async def consultar_cep(cep: str) -> dict:
    """Proxy para ViaCEP — usado pelo frontend no autopreenchimento."""
    dados = await _consulta_cep(cep)
    if not dados:
        raise HTTPException(status_code=404, detail="CEP não encontrado.")
    return {
        "cep":        dados.get("cep", "").replace("-", ""),
        "logradouro": dados.get("logradouro", ""),
        "bairro":     dados.get("bairro", ""),
        "cidade":     dados.get("localidade", ""),
        "uf":         dados.get("uf", ""),
        "ibge":       dados.get("ibge", ""),
    }


# ------------------------------------------------------------------
# CONTATOS
# ------------------------------------------------------------------

async def adicionar_contato(
    db:         AsyncSession,
    cliente_id: UUID,
    dados:      ContatoCreate,
    usuario:    str,
) -> ClienteContato:
    await _busca_cliente_ou_404(db, cliente_id)

    if dados.principal:
        await db.execute(
            text("""
                UPDATE clientes_contatos
                SET principal = FALSE
                WHERE cliente_id = :cid AND principal = TRUE
            """),
            {"cid": str(cliente_id)}
        )

    contato = ClienteContato(cliente_id=cliente_id, **dados.model_dump())
    db.add(contato)
    await db.flush()
    await db.refresh(contato)
    return contato


async def atualizar_contato(
    db:          AsyncSession,
    cliente_id:  UUID,
    contato_id:  UUID,
    dados:       ContatoUpdate,
    usuario:     str,
) -> ClienteContato:
    result = await db.execute(
        select(ClienteContato).where(
            ClienteContato.id == contato_id,
            ClienteContato.cliente_id == cliente_id,
        )
    )
    contato = result.scalar_one_or_none()
    if not contato:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(contato, campo, valor)

    await db.flush()
    await db.refresh(contato)
    return contato


async def remover_contato(
    db:         AsyncSession,
    cliente_id: UUID,
    contato_id: UUID,
    usuario:    str,
) -> None:
    result = await db.execute(
        select(ClienteContato).where(
            ClienteContato.id == contato_id,
            ClienteContato.cliente_id == cliente_id,
        )
    )
    contato = result.scalar_one_or_none()
    if not contato:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    contato.ativo = False
    await db.flush()
