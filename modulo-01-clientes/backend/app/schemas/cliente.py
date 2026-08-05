from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
import re

from app.models.cliente import (
    TipoPessoa, PorteEmpresa, StatusCliente, TipoEndereco
)


# ==================================================================
# HELPERS DE VALIDAÇÃO
# ==================================================================

def _valida_cnpj(cnpj: str) -> bool:
    """Valida dígitos verificadores do CNPJ."""
    c = re.sub(r"\D", "", cnpj)
    if len(c) != 14 or len(set(c)) == 1:
        return False
    def _calc(c, n):
        s = sum(int(c[i]) * ((n - i) % 9 + 2 if (n - i) % 9 >= 0 else 2) for i in range(n - 1))
        # pesos reais CNPJ
        pesos_cnpj = [5,4,3,2,9,8,7,6,5,4,3,2]
        pesos_cnpj2= [6,5,4,3,2,9,8,7,6,5,4,3,2]
        return 0
    p1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    p2 = [6,5,4,3,2,9,8,7,6,5,4,3,2]
    d1 = sum(int(c[i]) * p1[i] for i in range(12)) % 11
    d1 = 0 if d1 < 2 else 11 - d1
    d2 = sum(int(c[i]) * p2[i] for i in range(13)) % 11
    d2 = 0 if d2 < 2 else 11 - d2
    return int(c[12]) == d1 and int(c[13]) == d2


def _valida_cpf(cpf: str) -> bool:
    """Valida dígitos verificadores do CPF."""
    c = re.sub(r"\D", "", cpf)
    if len(c) != 11 or len(set(c)) == 1:
        return False
    d1 = sum(int(c[i]) * (10 - i) for i in range(9)) % 11
    d1 = 0 if d1 < 2 else 11 - d1
    d2 = sum(int(c[i]) * (11 - i) for i in range(10)) % 11
    d2 = 0 if d2 < 2 else 11 - d2
    return int(c[9]) == d1 and int(c[10]) == d2


def _apenas_digitos(v: str) -> str:
    return re.sub(r"\D", "", v) if v else v


# ==================================================================
# SCHEMAS: ENDEREÇO
# ==================================================================

class EnderecoBase(BaseModel):
    tipo:        TipoEndereco  = TipoEndereco.MATRIZ
    principal:   bool          = False
    cep:         str           = Field(..., min_length=8, max_length=9)
    logradouro:  str           = Field(..., max_length=200)
    numero:      str           = Field(..., max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro:      str           = Field(..., max_length=100)
    cidade:      str           = Field(..., max_length=100)
    uf:          str           = Field(..., min_length=2, max_length=2)
    ibge_codigo: Optional[str] = Field(None, max_length=7)

    @field_validator("cep")
    @classmethod
    def normaliza_cep(cls, v):
        d = _apenas_digitos(v)
        if len(d) != 8:
            raise ValueError("CEP inválido.")
        return d

    @field_validator("uf")
    @classmethod
    def valida_uf(cls, v):
        ufs = {"AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS",
               "MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC",
               "SP","SE","TO"}
        if v.upper() not in ufs:
            raise ValueError("UF inválida.")
        return v.upper()


class EnderecoCreate(EnderecoBase):
    pass

class EnderecoUpdate(BaseModel):
    tipo:        Optional[TipoEndereco] = None
    principal:   Optional[bool]         = None
    cep:         Optional[str]          = None
    logradouro:  Optional[str]          = None
    numero:      Optional[str]          = None
    complemento: Optional[str]          = None
    bairro:      Optional[str]          = None
    cidade:      Optional[str]          = None
    uf:          Optional[str]          = None
    ativo:       Optional[bool]         = None

class EnderecoOut(EnderecoBase):
    id:           UUID
    cliente_id:   UUID
    ativo:        bool
    criado_em:    datetime
    atualizado_em:datetime

    model_config = {"from_attributes": True}


# ==================================================================
# SCHEMAS: CONTATO
# ==================================================================

class ContatoBase(BaseModel):
    nome:          str            = Field(..., max_length=200)
    cargo:         Optional[str]  = Field(None, max_length=100)
    departamento:  Optional[str]  = Field(None, max_length=100)
    email:         Optional[str]  = Field(None, max_length=254)
    telefone:      Optional[str]  = Field(None, max_length=20)
    whatsapp:      Optional[str]  = Field(None, max_length=20)
    linkedin:      Optional[str]  = Field(None, max_length=200)
    is_financeiro: bool           = False
    is_contrato:   bool           = False
    is_tecnico:    bool           = False
    is_comercial:  bool           = False
    principal:     bool           = False
    observacoes:   Optional[str]  = None

    @model_validator(mode="after")
    def valida_meio_contato(self):
        if not any([self.email, self.telefone, self.whatsapp]):
            raise ValueError("Informe ao menos um meio de contato: e-mail, telefone ou WhatsApp.")
        return self

    @field_validator("email")
    @classmethod
    def valida_email(cls, v):
        if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("E-mail inválido.")
        return v


class ContatoCreate(ContatoBase):
    pass

class ContatoUpdate(BaseModel):
    nome:          Optional[str]  = None
    cargo:         Optional[str]  = None
    departamento:  Optional[str]  = None
    email:         Optional[str]  = None
    telefone:      Optional[str]  = None
    whatsapp:      Optional[str]  = None
    linkedin:      Optional[str]  = None
    is_financeiro: Optional[bool] = None
    is_contrato:   Optional[bool] = None
    is_tecnico:    Optional[bool] = None
    is_comercial:  Optional[bool] = None
    principal:     Optional[bool] = None
    ativo:         Optional[bool] = None
    observacoes:   Optional[str]  = None

class ContatoOut(ContatoBase):
    id:            UUID
    cliente_id:    UUID
    ativo:         bool
    criado_em:     datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


# ==================================================================
# SCHEMAS: CLIENTE
# ==================================================================

class ClienteBase(BaseModel):
    tipo_pessoa:         TipoPessoa
    # PJ
    razao_social:        Optional[str] = Field(None, max_length=200)
    nome_fantasia:       Optional[str] = Field(None, max_length=200)
    cnpj:                Optional[str] = None
    inscricao_estadual:  Optional[str] = Field(None, max_length=20)
    inscricao_municipal: Optional[str] = Field(None, max_length=20)
    # PF
    nome_completo:       Optional[str] = Field(None, max_length=200)
    cpf:                 Optional[str] = None
    # Classificação
    segmento_id:         Optional[int] = None
    porte:               Optional[PorteEmpresa] = None
    origem:              Optional[str] = Field(None, max_length=100)
    observacoes:         Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def valida_cnpj(cls, v):
        if v is None:
            return v
        d = _apenas_digitos(v)
        if not _valida_cnpj(d):
            raise ValueError("CNPJ inválido.")
        return d

    @field_validator("cpf")
    @classmethod
    def valida_cpf(cls, v):
        if v is None:
            return v
        d = _apenas_digitos(v)
        if not _valida_cpf(d):
            raise ValueError("CPF inválido.")
        return d

    @model_validator(mode="after")
    def valida_campos_por_tipo(self):
        if self.tipo_pessoa == TipoPessoa.PJ:
            if not self.razao_social:
                raise ValueError("Razão social é obrigatória para Pessoa Jurídica.")
            if not self.cnpj:
                raise ValueError("CNPJ é obrigatório para Pessoa Jurídica.")
        else:
            if not self.nome_completo:
                raise ValueError("Nome completo é obrigatório para Pessoa Física.")
            if not self.cpf:
                raise ValueError("CPF é obrigatório para Pessoa Física.")
        return self


class ClienteCreate(ClienteBase):
    enderecos: list[EnderecoCreate] = Field(default_factory=list)
    contatos:  list[ContatoCreate]  = Field(default_factory=list)

    @model_validator(mode="after")
    def valida_contato_financeiro(self):
        # Ao criar, ao menos um contato com papel financeiro é recomendado
        # (não obrigatório em prospecto, mas alertamos via resposta)
        return self


class ClienteUpdate(BaseModel):
    razao_social:        Optional[str]          = None
    nome_fantasia:       Optional[str]          = None
    inscricao_estadual:  Optional[str]          = None
    inscricao_municipal: Optional[str]          = None
    nome_completo:       Optional[str]          = None
    segmento_id:         Optional[int]          = None
    porte:               Optional[PorteEmpresa] = None
    origem:              Optional[str]          = None
    observacoes:         Optional[str]          = None


class ClienteInativar(BaseModel):
    motivo: str = Field(..., min_length=10, description="Motivo obrigatório para inativação.")


class ClienteOut(ClienteBase):
    id:             UUID
    status:         StatusCliente
    criado_em:      datetime
    atualizado_em:  datetime
    enderecos:      list[EnderecoOut] = []
    contatos:       list[ContatoOut]  = []

    model_config = {"from_attributes": True}


class ClienteResumoOut(BaseModel):
    """Schema leve para listagens — sem endereços/contatos aninhados."""
    id:                UUID
    tipo_pessoa:       TipoPessoa
    nome_principal:    str
    nome_fantasia:     Optional[str]
    documento:         Optional[str]
    segmento:          Optional[str]
    porte:             Optional[PorteEmpresa]
    status:            StatusCliente
    cidade_uf:         Optional[str]
    contato_financeiro:Optional[str]
    email_financeiro:  Optional[str]
    criado_em:         datetime

    model_config = {"from_attributes": True}


# ==================================================================
# SCHEMAS: SEGMENTO
# ==================================================================

class SegmentoOut(BaseModel):
    id:    int
    nome:  str
    ativo: bool

    model_config = {"from_attributes": True}


# ==================================================================
# SCHEMAS: PAGINAÇÃO
# ==================================================================

class PaginacaoMeta(BaseModel):
    total:    int
    pagina:   int
    por_pagina: int
    paginas:  int

class ClienteListOut(BaseModel):
    dados: list[ClienteResumoOut]
    meta:  PaginacaoMeta
