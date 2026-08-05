"""
Testes do módulo de clientes.
Execute com: pytest tests/ -v
"""
import pytest
from app.schemas.cliente import ClienteCreate, EnderecoCreate, ContatoCreate
from app.models.cliente import TipoPessoa


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def make_cliente_pj(**kwargs):
    base = dict(
        tipo_pessoa   = TipoPessoa.PJ,
        razao_social  = "Empresa Teste LTDA",
        nome_fantasia = "Empresa Teste",
        cnpj          = "11222333000181",  # CNPJ válido para testes
        segmento_id   = None,
        contatos      = [
            ContatoCreate(
                nome          = "João Silva",
                cargo         = "Diretor Financeiro",
                email         = "joao@empresateste.com.br",
                is_financeiro = True,
                principal     = True,
            )
        ],
        enderecos = [
            EnderecoCreate(
                tipo       = "MATRIZ",
                principal  = True,
                cep        = "01310100",
                logradouro = "Avenida Paulista",
                numero     = "1000",
                bairro     = "Bela Vista",
                cidade     = "São Paulo",
                uf         = "SP",
            )
        ],
    )
    base.update(kwargs)
    return ClienteCreate(**base)


def make_cliente_pf(**kwargs):
    base = dict(
        tipo_pessoa   = TipoPessoa.PF,
        nome_completo = "Maria Oliveira",
        cpf           = "52998224725",  # CPF válido para testes
        contatos      = [
            ContatoCreate(
                nome          = "Maria Oliveira",
                telefone      = "11999990000",
                is_financeiro = True,
                principal     = True,
            )
        ],
        enderecos = [],
    )
    base.update(kwargs)
    return ClienteCreate(**base)


# ------------------------------------------------------------------
# Validação de CNPJ/CPF
# ------------------------------------------------------------------

class TestValidacaoDocumentos:

    def test_cnpj_valido(self):
        c = make_cliente_pj(cnpj="11222333000181")
        assert c.cnpj == "11222333000181"

    def test_cnpj_invalido_levanta_erro(self):
        with pytest.raises(Exception, match="CNPJ inválido"):
            make_cliente_pj(cnpj="00000000000000")

    def test_cnpj_com_mascara_e_normalizado(self):
        c = make_cliente_pj(cnpj="11.222.333/0001-81")
        assert c.cnpj == "11222333000181"

    def test_cpf_valido(self):
        c = make_cliente_pf(cpf="52998224725")
        assert c.cpf == "52998224725"

    def test_cpf_invalido_levanta_erro(self):
        with pytest.raises(Exception, match="CPF inválido"):
            make_cliente_pf(cpf="11111111111")

    def test_cpf_com_mascara_e_normalizado(self):
        c = make_cliente_pf(cpf="529.982.247-25")
        assert c.cpf == "52998224725"


# ------------------------------------------------------------------
# Validação de campos obrigatórios por tipo de pessoa
# ------------------------------------------------------------------

class TestCamposObrigatorios:

    def test_pj_sem_razao_social_levanta_erro(self):
        with pytest.raises(Exception, match="Razão social"):
            make_cliente_pj(razao_social=None)

    def test_pj_sem_cnpj_levanta_erro(self):
        with pytest.raises(Exception, match="CNPJ"):
            make_cliente_pj(cnpj=None)

    def test_pf_sem_nome_levanta_erro(self):
        with pytest.raises(Exception, match="Nome completo"):
            make_cliente_pf(nome_completo=None)

    def test_pf_sem_cpf_levanta_erro(self):
        with pytest.raises(Exception, match="CPF"):
            make_cliente_pf(cpf=None)


# ------------------------------------------------------------------
# Validação de endereço
# ------------------------------------------------------------------

class TestValidacaoEndereco:

    def test_cep_normalizado(self):
        end = EnderecoCreate(
            cep="01310-100",
            logradouro="Avenida Paulista",
            numero="1000",
            bairro="Bela Vista",
            cidade="São Paulo",
            uf="SP",
        )
        assert end.cep == "01310100"

    def test_uf_invalida_levanta_erro(self):
        with pytest.raises(Exception, match="UF inválida"):
            EnderecoCreate(
                cep="01310100",
                logradouro="Rua X",
                numero="1",
                bairro="Bairro",
                cidade="Cidade",
                uf="XX",
            )

    def test_uf_em_minusculo_e_normalizada(self):
        end = EnderecoCreate(
            cep="01310100",
            logradouro="Rua X",
            numero="1",
            bairro="Bairro",
            cidade="Cidade",
            uf="sp",
        )
        assert end.uf == "SP"


# ------------------------------------------------------------------
# Validação de contato
# ------------------------------------------------------------------

class TestValidacaoContato:

    def test_contato_sem_nenhum_meio_levanta_erro(self):
        with pytest.raises(Exception, match="meio de contato"):
            ContatoCreate(nome="Sem Contato")

    def test_contato_so_email_valido(self):
        c = ContatoCreate(nome="Só Email", email="teste@exemplo.com")
        assert c.email == "teste@exemplo.com"

    def test_email_invalido_levanta_erro(self):
        with pytest.raises(Exception, match="E-mail inválido"):
            ContatoCreate(nome="Email Ruim", email="nao-e-email")
