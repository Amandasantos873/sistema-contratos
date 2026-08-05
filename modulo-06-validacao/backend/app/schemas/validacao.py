from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.validacao import SeveridadeAlerta, StatusValidacao, StatusAlerta


class AlertaOut(BaseModel):
    id:               UUID
    codigo:           str
    severidade:       SeveridadeAlerta
    detalhe:          str
    item_referencia:  Optional[UUID]
    valor_esperado:   Optional[Decimal]
    valor_encontrado: Optional[Decimal]
    status:           StatusAlerta
    justificativa:    Optional[str]

    model_config = {"from_attributes": True}


class ValidacaoOut(BaseModel):
    id:             UUID
    fatura_id:      UUID
    status:         StatusValidacao
    total_criticos: int
    total_atencao:  int
    total_info:     int
    executado_em:   datetime
    alertas:        list[AlertaOut] = []
    analise_ia:     Optional[Any]   = None

    model_config = {"from_attributes": True}


class JustificarAlertaRequest(BaseModel):
    justificativa: str = Field(..., min_length=15, description="Justificativa obrigatória para emissão com ressalva.")


class EmitirComRessalvaRequest(BaseModel):
    """Emite a fatura mesmo com alertas críticos, mediante justificativa por alerta."""
    justificativas: list[dict] = Field(
        ...,
        description="Lista de {alerta_id, justificativa} — obrigatório para cada CRITICO em aberto."
    )


class AvisoPrevioCreate(BaseModel):
    contrato_item_id:    UUID
    data_solicitacao:    date
    prazo_vigencia_dias: int  = Field(default=30, ge=1, le=180)
    motivo:              str  = Field(..., min_length=10)


class AvisoPrevioOut(BaseModel):
    id:                  UUID
    contrato_item_id:    UUID
    data_solicitacao:    date
    prazo_vigencia_dias: int
    data_fim_vigencia:   date
    motivo:              str
    status:              str
    criado_por:          str

    model_config = {"from_attributes": True}


class AlertaPainelOut(BaseModel):
    alerta_id:      UUID
    fatura_id:      UUID
    numero_fatura:  str
    cliente_nome:   str
    competencia:    date
    codigo:         str
    descricao_alerta: str
    severidade:     SeveridadeAlerta
    detalhe:        str
    valor_esperado:  Optional[Decimal]
    valor_encontrado:Optional[Decimal]
    status_alerta:  str
    criado_em:      datetime

    model_config = {"from_attributes": True}
