"""
Service de validação de faturamento.

Executa 8 regras determinísticas contra os dados do contrato e da fatura.
Opcionalmente, chama a Claude API para análise de anomalias de volumetria.

Regras:
  VAL001 — Valor faturado ≠ valor contratado
  VAL002 — Item sem go-live confirmado
  VAL003 — Fatura fora da data de apuração do contrato
  VAL004 — Reajuste aplicado sem aprovação
  VAL005 — Contrato vencido ou encerrado
  VAL006 — Volumetria sem integração recebida
  VAL007 — Produto cancelado após data de cancelamento
  VAL008 — Produto em aviso prévio com prazo vencido
  VAL009 — Volumetria com variação > 20% vs mês anterior (IA opcional)
  VAL010 — Fatura duplicada na mesma competência
  VAL011 — Cliente bloqueado com fatura em aberto
  VAL012 — Desconto não previsto no contrato
"""
import json
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.validacao import (
    FaturaValidacao, FaturaAlerta, AvisoPrevioCancelamento,
    SeveridadeAlerta, StatusValidacao, StatusAlerta
)
from app.models.fatura import Fatura, FaturaItem, FaturaVolumetria
from app.models.contrato import Contrato, ContratoItem
from app.schemas.validacao import (
    ValidacaoOut, AlertaOut, AvisoPrevioCreate,
    JustificarAlertaRequest, EmitirComRessalvaRequest, AlertaPainelOut
)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

TOLERANCIA_VALOR = Decimal("0.02")   # 2 centavos de tolerância para arredondamentos

def _alerta(codigo: str, severidade: str, detalhe: str,
            item_ref=None, esperado=None, encontrado=None) -> dict:
    return {
        "codigo": codigo, "severidade": severidade, "detalhe": detalhe,
        "item_referencia": item_ref, "valor_esperado": esperado, "valor_encontrado": encontrado,
    }


# ==================================================================
# REGRAS DETERMINÍSTICAS
# ==================================================================

async def _val001_valor_incorreto(db, fatura: Fatura, contrato: Contrato) -> list[dict]:
    """Compara valor de cada item da fatura com o valor atual no contrato."""
    alertas = []
    for fi in fatura.itens:
        if fi.eh_volumetria:
            continue
        ci_row = await db.execute(
            text("SELECT valor_unitario, desconto_pct, produto_id FROM contratos_itens WHERE id = :iid"),
            {"iid": str(fi.contrato_item_id)}
        )
        ci = ci_row.fetchone()
        if not ci:
            continue
        esperado   = round(ci.valor_unitario * fi.quantidade * (1 - ci.desconto_pct / 100), 2)
        encontrado = round(fi.valor_unitario * fi.quantidade * (1 - fi.desconto_pct / 100), 2)
        if abs(encontrado - esperado) > TOLERANCIA_VALOR:
            alertas.append(_alerta(
                "VAL001", "CRITICO",
                f"Item '{fi.descricao}': valor contratado R$ {esperado} × valor faturado R$ {encontrado}.",
                fi.id, esperado, encontrado
            ))
    return alertas


async def _val002_sem_goLive(db, fatura: Fatura) -> list[dict]:
    """Verifica se algum item da fatura não tem go-live confirmado."""
    alertas = []
    for fi in fatura.itens:
        if fi.eh_volumetria:
            continue
        row = await db.execute(
            text("SELECT data_goLive_item, status_item FROM contratos_itens WHERE id = :iid"),
            {"iid": str(fi.contrato_item_id)}
        )
        ci = row.fetchone()
        if ci and (ci.data_goLive_item is None or ci.status_item != "ATIVO"):
            alertas.append(_alerta(
                "VAL002", "CRITICO",
                f"Item '{fi.descricao}' está sendo faturado sem go-live confirmado.",
                fi.id
            ))
    return alertas


async def _val003_data_apuracao(db, fatura: Fatura, contrato: Contrato) -> list[dict]:
    """Verifica se o dia de apuração da fatura bate com o do contrato."""
    if fatura.dia_apuracao != contrato.dia_faturamento.value:
        return [_alerta(
            "VAL003", "ATENCAO",
            f"Fatura apurada em '{fatura.dia_apuracao}', mas o contrato define '{contrato.dia_faturamento.value}'.",
        )]
    return []


async def _val004_reajuste_sem_aprovacao(db, fatura: Fatura) -> list[dict]:
    """Verifica se há reajuste efetivado sem aprovação registrada."""
    row = await db.execute(
        text("""
            SELECT COUNT(*) FROM contratos_reajustes
            WHERE contrato_id = :cid
              AND status = 'EFETIVADO'
              AND aprovado_por IS NULL
        """),
        {"cid": str(fatura.contrato_id)}
    )
    count = row.scalar()
    if count > 0:
        return [_alerta("VAL004", "CRITICO",
            f"{count} reajuste(s) efetivado(s) sem registro de aprovação interna.")]
    return []


async def _val005_contrato_vencido(db, fatura: Fatura, contrato: Contrato) -> list[dict]:
    """Verifica se o contrato está encerrado, cancelado ou com vigência expirada."""
    if contrato.status.value in ("ENCERRADO", "CANCELADO"):
        return [_alerta("VAL005", "CRITICO",
            f"Contrato com status '{contrato.status.value}' — não deve ser faturado.")]
    if contrato.data_fim_contrato and contrato.data_fim_contrato < fatura.competencia:
        return [_alerta("VAL005", "CRITICO",
            f"Contrato vencido em {contrato.data_fim_contrato.strftime('%d/%m/%Y')} "
            f"— competência {fatura.competencia.strftime('%m/%Y')} fora da vigência.")]
    return []


async def _val006_volumetria_sem_integracao(db, fatura: Fatura, contrato: Contrato) -> list[dict]:
    """Para contratos BPO/BSP, verifica se a integração de folha foi recebida."""
    if contrato.modalidade.value not in ("BPO", "BSP"):
        return []
    tem_item_folha = any(fi.eh_volumetria for fi in fatura.itens)
    if not tem_item_folha and len(fatura.volumetrias) == 0:
        # Verifica se existem produtos de folha ativos no contrato
        row = await db.execute(
            text("""
                SELECT COUNT(*) FROM contratos_itens ci
                JOIN produtos_servicos ps ON ps.id = ci.produto_id
                WHERE ci.contrato_id = :cid AND ci.ativo = TRUE
                  AND ci.fase = 'RECORRENCIA' AND ci.status_item = 'ATIVO'
                  AND ps.mao_de_obra_alocada = TRUE
            """),
            {"cid": str(fatura.contrato_id)}
        )
        if row.scalar() > 0:
            return [_alerta("VAL006", "ATENCAO",
                "Contrato possui itens de mão de obra alocada, mas nenhuma volumetria foi recebida da integração de folha.")]
    return []


async def _val007_produto_cancelado(db, fatura: Fatura) -> list[dict]:
    """Verifica se algum item faturado está com status CANCELADO no contrato."""
    alertas = []
    for fi in fatura.itens:
        if fi.eh_volumetria:
            continue
        row = await db.execute(
            text("SELECT status_item, produto_id FROM contratos_itens WHERE id = :iid"),
            {"iid": str(fi.contrato_item_id)}
        )
        ci = row.fetchone()
        if ci and ci.status_item == "CANCELADO":
            alertas.append(_alerta(
                "VAL007", "CRITICO",
                f"Item '{fi.descricao}' está cancelado no contrato mas consta na fatura.",
                fi.id
            ))
    return alertas


async def _val008_aviso_previo_vencido(db, fatura: Fatura) -> list[dict]:
    """Verifica se algum item está em aviso prévio com prazo de vigência expirado."""
    alertas = []
    for fi in fatura.itens:
        if fi.eh_volumetria:
            continue
        row = await db.execute(
            text("""
                SELECT id, data_fim_vigencia FROM aviso_previo_cancelamento
                WHERE contrato_item_id = :iid
                  AND status = 'ATIVO'
                  AND data_fim_vigencia < :comp
            """),
            {"iid": str(fi.contrato_item_id), "comp": fatura.competencia}
        )
        aviso = row.fetchone()
        if aviso:
            alertas.append(_alerta(
                "VAL008", "CRITICO",
                f"Item '{fi.descricao}' em aviso prévio com vigência encerrada em "
                f"{aviso.data_fim_vigencia.strftime('%d/%m/%Y')} — não deve mais ser faturado.",
                fi.id
            ))
    return alertas


async def _val009_volumetria_anomalia(db, fatura: Fatura) -> list[dict]:
    """Variação de volumetria > 20% em relação ao mês anterior."""
    alertas = []
    for vol in fatura.volumetrias:
        row = await db.execute(
            text("""
                SELECT fv.quantidade FROM faturas_volumetrias fv
                JOIN faturas f ON f.id = fv.fatura_id
                WHERE fv.contrato_item_id = :iid
                  AND fv.tipo_vinculo = :tv
                  AND f.competencia < :comp
                ORDER BY f.competencia DESC LIMIT 1
            """),
            {"iid": str(vol.contrato_item_id), "tv": vol.tipo_vinculo.value, "comp": fatura.competencia}
        )
        ant = row.scalar()
        if ant and ant > 0:
            variacao = abs(vol.quantidade - ant) / ant
            if variacao > 0.20:
                alertas.append(_alerta(
                    "VAL009", "ATENCAO",
                    f"Volumetria {vol.tipo_vinculo.value}: {ant} → {vol.quantidade} "
                    f"({variacao*100:.1f}% de variação vs mês anterior).",
                    None, Decimal(str(ant)), Decimal(str(vol.quantidade))
                ))
    return alertas


async def _val010_duplicata(db, fatura: Fatura) -> list[dict]:
    """Verifica se já existe outra fatura para o mesmo contrato e competência."""
    row = await db.execute(
        text("""
            SELECT COUNT(*) FROM faturas
            WHERE contrato_id = :cid AND competencia = :comp AND id != :fid
        """),
        {"cid": str(fatura.contrato_id), "comp": fatura.competencia, "fid": str(fatura.id)}
    )
    if row.scalar() > 0:
        return [_alerta("VAL010", "CRITICO",
            f"Já existe outra fatura para competência {fatura.competencia.strftime('%m/%Y')} neste contrato.")]
    return []


async def _val011_cliente_bloqueado(db, fatura: Fatura, contrato: Contrato) -> list[dict]:
    """Verifica se o cliente está bloqueado ou inativo."""
    row = await db.execute(
        text("SELECT status FROM clientes WHERE id = :cid"),
        {"cid": str(contrato.cliente_id)}
    )
    status = row.scalar()
    if status in ("INATIVO", "BLOQUEADO"):
        return [_alerta("VAL011", "ATENCAO",
            f"Cliente com status '{status}' possui fatura em aberto.")]
    return []


async def _val012_desconto_nao_previsto(db, fatura: Fatura) -> list[dict]:
    """Verifica se desconto aplicado na fatura difere do contratado."""
    alertas = []
    for fi in fatura.itens:
        if fi.eh_volumetria:
            continue
        row = await db.execute(
            text("SELECT desconto_pct FROM contratos_itens WHERE id = :iid"),
            {"iid": str(fi.contrato_item_id)}
        )
        desconto_contrato = row.scalar()
        if desconto_contrato is not None and abs(fi.desconto_pct - desconto_contrato) > Decimal("0.01"):
            alertas.append(_alerta(
                "VAL012", "ATENCAO",
                f"Item '{fi.descricao}': desconto contratado {desconto_contrato}% × aplicado {fi.desconto_pct}%.",
                fi.id, desconto_contrato, fi.desconto_pct
            ))
    return alertas


# ==================================================================
# ANÁLISE IA — ANOMALIAS (Claude API, opcional)
# ==================================================================

async def _analise_ia_anomalias(fatura_id: UUID, contexto: dict) -> Optional[dict]:
    """
    Chama a Claude API para análise de anomalias que a lógica determinística não captura.
    Retorna um dicionário com anomalias identificadas ou None em caso de erro.
    """
    prompt = f"""Você é um auditor de faturamento. Analise os dados abaixo e identifique anomalias.
Retorne SOMENTE um JSON com a chave "anomalias" contendo uma lista de objetos com:
  - codigo: string (use VAL_IA_001, VAL_IA_002, etc.)
  - severidade: "CRITICO" | "ATENCAO" | "INFO"
  - detalhe: string descrevendo a anomalia encontrada

Dados da fatura:
{json.dumps(contexto, default=str, ensure_ascii=False)}

Se não houver anomalias, retorne {{"anomalias": []}}."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            if response.status_code == 200:
                data = response.json()
                texto = data["content"][0]["text"]
                # Remove possíveis backticks
                texto = texto.replace("```json", "").replace("```", "").strip()
                return json.loads(texto)
    except Exception:
        pass
    return None


# ==================================================================
# VALIDAÇÃO PRINCIPAL
# ==================================================================

async def validar_fatura(
    db:           AsyncSession,
    fatura_id:    UUID,
    usuario:      str,
    com_ia:       bool = False,
) -> ValidacaoOut:
    """
    Executa todas as regras de validação em uma fatura.
    Se com_ia=True, chama adicionalmente a Claude API para análise de anomalias.
    """
    # Carrega fatura completa
    result = await db.execute(
        select(Fatura)
        .options(
            selectinload(Fatura.itens),
            selectinload(Fatura.volumetrias),
        )
        .where(Fatura.id == fatura_id)
    )
    fatura = result.scalar_one_or_none()
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada.")

    # Carrega contrato
    contrato = await db.get(Contrato, fatura.contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")

    # Executa todas as regras
    todos_alertas: list[dict] = []
    for regra in [
        _val001_valor_incorreto(db, fatura, contrato),
        _val002_sem_goLive(db, fatura),
        _val003_data_apuracao(db, fatura, contrato),
        _val004_reajuste_sem_aprovacao(db, fatura),
        _val005_contrato_vencido(db, fatura, contrato),
        _val006_volumetria_sem_integracao(db, fatura, contrato),
        _val007_produto_cancelado(db, fatura),
        _val008_aviso_previo_vencido(db, fatura),
        _val009_volumetria_anomalia(db, fatura),
        _val010_duplicata(db, fatura),
        _val011_cliente_bloqueado(db, fatura, contrato),
        _val012_desconto_nao_previsto(db, fatura),
    ]:
        todos_alertas.extend(await regra)

    # Contadores
    criticos = sum(1 for a in todos_alertas if a["severidade"] == "CRITICO")
    atencao  = sum(1 for a in todos_alertas if a["severidade"] == "ATENCAO")
    infos    = sum(1 for a in todos_alertas if a["severidade"] == "INFO")

    # Status
    if criticos > 0:
        status = StatusValidacao.BLOQUEADA
    elif atencao > 0 or infos > 0:
        status = StatusValidacao.COM_ALERTAS
    else:
        status = StatusValidacao.APROVADA

    # Análise IA opcional
    analise_ia = None
    if com_ia and len(fatura.volumetrias) > 0:
        contexto = {
            "fatura_id":    str(fatura_id),
            "competencia":  fatura.competencia.isoformat(),
            "valor_total":  float(fatura.valor_total),
            "volumetrias":  [
                {"tipo": v.tipo_vinculo.value, "quantidade": v.quantidade, "valor": float(v.valor_total)}
                for v in fatura.volumetrias
            ],
            "alertas_deterministicos": len(todos_alertas),
        }
        analise_ia = await _analise_ia_anomalias(fatura_id, contexto)

    # Persiste validação
    validacao = FaturaValidacao(
        fatura_id      = fatura_id,
        status         = status,
        total_criticos = criticos,
        total_atencao  = atencao,
        total_info     = infos,
        executado_por  = usuario,
        analise_ia     = analise_ia,
    )
    db.add(validacao)
    await db.flush()

    # Persiste alertas
    for a in todos_alertas:
        db.add(FaturaAlerta(
            validacao_id     = validacao.id,
            fatura_id        = fatura_id,
            codigo           = a["codigo"],
            severidade       = a["severidade"],
            detalhe          = a["detalhe"],
            item_referencia  = a.get("item_referencia"),
            valor_esperado   = a.get("valor_esperado"),
            valor_encontrado = a.get("valor_encontrado"),
        ))

    await db.flush()
    await db.refresh(validacao)

    return ValidacaoOut(
        id             = validacao.id,
        fatura_id      = validacao.fatura_id,
        status         = validacao.status,
        total_criticos = validacao.total_criticos,
        total_atencao  = validacao.total_atencao,
        total_info     = validacao.total_info,
        executado_em   = validacao.executado_em,
        analise_ia     = analise_ia,
        alertas        = [AlertaOut.model_validate(a) for a in validacao.alertas],
    )


# ==================================================================
# JUSTIFICAR E EMITIR COM RESSALVA
# ==================================================================

async def justificar_alerta(
    db:         AsyncSession,
    alerta_id:  UUID,
    dados:      JustificarAlertaRequest,
    usuario:    str,
) -> FaturaAlerta:
    alerta = await db.get(FaturaAlerta, alerta_id)
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    if alerta.status != StatusAlerta.ABERTO:
        raise HTTPException(status_code=400, detail="Alerta já foi tratado.")

    alerta.justificativa   = dados.justificativa
    alerta.justificado_por = usuario
    alerta.status          = StatusAlerta.JUSTIFICADO
    from sqlalchemy.sql import func as sqlfunc
    alerta.justificado_em  = sqlfunc.now()

    await db.flush()
    return alerta


async def emitir_com_ressalva(
    db:        AsyncSession,
    fatura_id: UUID,
    dados:     EmitirComRessalvaRequest,
    usuario:   str,
) -> dict:
    """
    Permite emitir a fatura mesmo com alertas críticos,
    desde que todos os críticos em aberto tenham justificativa.
    """
    from app.models.fatura import Fatura as FaturaModel, StatusFatura
    fatura = await db.get(FaturaModel, fatura_id)
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada.")

    # Aplica justificativas
    jmap = {str(j["alerta_id"]): j["justificativa"] for j in dados.justificativas}

    # Busca alertas críticos abertos
    result = await db.execute(
        select(FaturaAlerta).where(
            FaturaAlerta.fatura_id == fatura_id,
            FaturaAlerta.severidade == SeveridadeAlerta.CRITICO,
            FaturaAlerta.status == StatusAlerta.ABERTO,
        )
    )
    criticos_abertos = result.scalars().all()

    nao_justificados = [a for a in criticos_abertos if str(a.id) not in jmap]
    if nao_justificados:
        raise HTTPException(
            status_code=400,
            detail=f"{len(nao_justificados)} alerta(s) crítico(s) sem justificativa. "
                   f"Todos os críticos precisam ser justificados para emissão com ressalva."
        )

    for alerta in criticos_abertos:
        alerta.justificativa   = jmap[str(alerta.id)]
        alerta.justificado_por = usuario
        alerta.status          = StatusAlerta.JUSTIFICADO

    # Atualiza status da validação mais recente
    await db.execute(
        text("""
            UPDATE faturas_validacoes SET status = 'JUSTIFICADA'
            WHERE fatura_id = :fid
            ORDER BY executado_em DESC LIMIT 1
        """),
        {"fid": str(fatura_id)}
    )

    await db.flush()
    return {"fatura_id": str(fatura_id), "status": "JUSTIFICADA", "alertas_justificados": len(criticos_abertos)}


# ==================================================================
# PAINEL DE ALERTAS ABERTOS
# ==================================================================

async def listar_alertas_abertos(db: AsyncSession) -> list[AlertaPainelOut]:
    rows = await db.execute(
        text("""
            SELECT alerta_id, fatura_id, numero_fatura, cliente_nome, competencia,
                   codigo, descricao_alerta, severidade, detalhe,
                   valor_esperado, valor_encontrado, status_alerta, criado_em
            FROM vw_faturas_alertas_abertos
        """)
    )
    return [AlertaPainelOut.model_validate(dict(r._mapping)) for r in rows]


# ==================================================================
# AVISO PRÉVIO DE CANCELAMENTO
# ==================================================================

async def registrar_aviso_previo(
    db:      AsyncSession,
    dados:   AvisoPrevioCreate,
    usuario: str,
) -> AvisoPrevioCancelamento:
    from datetime import timedelta
    data_fim = dados.data_solicitacao + timedelta(days=dados.prazo_vigencia_dias)
    aviso = AvisoPrevioCancelamento(
        contrato_item_id    = dados.contrato_item_id,
        data_solicitacao    = dados.data_solicitacao,
        prazo_vigencia_dias = dados.prazo_vigencia_dias,
        data_fim_vigencia   = data_fim,
        motivo              = dados.motivo,
        criado_por          = usuario,
    )
    db.add(aviso)
    await db.flush()
    await db.refresh(aviso)
    return aviso
