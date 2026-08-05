from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from app.models.reajuste import IndiceEconomico, StatusReajuste, TipoAditivo


# ==================================================================
# ÍNDICES ECONÔMICOS
# ==================================================================

class IndiceCreate(BaseModel):
    indice:           IndiceEconomico
    competencia:      date
    valor_percentual: Decimal = Field(..., description="Variação mensal em % — ex: 0.43 para 0,43%")
    fonte:            Optional[str] = None

    @model_validator(mode="after")
    def valida_dia_um(self):
        if self.competencia.day != 1:
            raise ValueError("Competência deve ser sempre o 1º dia do mês.")
        return self

class IndiceOut(BaseModel):
    id:               int
    indice:           IndiceEconomico
    competencia:      date
    valor_percentual: Decimal
    fonte:            Optional[str]
    criado_em:        datetime

    model_config = {"from_attributes": True}

class IndiceAcumuladoOut(BaseModel):
    indice:               IndiceEconomico
    competencia_inicial:  date
    competencia_final:    date
    percentual_acumulado: Decimal
    meses:                int


# ==================================================================
# REAJUSTE — ITEM
# ==================================================================

class ReajusteItemOut(BaseModel):
    id:                  UUID
    contrato_item_id:    UUID
    produto_nome:        Optional[str] = None   # enriquecido no service
    valor_anterior:      Decimal
    percentual_aplicado: Decimal
    valor_novo:          Decimal
    variacao:            Optional[Decimal]
    aprovado:            Optional[bool]
    observacoes:         Optional[str]

    model_config = {"from_attributes": True}

class ReajusteItemAprovar(BaseModel):
    contrato_item_id:    UUID
    aprovado:            bool
    percentual_negociado:Optional[Decimal] = None   # se diferente do calculado
    observacoes:         Optional[str]     = None


# ==================================================================
# REAJUSTE — CABEÇALHO
# ==================================================================

class ReajusteCalcularRequest(BaseModel):
    """Solicita o cálculo de um reajuste para um contrato."""
    contrato_id:        UUID
    indice:             IndiceEconomico
    percentual_fixo:    Optional[Decimal] = None   # obrigatório se indice=FIXO
    data_efetivacao:    date
    observacoes:        Optional[str]     = None

    @model_validator(mode="after")
    def valida_fixo(self):
        if self.indice == IndiceEconomico.FIXO and not self.percentual_fixo:
            raise ValueError("percentual_fixo é obrigatório quando indice = FIXO.")
        return self

class ReajusteAprovarRequest(BaseModel):
    """Aprovação com possibilidade de ajustar percentual aplicado e itens individualmente."""
    percentual_aplicado: Optional[Decimal]         = None   # sobrescreve o calculado se informado
    itens:               list[ReajusteItemAprovar] = Field(default_factory=list)
    observacoes:         Optional[str]             = None

class ReajusteReprovarRequest(BaseModel):
    motivo: str = Field(..., min_length=10)

class ReajusteComunicarRequest(BaseModel):
    data_comunicacao: date

class ReajusteOut(BaseModel):
    id:                    UUID
    contrato_id:           UUID
    numero_reajuste:       int
    indice:                IndiceEconomico
    percentual_fixo:       Optional[Decimal]
    data_base:             date
    data_fim_periodo:      date
    competencia_inicial:   date
    competencia_final:     date
    percentual_calculado:  Optional[Decimal]
    percentual_aplicado:   Optional[Decimal]
    valor_mensal_anterior: Decimal
    valor_mensal_novo:     Optional[Decimal]
    variacao_mensal:       Optional[Decimal]
    status:                StatusReajuste
    data_calculo:          datetime
    calculado_por:         str
    data_aprovacao:        Optional[datetime]
    aprovado_por:          Optional[str]
    motivo_reprovacao:     Optional[str]
    data_comunicacao:      Optional[date]
    data_efetivacao:       date
    observacoes:           Optional[str]
    aditivo_id:            Optional[UUID]
    criado_em:             datetime
    itens:                 list[ReajusteItemOut] = []

    model_config = {"from_attributes": True}

class ReajustePendenteOut(BaseModel):
    """Linha da view vw_reajustes_pendentes."""
    contrato_id:            UUID
    contrato_numero:        str
    cliente_nome:           str
    modalidade:             str
    valor_mensal:           Decimal
    data_inicio_recorrencia:Optional[date]
    ultimo_reajuste:        Optional[date]
    proximo_reajuste:       date
    dias_atraso:            int
    status_em_andamento:    Optional[str]
    total_reajustes:        int

    model_config = {"from_attributes": True}


# ==================================================================
# ADITIVO
# ==================================================================

class AditivoCreate(BaseModel):
    tipo_aditivo:   TipoAditivo
    descricao:      str  = Field(..., min_length=10)
    data_aditivo:   date
    data_vigencia:  date
    valor_anterior: Optional[Decimal] = None
    valor_novo:     Optional[Decimal] = None
    observacoes:    Optional[str]     = None

class AditivoOut(BaseModel):
    id:             UUID
    contrato_id:    UUID
    numero_aditivo: int
    tipo:           str
    tipo_aditivo:   Optional[TipoAditivo]
    descricao:      str
    data_aditivo:   date
    data_vigencia:  date
    valor_anterior: Optional[Decimal]
    valor_novo:     Optional[Decimal]
    status:         str
    aprovado_por:   Optional[str]
    data_aprovacao: Optional[date]
    criado_em:      datetime
    criado_por:     str

    model_config = {"from_attributes": True}
