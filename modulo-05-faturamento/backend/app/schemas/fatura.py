from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.fatura import (
    StatusFatura, TipoDocumentoFat, StatusDocumento, TipoVinculoFolha
)


# ==================================================================
# FAIXAS DE VOLUMETRIA
# ==================================================================

class FaixaCreate(BaseModel):
    produto_id:      int
    tipo_vinculo:    TipoVinculoFolha
    faixa_de:        int = Field(..., ge=0)
    faixa_ate:       Optional[int] = None
    valor_unitario:  Decimal = Field(..., gt=0)
    vigencia_inicio: date
    vigencia_fim:    Optional[date] = None

class FaixaOut(FaixaCreate):
    id:        int
    ativo:     bool
    criado_em: datetime
    model_config = {"from_attributes": True}


# ==================================================================
# VOLUMETRIA DA FATURA (recebida via integração de folha)
# ==================================================================

class VolumetriaInput(BaseModel):
    contrato_item_id:  UUID
    tipo_vinculo:      TipoVinculoFolha
    quantidade:        int = Field(..., ge=0)
    competencia_folha: Optional[date] = None
    fonte:             str = "INTEGRACAO_FOLHA"

class VolumetriaOut(BaseModel):
    id:               UUID
    tipo_vinculo:     TipoVinculoFolha
    quantidade:       int
    valor_unitario:   Decimal
    valor_total:      Decimal
    fonte:            str
    model_config = {"from_attributes": True}


# ==================================================================
# ITEM DA FATURA
# ==================================================================

class FaturaItemOut(BaseModel):
    id:               UUID
    contrato_item_id: UUID
    produto_id:       int
    descricao:        str
    quantidade:       Decimal
    valor_unitario:   Decimal
    desconto_pct:     Decimal
    valor_total:      Decimal
    eh_volumetria:    bool
    observacoes:      Optional[str]
    model_config = {"from_attributes": True}


# ==================================================================
# DOCUMENTO DA FATURA
# ==================================================================

class DocumentoOut(BaseModel):
    id:              UUID
    tipo:            TipoDocumentoFat
    status:          StatusDocumento
    numero:          Optional[str]
    url:             Optional[str]
    mensagem_erro:   Optional[str]
    emitido_em:      Optional[datetime]
    model_config = {"from_attributes": True}


# ==================================================================
# FATURA
# ==================================================================

class FaturaApurarRequest(BaseModel):
    """Solicita apuração de faturas para uma data de apuração e competência."""
    dia_apuracao:    str   = Field(..., description="DIA_01 | DIA_15 | DIA_25")
    competencia:     date  = Field(..., description="Mês de referência — usar o 1º dia do mês")
    data_apuracao:   date  = Field(..., description="Data real da apuração")
    data_vencimento: date

class FaturaRegistrarPagamento(BaseModel):
    valor_pago:      Decimal = Field(..., gt=0)
    data_pagamento:  date
    observacoes:     Optional[str] = None

class FaturaRegistrarNF(BaseModel):
    numero_nf:          str
    serie_nf:           Optional[str] = None
    codigo_verificacao: Optional[str] = None
    data_emissao_nf:    date

class FaturaOut(BaseModel):
    id:                 UUID
    numero_fatura:      str
    contrato_id:        UUID
    competencia:        date
    dia_apuracao:       str
    data_apuracao:      date
    data_vencimento:    date
    status:             StatusFatura
    valor_servicos:     Decimal
    valor_volumetria:   Decimal
    valor_total:        Decimal
    valor_pago:         Optional[Decimal]
    data_pagamento:     Optional[date]
    descricao_nf:       Optional[str]
    numero_nf:          Optional[str]
    data_emissao_nf:    Optional[date]
    observacoes:        Optional[str]
    criado_em:          datetime
    itens:              list[FaturaItemOut]    = []
    volumetrias:        list[VolumetriaOut]    = []
    documentos:         list[DocumentoOut]     = []
    model_config = {"from_attributes": True}

class FaturaResumoOut(BaseModel):
    id:                 UUID
    numero_fatura:      str
    contrato_id:        UUID
    contrato_numero:    str
    cliente_nome:       str
    modalidade:         str
    competencia:        date
    dia_apuracao:       str
    data_vencimento:    date
    status:             StatusFatura
    valor_servicos:     Decimal
    valor_volumetria:   Decimal
    valor_total:        Decimal
    numero_nf:          Optional[str]
    docs_emitidos:      int
    dias_atraso:        int
    criado_em:          datetime
    model_config = {"from_attributes": True}

class FaturaListOut(BaseModel):
    dados: list[FaturaResumoOut]
    meta:  dict

class ApuracaoResultado(BaseModel):
    """Resultado da apuração em lote."""
    competencia:        date
    dia_apuracao:       str
    faturas_criadas:    int
    faturas_existentes: int
    valor_total:        Decimal
    faturas:            list[FaturaResumoOut] = []
