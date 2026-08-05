// src/components/clientes/ClienteForm.jsx
"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { clienteService } from "../../services/clienteService";
import { useSegmentos } from "../../hooks/useClientes";
import { UFS, PORTE_LABEL } from "../../utils/formatters";

const ABA = { DADOS: "dados", ENDERECOS: "enderecos", CONTATOS: "contatos" };

// ------------------------------------------------------------------
// Formulário principal
// ------------------------------------------------------------------
export default function ClienteForm({ clienteInicial = null }) {
  const router  = useRouter();
  const isEdicao = !!clienteInicial;
  const segmentos = useSegmentos();

  const [aba, setAba]         = useState(ABA.DADOS);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro]       = useState(null);
  const [sucesso, setSucesso] = useState(null);

  // Dados do cliente
  const [dados, setDados] = useState({
    tipo_pessoa:         clienteInicial?.tipo_pessoa   ?? "PJ",
    razao_social:        clienteInicial?.razao_social  ?? "",
    nome_fantasia:       clienteInicial?.nome_fantasia ?? "",
    cnpj:                clienteInicial?.cnpj          ?? "",
    inscricao_estadual:  clienteInicial?.inscricao_estadual  ?? "",
    inscricao_municipal: clienteInicial?.inscricao_municipal ?? "",
    nome_completo:       clienteInicial?.nome_completo ?? "",
    cpf:                 clienteInicial?.cpf           ?? "",
    segmento_id:         clienteInicial?.segmento_id   ?? "",
    porte:               clienteInicial?.porte         ?? "",
    origem:              clienteInicial?.origem        ?? "",
    observacoes:         clienteInicial?.observacoes   ?? "",
  });

  // Endereços (lista)
  const [enderecos, setEnderecos] = useState(
    clienteInicial?.enderecos?.length
      ? clienteInicial.enderecos
      : [enderecoVazio()]
  );

  // Contatos (lista)
  const [contatos, setContatos] = useState(
    clienteInicial?.contatos?.length
      ? clienteInicial.contatos
      : [contatoVazio()]
  );

  // -----------------------------------------------------------------
  const set = (campo) => (e) => setDados((d) => ({ ...d, [campo]: e.target.value }));

  const handleSubmit = async () => {
    setSalvando(true);
    setErro(null);
    try {
      const payload = {
        ...dados,
        tipo_pessoa: dados.tipo_pessoa,
        segmento_id: dados.segmento_id ? Number(dados.segmento_id) : null,
        cnpj:        dados.tipo_pessoa === "PJ" ? dados.cnpj.replace(/\D/g, "") : undefined,
        cpf:         dados.tipo_pessoa === "PF" ? dados.cpf.replace(/\D/g, "")  : undefined,
        enderecos:   enderecos.filter((e) => e.logradouro).map((e) => ({ ...e, cep: e.cep.replace(/\D/g, "") })),
        contatos:    contatos.filter((c) => c.nome),
      };

      if (isEdicao) {
        await clienteService.atualizar(clienteInicial.id, payload);
        setSucesso("Cliente atualizado com sucesso.");
      } else {
        const novo = await clienteService.criar(payload);
        setSucesso("Cliente criado com sucesso.");
        setTimeout(() => router.push(`/clientes/${novo.id}`), 1200);
      }
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  };

  const isPJ = dados.tipo_pessoa === "PJ";

  return (
    <div style={{ padding: "2rem", maxWidth: 860, margin: "0 auto" }}>

      {/* Cabeçalho */}
      <div style={{ marginBottom: "1.5rem" }}>
        <button onClick={() => router.back()} style={btnVoltarStyle}>← Voltar</button>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: "12px 0 4px", color: "#111827" }}>
          {isEdicao ? "Editar cliente" : "Novo cliente"}
        </h1>
      </div>

      {/* Abas */}
      <div style={{ display: "flex", borderBottom: "2px solid #E5E7EB", marginBottom: "1.5rem" }}>
        {[
          { id: ABA.DADOS,      label: "Dados cadastrais" },
          { id: ABA.ENDERECOS,  label: `Endereços (${enderecos.length})` },
          { id: ABA.CONTATOS,   label: `Contatos (${contatos.length})` },
        ].map((a) => (
          <button
            key={a.id}
            onClick={() => setAba(a.id)}
            style={{
              padding: "8px 18px", border: "none", background: "none",
              fontSize: 14, fontWeight: aba === a.id ? 600 : 400,
              color: aba === a.id ? "#1E40AF" : "#6B7280",
              borderBottom: aba === a.id ? "2px solid #1E40AF" : "2px solid transparent",
              cursor: "pointer", marginBottom: -2,
            }}
          >
            {a.label}
          </button>
        ))}
      </div>

      {/* Alertas */}
      {erro    && <div style={alertaStyle("#FEE2E2", "#B91C1C")}>{erro}</div>}
      {sucesso && <div style={alertaStyle("#DCFCE7", "#15803D")}>{sucesso}</div>}

      {/* ABA: Dados cadastrais */}
      {aba === ABA.DADOS && (
        <div style={cardStyle}>
          <Secao titulo="Tipo de pessoa">
            <div style={{ display: "flex", gap: 12 }}>
              {["PJ", "PF"].map((t) => (
                <label key={t} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 14 }}>
                  <input
                    type="radio" name="tipo_pessoa" value={t}
                    checked={dados.tipo_pessoa === t}
                    onChange={set("tipo_pessoa")}
                  />
                  {t === "PJ" ? "🏢 Pessoa Jurídica" : "👤 Pessoa Física"}
                </label>
              ))}
            </div>
          </Secao>

          {isPJ ? (
            <>
              <Secao titulo="Identificação">
                <Grade cols={2}>
                  <Campo label="Razão social *" value={dados.razao_social} onChange={set("razao_social")} />
                  <Campo label="Nome fantasia"  value={dados.nome_fantasia} onChange={set("nome_fantasia")} />
                </Grade>
                <Grade cols={3}>
                  <Campo label="CNPJ *" value={dados.cnpj} onChange={set("cnpj")} placeholder="00.000.000/0001-00" mascara={maskCNPJ} />
                  <Campo label="Insc. estadual"  value={dados.inscricao_estadual}  onChange={set("inscricao_estadual")} />
                  <Campo label="Insc. municipal" value={dados.inscricao_municipal} onChange={set("inscricao_municipal")} />
                </Grade>
              </Secao>
            </>
          ) : (
            <Secao titulo="Identificação">
              <Grade cols={2}>
                <Campo label="Nome completo *" value={dados.nome_completo} onChange={set("nome_completo")} />
                <Campo label="CPF *" value={dados.cpf} onChange={set("cpf")} placeholder="000.000.000-00" mascara={maskCPF} />
              </Grade>
            </Secao>
          )}

          <Secao titulo="Classificação">
            <Grade cols={3}>
              <div>
                <label style={labelStyle}>Segmento</label>
                <select value={dados.segmento_id} onChange={set("segmento_id")} style={selectStyle}>
                  <option value="">Selecione...</option>
                  {segmentos.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Porte</label>
                <select value={dados.porte} onChange={set("porte")} style={selectStyle}>
                  <option value="">Selecione...</option>
                  {Object.entries(PORTE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <Campo label="Origem" value={dados.origem} onChange={set("origem")} placeholder="Ex: indicação, site..." />
            </Grade>
          </Secao>

          <Secao titulo="Observações">
            <textarea
              value={dados.observacoes}
              onChange={set("observacoes")}
              rows={3}
              placeholder="Informações adicionais sobre o cliente..."
              style={{ ...inputStyle, width: "100%", resize: "vertical" }}
            />
          </Secao>
        </div>
      )}

      {/* ABA: Endereços */}
      {aba === ABA.ENDERECOS && (
        <div>
          {enderecos.map((end, i) => (
            <EnderecoForm
              key={i}
              index={i}
              dados={end}
              onChange={(campo, val) => {
                const novo = [...enderecos];
                novo[i] = { ...novo[i], [campo]: val };
                setEnderecos(novo);
              }}
              onRemover={enderecos.length > 1 ? () => setEnderecos(enderecos.filter((_, j) => j !== i)) : null}
              clienteId={clienteInicial?.id}
            />
          ))}
          <button
            onClick={() => setEnderecos([...enderecos, enderecoVazio()])}
            style={btnAddStyle}
          >
            + Adicionar endereço
          </button>
        </div>
      )}

      {/* ABA: Contatos */}
      {aba === ABA.CONTATOS && (
        <div>
          {contatos.map((con, i) => (
            <ContatoForm
              key={i}
              index={i}
              dados={con}
              onChange={(campo, val) => {
                const novo = [...contatos];
                novo[i] = { ...novo[i], [campo]: val };
                setContatos(novo);
              }}
              onRemover={contatos.length > 1 ? () => setContatos(contatos.filter((_, j) => j !== i)) : null}
            />
          ))}
          <button
            onClick={() => setContatos([...contatos, contatoVazio()])}
            style={btnAddStyle}
          >
            + Adicionar contato
          </button>
        </div>
      )}

      {/* Rodapé de ação */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: "1.5rem" }}>
        <button onClick={() => router.back()} style={btnSecStyle}>Cancelar</button>
        <button onClick={handleSubmit} disabled={salvando} style={btnPrimStyle}>
          {salvando ? "Salvando..." : isEdicao ? "Salvar alterações" : "Cadastrar cliente"}
        </button>
      </div>
    </div>
  );
}


// ------------------------------------------------------------------
// Sub-componente: Endereço
// ------------------------------------------------------------------
function EnderecoForm({ index, dados, onChange, onRemover, clienteId }) {
  const [buscandoCep, setBuscandoCep] = useState(false);

  const handleCep = async (e) => {
    const val = e.target.value;
    onChange("cep", val);
    const d = val.replace(/\D/g, "");
    if (d.length === 8) {
      setBuscandoCep(true);
      try {
        const res = await clienteService.consultarCep(d);
        onChange("logradouro", res.logradouro || "");
        onChange("bairro",     res.bairro     || "");
        onChange("cidade",     res.cidade     || "");
        onChange("uf",         res.uf         || "");
        onChange("ibge_codigo",res.ibge       || "");
      } catch {}
      setBuscandoCep(false);
    }
  };

  return (
    <div style={{ ...cardStyle, marginBottom: 16, position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <strong style={{ fontSize: 14, color: "#374151" }}>Endereço {index + 1}</strong>
        {onRemover && (
          <button onClick={onRemover} style={{ background: "none", border: "none", color: "#EF4444", cursor: "pointer", fontSize: 13 }}>
            Remover
          </button>
        )}
      </div>

      <Grade cols={3}>
        <div>
          <label style={labelStyle}>Tipo</label>
          <select value={dados.tipo} onChange={(e) => onChange("tipo", e.target.value)} style={selectStyle}>
            <option value="MATRIZ">Matriz</option>
            <option value="FILIAL">Filial</option>
            <option value="COBRANCA">Cobrança</option>
            <option value="ENTREGA">Entrega</option>
          </select>
        </div>
        <div>
          <label style={labelStyle}>CEP *{buscandoCep && " (buscando...)"}</label>
          <input value={dados.cep} onChange={handleCep} placeholder="00000-000" style={inputStyle} maxLength={9} />
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14, cursor: "pointer", paddingTop: 22 }}>
          <input type="checkbox" checked={dados.principal} onChange={(e) => onChange("principal", e.target.checked)} />
          Endereço principal
        </label>
      </Grade>

      <Grade cols={2}>
        <Campo label="Logradouro *" value={dados.logradouro} onChange={(e) => onChange("logradouro", e.target.value)} />
        <Grade cols={2}>
          <Campo label="Número *"      value={dados.numero}      onChange={(e) => onChange("numero", e.target.value)} />
          <Campo label="Complemento"   value={dados.complemento} onChange={(e) => onChange("complemento", e.target.value)} />
        </Grade>
      </Grade>

      <Grade cols={3}>
        <Campo label="Bairro *"  value={dados.bairro}  onChange={(e) => onChange("bairro", e.target.value)} />
        <Campo label="Cidade *"  value={dados.cidade}  onChange={(e) => onChange("cidade", e.target.value)} />
        <div>
          <label style={labelStyle}>UF *</label>
          <select value={dados.uf} onChange={(e) => onChange("uf", e.target.value)} style={selectStyle}>
            <option value="">UF</option>
            {UFS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
          </select>
        </div>
      </Grade>
    </div>
  );
}


// ------------------------------------------------------------------
// Sub-componente: Contato
// ------------------------------------------------------------------
function ContatoForm({ index, dados, onChange, onRemover }) {
  return (
    <div style={{ ...cardStyle, marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <strong style={{ fontSize: 14, color: "#374151" }}>Contato {index + 1}</strong>
        {onRemover && (
          <button onClick={onRemover} style={{ background: "none", border: "none", color: "#EF4444", cursor: "pointer", fontSize: 13 }}>
            Remover
          </button>
        )}
      </div>

      <Grade cols={2}>
        <Campo label="Nome *"       value={dados.nome}        onChange={(e) => onChange("nome", e.target.value)} />
        <Campo label="Cargo"        value={dados.cargo}       onChange={(e) => onChange("cargo", e.target.value)} />
        <Campo label="Departamento" value={dados.departamento} onChange={(e) => onChange("departamento", e.target.value)} />
        <Campo label="E-mail"       value={dados.email}       onChange={(e) => onChange("email", e.target.value)} type="email" />
        <Campo label="Telefone"     value={dados.telefone}    onChange={(e) => onChange("telefone", e.target.value)} />
        <Campo label="WhatsApp"     value={dados.whatsapp}    onChange={(e) => onChange("whatsapp", e.target.value)} />
      </Grade>

      <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 16 }}>
        {[
          { key: "is_financeiro", label: "💰 Financeiro" },
          { key: "is_contrato",   label: "📋 Contratos"  },
          { key: "is_tecnico",    label: "🔧 Técnico"    },
          { key: "is_comercial",  label: "🤝 Comercial"  },
          { key: "principal",     label: "⭐ Principal"  },
        ].map(({ key, label }) => (
          <label key={key} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 13, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={dados[key] || false}
              onChange={(e) => onChange(key, e.target.checked)}
            />
            {label}
          </label>
        ))}
      </div>
    </div>
  );
}


// ------------------------------------------------------------------
// Componentes auxiliares de layout
// ------------------------------------------------------------------
function Secao({ titulo, children }) {
  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <h3 style={{ fontSize: 13, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 12px" }}>
        {titulo}
      </h3>
      {children}
    </div>
  );
}

function Grade({ cols, children }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 12, marginBottom: 12 }}>
      {children}
    </div>
  );
}

function Campo({ label, value, onChange, placeholder = "", type = "text", mascara }) {
  const handleChange = (e) => {
    if (mascara) {
      e.target.value = mascara(e.target.value);
    }
    onChange(e);
  };
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input type={type} value={value || ""} onChange={handleChange} placeholder={placeholder} style={inputStyle} />
    </div>
  );
}

// ------------------------------------------------------------------
// Máscaras
// ------------------------------------------------------------------
const maskCNPJ = (v) => v.replace(/\D/g,"").slice(0,14)
  .replace(/^(\d{2})(\d)/,      "$1.$2")
  .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
  .replace(/\.(\d{3})(\d)/,     ".$1/$2")
  .replace(/(\d{4})(\d)/,       "$1-$2");

const maskCPF = (v) => v.replace(/\D/g,"").slice(0,11)
  .replace(/(\d{3})(\d)/,       "$1.$2")
  .replace(/(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
  .replace(/\.(\d{3})(\d)/,     ".$1-$2");

// ------------------------------------------------------------------
// Valores vazios
// ------------------------------------------------------------------
function enderecoVazio() {
  return { tipo: "MATRIZ", principal: true, cep: "", logradouro: "", numero: "", complemento: "", bairro: "", cidade: "", uf: "", ibge_codigo: "" };
}
function contatoVazio() {
  return { nome: "", cargo: "", departamento: "", email: "", telefone: "", whatsapp: "", is_financeiro: false, is_contrato: false, is_tecnico: false, is_comercial: false, principal: false };
}

// ------------------------------------------------------------------
// Estilos
// ------------------------------------------------------------------
const cardStyle = { background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1.25rem" };
const inputStyle = { padding: "7px 11px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 14, width: "100%", boxSizing: "border-box", color: "#111827" };
const selectStyle = { ...inputStyle };
const labelStyle  = { display: "block", fontSize: 12, fontWeight: 500, color: "#374151", marginBottom: 4 };
const btnPrimStyle = { padding: "9px 22px", background: "#1E40AF", color: "#fff", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 500, cursor: "pointer" };
const btnSecStyle  = { padding: "9px 18px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 14, cursor: "pointer" };
const btnVoltarStyle = { background: "none", border: "none", color: "#6B7280", fontSize: 13, cursor: "pointer", padding: 0 };
const btnAddStyle  = { marginTop: 8, padding: "8px 16px", background: "#EFF6FF", color: "#1E40AF", border: "1px dashed #93C5FD", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const alertaStyle  = (bg, color) => ({ padding: "10px 16px", borderRadius: 8, fontSize: 14, marginBottom: 16, background: bg, color });
