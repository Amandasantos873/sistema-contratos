"""
Service do módulo de faturamento.

Fluxo principal:
  1. Apuração em lote → cria faturas RASCUNHO para todos os contratos do dia
  2. Recebimento de volumetrias via integração de folha
  3. Cálculo de valores por faixa de volumetria
  4. Geração de documentos: descritivo, boletim de medição, RPS/NFS-e (K2), boleto
  5. Registro de pagamento
"""
from math import ceil
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.fatura import (
    Fatura, FaturaItem, FaturaVolumetria, FaturaDocumento,
    FaixaVolumetria, StatusFatura, TipoDocumentoFat, StatusDocumento,
    TipoVinculoFolha
)
from app.schemas.fatura import (
    FaturaApurarRequest, FaturaRegistrarPagamento, FaturaRegistrarNF,
    VolumetriaInput, FaturaOut, FaturaResumoOut, FaturaListOut,
    ApuracaoResultado,
)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _arredonda(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_fatura_ou_404(db: AsyncSession, fatura_id: UUID) -> Fatura:
    result = await db.execute(
        select(Fatura)
        .options(
            selectinload(Fatura.itens),
            selectinload(Fatura.volumetrias),
            selectinload(Fatura.documentos),
        )
        .where(Fatura.id == fatura_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Fatura não encontrada.")
    return f


async def _busca_faixa_preco(
    db:          AsyncSession,
    produto_id:  int,
    tipo_vinculo:str,
    quantidade:  int,
    competencia: date,
) -> Decimal:
    """Retorna o valor unitário da faixa de volumetria para a quantidade informada."""
    row = await db.execute(
        text("""
            SELECT valor_unitario FROM faixas_volumetria
            WHERE produto_id     = :pid
              AND tipo_vinculo    = :tv
              AND faixa_de       <= :qtd
              AND (faixa_ate IS NULL OR faixa_ate >= :qtd)
              AND ativo          = TRUE
              AND vigencia_inicio <= :comp
              AND (vigencia_fim IS NULL OR vigencia_fim >= :comp)
            ORDER BY faixa_de DESC
            LIMIT 1
        """),
        {"pid": produto_id, "tv": tipo_vinculo, "qtd": quantidade, "comp": competencia}
    )
    valor = row.scalar()
    if valor is None:
        raise HTTPException(
            status_code=422,
            detail=f"Faixa de preço não encontrada para {tipo_vinculo} com quantidade {quantidade}. "
                   f"Verifique o cadastro de faixas de volumetria."
        )
    return Decimal(str(valor))


def _gera_descricao_nf(modalidade: str, competencia: date, valor_total: Decimal) -> str:
    """Gera o texto padrão da NFS-e conforme formato do K2."""
    valor_fmt = f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (
        f"Prestação de Serviços Conforme Contrato {modalidade} "
        f"competência {competencia.strftime('%m/%Y')} "
        f"— Valor Total {valor_fmt}"
    )


# ==================================================================
# FAIXAS DE VOLUMETRIA
# ==================================================================

async def listar_faixas(db: AsyncSession, produto_id: Optional[int] = None) -> list:
    q = select(FaixaVolumetria).where(FaixaVolumetria.ativo == True)
    if produto_id:
        q = q.where(FaixaVolumetria.produto_id == produto_id)
    result = await db.execute(q.order_by(FaixaVolumetria.produto_id, FaixaVolumetria.tipo_vinculo, FaixaVolumetria.faixa_de))
    return result.scalars().all()


async def criar_faixa(db: AsyncSession, dados, usuario: str) -> FaixaVolumetria:
    faixa = FaixaVolumetria(**dados.model_dump(), criado_por=usuario)
    db.add(faixa)
    await db.flush()
    await db.refresh(faixa)
    return faixa


# ==================================================================
# APURAÇÃO EM LOTE
# ==================================================================

async def apurar_faturas(
    db:      AsyncSession,
    dados:   FaturaApurarRequest,
    usuario: str,
) -> ApuracaoResultado:
    """
    Gera faturas RASCUNHO para todos os contratos elegíveis no dia de apuração.
    Contratos que já têm fatura para a competência são ignorados.
    """
    # Busca itens elegíveis
    itens_rows = await db.execute(
        text("""
            SELECT item_id, contrato_id, contrato_numero, cliente_id, cliente_nome,
                   modalidade, produto_id, produto_nome, produto_unidade,
                   quantidade, valor_unitario, desconto_pct, valor_total,
                   data_inicio_faturamento
            FROM vw_itens_a_faturar
            WHERE dia_faturamento = :dia
              AND data_inicio_faturamento <= :competencia
            ORDER BY contrato_id, produto_nome
        """),
        {"dia": dados.dia_apuracao, "competencia": dados.competencia}
    )
    itens_elegiveis = [dict(r._mapping) for r in itens_rows]

    if not itens_elegiveis:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum item elegível para apuração em {dados.dia_apuracao} na competência {dados.competencia.strftime('%m/%Y')}."
        )

    # Agrupa por contrato
    por_contrato: dict[str, dict] = {}
    for item in itens_elegiveis:
        cid = str(item["contrato_id"])
        if cid not in por_contrato:
            por_contrato[cid] = {
                "contrato_id":   item["contrato_id"],
                "contrato_numero": item["contrato_numero"],
                "cliente_nome":  item["cliente_nome"],
                "modalidade":    item["modalidade"],
                "itens":         [],
            }
        por_contrato[cid]["itens"].append(item)

    faturas_criadas    = []
    faturas_existentes = 0

    for cid, grupo in por_contrato.items():
        # Verifica se já existe fatura para esta competência
        existe = await db.execute(
            select(Fatura).where(
                Fatura.contrato_id == grupo["contrato_id"],
                Fatura.competencia == dados.competencia,
            )
        )
        if existe.scalar_one_or_none():
            faturas_existentes += 1
            continue

        # Cria fatura
        fatura = Fatura(
            contrato_id     = grupo["contrato_id"],
            competencia     = dados.competencia,
            dia_apuracao    = dados.dia_apuracao,
            data_apuracao   = dados.data_apuracao,
            data_vencimento = dados.data_vencimento,
            status          = StatusFatura.RASCUNHO,
            criado_por      = usuario,
            atualizado_por  = usuario,
        )
        db.add(fatura)
        await db.flush()

        # Cria itens (apenas serviços padrão — volumetria vem depois via integração)
        for item in grupo["itens"]:
            db.add(FaturaItem(
                fatura_id        = fatura.id,
                contrato_item_id = item["item_id"],
                produto_id       = item["produto_id"],
                descricao        = item["produto_nome"],
                quantidade       = item["quantidade"],
                valor_unitario   = item["valor_unitario"],
                desconto_pct     = item["desconto_pct"],
                eh_volumetria    = False,
            ))

        await db.flush()
        await db.refresh(fatura)

        # Gera descrição padrão da NF
        fatura.descricao_nf  = _gera_descricao_nf(
            grupo["modalidade"], dados.competencia, fatura.valor_total
        )
        fatura.status = StatusFatura.APURADA
        faturas_criadas.append(fatura)

    await db.flush()

    return ApuracaoResultado(
        competencia        = dados.competencia,
        dia_apuracao       = dados.dia_apuracao,
        faturas_criadas    = len(faturas_criadas),
        faturas_existentes = faturas_existentes,
        valor_total        = _arredonda(sum(f.valor_total for f in faturas_criadas)),
        faturas            = [],
    )


# ==================================================================
# RECEBER VOLUMETRIAS (integração com sistema de folha)
# ==================================================================

async def receber_volumetrias(
    db:          AsyncSession,
    fatura_id:   UUID,
    volumetrias: list[VolumetriaInput],
    usuario:     str,
) -> Fatura:
    """
    Recebe as volumetrias do sistema de folha e calcula o valor
    por faixa de preço para cada tipo de vínculo.
    """
    fatura = await _get_fatura_ou_404(db, fatura_id)

    if fatura.status not in (StatusFatura.APURADA, StatusFatura.RASCUNHO):
        raise HTTPException(status_code=400, detail="Volumetrias só podem ser lançadas em faturas no status RASCUNHO ou APURADA.")

    # Remove volumetrias anteriores (substituição completa)
    for vol_ant in list(fatura.volumetrias):
        await db.delete(vol_ant)

    # Remove itens de volumetria anteriores da fatura
    for item_ant in [i for i in fatura.itens if i.eh_volumetria]:
        await db.delete(item_ant)

    await db.flush()

    # Busca a competência e o produto de cada item para calcular a faixa
    for vol in volumetrias:
        # Descobre o produto_id do contrato_item
        item_row = await db.execute(
            text("SELECT produto_id FROM contratos_itens WHERE id = :iid"),
            {"iid": str(vol.contrato_item_id)}
        )
        produto_id = item_row.scalar()
        if not produto_id:
            raise HTTPException(status_code=404, detail=f"Item {vol.contrato_item_id} não encontrado.")

        # Busca o valor unitário pela faixa
        valor_unit = await _busca_faixa_preco(
            db, produto_id, vol.tipo_vinculo.value, vol.quantidade, fatura.competencia
        )

        # Grava volumetria
        db.add(FaturaVolumetria(
            fatura_id         = fatura_id,
            contrato_item_id  = vol.contrato_item_id,
            tipo_vinculo      = vol.tipo_vinculo,
            quantidade        = vol.quantidade,
            valor_unitario    = valor_unit,
            fonte             = vol.fonte,
            competencia_folha = vol.competencia_folha or fatura.competencia,
        ))

        # Grava como item da fatura (para o descritivo)
        tipo_label = vol.tipo_vinculo.value.replace("_", " ").title()
        db.add(FaturaItem(
            fatura_id        = fatura_id,
            contrato_item_id = vol.contrato_item_id,
            produto_id       = produto_id,
            descricao        = f"Folha de Pagamento — {tipo_label}",
            quantidade       = Decimal(str(vol.quantidade)),
            valor_unitario   = valor_unit,
            desconto_pct     = Decimal("0"),
            eh_volumetria    = True,
        ))

    await db.flush()
    await db.refresh(fatura)

    # Atualiza descrição da NF com novo valor total
    from app.models.contrato import Contrato
    contrato = await db.get(Contrato, fatura.contrato_id)
    fatura.descricao_nf = _gera_descricao_nf(
        contrato.modalidade.value, fatura.competencia, fatura.valor_total
    )

    return fatura


# ==================================================================
# LISTAGEM DE FATURAS
# ==================================================================

async def listar_faturas(
    db:           AsyncSession,
    pagina:       int = 1,
    por_pagina:   int = 20,
    competencia:  Optional[date] = None,
    status:       Optional[str]  = None,
    dia_apuracao: Optional[str]  = None,
    contrato_id:  Optional[UUID] = None,
    em_atraso:    bool = False,
) -> FaturaListOut:

    query = text("""
        SELECT id, numero_fatura, contrato_id, contrato_numero, cliente_nome,
               modalidade, competencia, dia_apuracao, data_vencimento, status,
               valor_servicos, valor_volumetria, valor_total, numero_nf,
               docs_emitidos, dias_atraso, criado_em
        FROM vw_faturas_resumo
        WHERE (:competencia  IS NULL OR competencia  = :competencia)
          AND (:status       IS NULL OR status       = :status)
          AND (:dia_apuracao IS NULL OR dia_apuracao = :dia_apuracao)
          AND (:contrato_id  IS NULL OR contrato_id  = :contrato_id::uuid)
          AND (:em_atraso    = FALSE  OR dias_atraso > 0)
        ORDER BY competencia DESC, cliente_nome
        LIMIT :limit OFFSET :offset
    """)

    count_q = text("""
        SELECT COUNT(*) FROM vw_faturas_resumo
        WHERE (:competencia  IS NULL OR competencia  = :competencia)
          AND (:status       IS NULL OR status       = :status)
          AND (:dia_apuracao IS NULL OR dia_apuracao = :dia_apuracao)
          AND (:contrato_id  IS NULL OR contrato_id  = :contrato_id::uuid)
          AND (:em_atraso    = FALSE  OR dias_atraso > 0)
    """)

    params = {
        "competencia":  competencia,
        "status":       status,
        "dia_apuracao": dia_apuracao,
        "contrato_id":  str(contrato_id) if contrato_id else None,
        "em_atraso":    em_atraso,
        "limit":        por_pagina,
        "offset":       (pagina - 1) * por_pagina,
    }

    total = (await db.execute(count_q, params)).scalar()
    rows  = await db.execute(query, params)
    dados = [FaturaResumoOut.model_validate(dict(r._mapping)) for r in rows]

    return FaturaListOut(
        dados=dados,
        meta={
            "total": total, "pagina": pagina,
            "por_pagina": por_pagina,
            "paginas": ceil(total / por_pagina) if total else 0,
        }
    )


async def buscar_fatura(db: AsyncSession, fatura_id: UUID) -> Fatura:
    return await _get_fatura_ou_404(db, fatura_id)


# ==================================================================
# REGISTRAR PAGAMENTO
# ==================================================================

async def registrar_pagamento(
    db:        AsyncSession,
    fatura_id: UUID,
    dados:     FaturaRegistrarPagamento,
    usuario:   str,
) -> Fatura:
    fatura = await _get_fatura_ou_404(db, fatura_id)

    if fatura.status in (StatusFatura.PAGA, StatusFatura.CANCELADA):
        raise HTTPException(status_code=400, detail="Fatura já está paga ou cancelada.")

    fatura.valor_pago      = dados.valor_pago
    fatura.data_pagamento  = dados.data_pagamento
    fatura.status          = StatusFatura.PAGA
    fatura.observacoes     = dados.observacoes
    fatura.atualizado_por  = usuario

    await db.flush()
    await db.refresh(fatura)
    return fatura


# ==================================================================
# REGISTRAR NFS-e / DADOS DA NOTA FISCAL
# ==================================================================

async def registrar_nf(
    db:        AsyncSession,
    fatura_id: UUID,
    dados:     FaturaRegistrarNF,
    usuario:   str,
) -> Fatura:
    fatura = await _get_fatura_ou_404(db, fatura_id)

    fatura.numero_nf           = dados.numero_nf
    fatura.serie_nf            = dados.serie_nf
    fatura.codigo_verificacao  = dados.codigo_verificacao
    fatura.data_emissao_nf     = dados.data_emissao_nf
    fatura.status              = StatusFatura.EMITIDA
    fatura.atualizado_por      = usuario

    # Registra o documento
    db.add(FaturaDocumento(
        fatura_id   = fatura_id,
        tipo        = TipoDocumentoFat.NFS_E,
        status      = StatusDocumento.EMITIDO,
        numero      = dados.numero_nf,
        emitido_em  = __import__("datetime").datetime.now(),
        emitido_por = usuario,
    ))

    await db.flush()
    await db.refresh(fatura)
    return fatura


# ==================================================================
# GERAR PAYLOAD K2 (preparação para envio à NFS-e)
# ==================================================================

async def gerar_payload_k2(
    db:        AsyncSession,
    fatura_id: UUID,
) -> dict:
    """
    Gera o payload no formato esperado pelo K2 Software para emissão da NFS-e.
    A descrição segue o padrão: "Prestação de Serviços Conforme Contrato [MOD] competência MM/AAAA — Valor Total R$ X"
    O valor enviado é sempre o total agrupado (não item a item).
    """
    fatura = await _get_fatura_ou_404(db, fatura_id)

    from app.models.contrato import Contrato
    from app.models.cliente import Cliente
    contrato = await db.get(Contrato, fatura.contrato_id)
    cliente  = await db.get(Cliente, contrato.cliente_id)

    payload = {
        "tipo_rps":        "RPS",
        "serie_rps":       "1",
        "competencia":     fatura.competencia.isoformat(),
        "descricao":       fatura.descricao_nf,
        "valor_servicos":  float(fatura.valor_total),
        "tomador": {
            "cnpj_cpf":   cliente.cnpj or cliente.cpf,
            "razao_social": cliente.razao_social or cliente.nome_completo,
        },
        "referencia_interna": fatura.numero_fatura,
    }

    # Registra o payload para auditoria
    doc = FaturaDocumento(
        fatura_id    = fatura_id,
        tipo         = TipoDocumentoFat.RPS,
        status       = StatusDocumento.PENDENTE,
        payload_envio = payload,
    )
    db.add(doc)
    await db.flush()

    return {"fatura_id": str(fatura_id), "payload": payload, "documento_id": str(doc.id)}


# ==================================================================
# DESCRITIVO DETALHADO (para o cliente)
# ==================================================================

async def gerar_descritivo(db: AsyncSession, fatura_id: UUID) -> dict:
    """
    Gera o descritivo detalhado da fatura para envio ao cliente.
    Inclui: itens de serviço + detalhamento de volumetria por tipo de vínculo.
    """
    fatura = await _get_fatura_ou_404(db, fatura_id)

    from app.models.contrato import Contrato
    from app.models.cliente import Cliente
    contrato = await db.get(Contrato, fatura.contrato_id)
    cliente  = await db.get(Cliente, contrato.cliente_id)

    itens_servico = [
        {
            "descricao":      i.descricao,
            "quantidade":     float(i.quantidade),
            "valor_unitario": float(i.valor_unitario),
            "desconto_pct":   float(i.desconto_pct),
            "valor_total":    float(i.quantidade * i.valor_unitario * (1 - i.desconto_pct / 100)),
        }
        for i in fatura.itens if not i.eh_volumetria
    ]

    volumetrias = [
        {
            "tipo_vinculo":   v.tipo_vinculo.value,
            "quantidade":     v.quantidade,
            "valor_unitario": float(v.valor_unitario),
            "valor_total":    float(v.quantidade * v.valor_unitario),
        }
        for v in fatura.volumetrias
    ]

    descritivo = {
        "numero_fatura":    fatura.numero_fatura,
        "competencia":      fatura.competencia.strftime("%m/%Y"),
        "cliente":          cliente.razao_social or cliente.nome_completo,
        "cnpj_cpf":         cliente.cnpj or cliente.cpf,
        "contrato":         contrato.numero,
        "modalidade":       contrato.modalidade.value,
        "data_vencimento":  fatura.data_vencimento.strftime("%d/%m/%Y"),
        "itens_servico":    itens_servico,
        "volumetrias":      volumetrias,
        "total_servicos":   float(fatura.valor_servicos),
        "total_volumetria": float(fatura.valor_volumetria),
        "valor_total":      float(fatura.valor_total),
        "numero_nf":        fatura.numero_nf,
    }

    return descritivo
