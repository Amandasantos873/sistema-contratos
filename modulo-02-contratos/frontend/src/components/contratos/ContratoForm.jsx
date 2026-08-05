// src/components/contratos/ContratoForm.jsx
"use client";
import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { contratoService } from "../../services/contratoService";
import { clienteService } from "../../services/clienteService";

const fmtMoeda = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function ContratoForm() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const clienteIdUrl = searchParams.get("cliente_id");

  const [aba, setAba]         = useState("geral");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro]       = useState(null);
  const [produtos, setProdutos] = useState([]);
  const [clientes, setClientes] = useState([]);

  const [form, setForm] = useState({
    cliente_id:              clienteIdUrl || "",
    modalidade:              "ASP",
    data_assinatura:         "",
    data_inicio_impl:        "",
    prazo_meses:             12,
    dia_faturamento:         "DIA_25",
    responsavel_comercial:   "",
    responsavel_implantacao: "",
    numero_proposta:         "",
    observacoes:             "",
  });

  const [itens, setItens]         = useState([]);
  const [parcelas, setParcelas]   = useState([{ numero_parcela: 1, valor: "", data_vencimento: "" }]);

  // Carrega produtos ao mudar modalidade
  useEffect(() => {
    if (form.modalidade) {
      contratoService.produtos(form.modalidade).then(setProdutos).catch(() => {});
    }
  }, [form.modalidade]);

  // Carrega clientes para o select
  useEffect(() => {
    clienteService.listar({ status: "ATIVO", por_pagina: 100 })
      .then((r) => setClientes(r.dados))
      .catch(() => {});
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const totalImpl   = parcelas.reduce((a, p) => a + (parseFloat(p.valor) || 0), 0);
  const totalMensal = itens.filter(i => i.fase === "RECORRENCIA")
    .reduce((a, i) => a + (parseFloat(i.quantidade || 1) * parseFloat(i.valor_unitario || 0) * (1 - parseFloat(i.desconto_pct || 0) / 100)), 0);

  const handleSubmit = async () => {
    setSalvando(true);
    setErro(null);
    try {
      const payload = {
        ...form,
        prazo_meses: parseInt(form.prazo_meses),
        itens: itens.map(i => ({
          produto_id:     parseInt(i.produto_id),
          quantidade:     parseFloat(i.quantidade || 1),
          valor_unitario: parseFloat(i.valor_unitario),
          desconto_pct:   parseFloat(i.desconto_pct || 0),
          fase:           i.fase,
        })),
        parcelas_impl: parcelas.filter(p => p.valor && p.data_vencimento).map(p => ({
          numero_parcela:  p.numero_parcela,
          valor:           parseFloat(p.valor),
          data_vencimento: p.data_vencimento,
        })),
      };
      const novo = await contratoService.criar(payload);
      router.push(`/contratos/${novo.id}`);
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  };

  const addItem = (fase) => setItens([...itens, { produto_id: "", quantidade: 1, valor_unitario: "", desconto_pct: 0, fase }]);
  const addParcela = () => setParcelas([...parcelas, { numero_parcela: parcelas.length + 1, valor: "", data_vencimento: "" }]);

  return (
    <div style={{ padding: "2rem", maxWidth: 880, margin: "0 auto" }}>
      <button onClick={() => router.back()} style={btnVoltarStyle}>← Voltar</button>
      <h1 style={{ fontSize: 20, fontWeight: 600, margin: "12px 0 4px", color: "#111827" }}>Novo contrato</h1>

      {/* Resumo financeiro flutuante */}
      <div style={{ display: "flex", gap: 12, marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {[
          { label: "Total implantação", valor: totalImpl },
          { label: "Mensalidade", valor: totalMensal },
        ].map(({ label, valor }) => (
          <div key={label} style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "12px 20px", minWidth: 180 }}>
            <p style={{ margin: 0, fontSize: 12, color: "#9CA3AF" }}>{label}</p>
            <p style={{ margin: "3px 0 0", fontSize: 18, fontWeight: 600, color: "#111827", fontFamily: "monospace" }}>
              {fmtMoeda(valor)}
            </p>
          </div>
        ))}
      </div>

      {/* Abas */}
      <div style={{ display: "flex", borderBottom: "2px solid #E5E7EB", marginBottom: "1.5rem" }}>
        {[
          { id: "geral",     label: "Dados gerais" },
          { id: "itens",     label: `Itens (${itens.length})` },
          { id: "parcelas",  label: `Parcelas de implantação (${parcelas.length})` },
        ].map((a) => (
          <button key={a.id} onClick={() => setAba(a.id)} style={{
            padding: "8px 18px", border: "none", background: "none", fontSize: 14,
            fontWeight: aba === a.id ? 600 : 400,
            color: aba === a.id ? "#1E40AF" : "#6B7280",
            borderBottom: aba === a.id ? "2px solid #1E40AF" : "2px solid transparent",
            cursor: "pointer", marginBottom: -2,
          }}>{a.label}</button>
        ))}
      </div>

      {erro && <div style={alertStyle}>{erro}</div>}

      {/* ABA: Dados gerais */}
      {aba === "geral" && (
        <div style={cardStyle}>
          <Grade cols={2}>
            <div>
              <Label>Cliente *</Label>
              <select value={form.cliente_id} onChange={set("cliente_id")} style={inputStyle}>
                <option value="">Selecione o cliente...</option>
                {clientes.map(c => <option key={c.id} value={c.id}>{c.nome_principal}</option>)}
              </select>
            </div>
            <div>
              <Label>Modalidade *</Label>
              <select value={form.modalidade} onChange={set("modalidade")} style={inputStyle}>
                <option value="ASP">ASP</option>
                <option value="BSP">BSP</option>
                <option value="BPO">BPO</option>
              </select>
            </div>
          </Grade>
          <Grade cols={3}>
            <Campo label="Data de assinatura *" value={form.data_assinatura} onChange={set("data_assinatura")} type="date" />
            <Campo label="Início da implantação *" value={form.data_inicio_impl} onChange={set("data_inicio_impl")} type="date" />
            <div>
              <Label>Prazo (meses) *</Label>
              <select value={form.prazo_meses} onChange={set("prazo_meses")} style={inputStyle}>
                {[6,12,18,24,36,48,60].map(m => <option key={m} value={m}>{m} meses</option>)}
              </select>
            </div>
          </Grade>
          <Grade cols={2}>
            <div>
              <Label>Dia de faturamento *</Label>
              <select value={form.dia_faturamento} onChange={set("dia_faturamento")} style={inputStyle}>
                <option value="DIA_01">1º dia útil do mês</option>
                <option value="DIA_15">Dia 15</option>
                <option value="DIA_25">Dia 25 (maior volume)</option>
              </select>
            </div>
            <Campo label="Nº da proposta" value={form.numero_proposta} onChange={set("numero_proposta")} />
          </Grade>
          <Grade cols={2}>
            <Campo label="Responsável comercial"   value={form.responsavel_comercial}   onChange={set("responsavel_comercial")} />
            <Campo label="Responsável implantação" value={form.responsavel_implantacao} onChange={set("responsavel_implantacao")} />
          </Grade>
          <div>
            <Label>Observações</Label>
            <textarea value={form.observacoes} onChange={set("observacoes")} rows={3}
              style={{ ...inputStyle, resize: "vertical" }} />
          </div>
        </div>
      )}

      {/* ABA: Itens */}
      {aba === "itens" && (
        <div>
          {["IMPLANTACAO", "RECORRENCIA"].map(fase => (
            <div key={fase} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 10px" }}>
                {fase === "IMPLANTACAO" ? "🔧 Itens de implantação" : "🔄 Itens recorrentes"}
              </h3>
              {itens.filter(i => i.fase === fase).map((item, idx) => {
                const globalIdx = itens.findIndex((it, i) => it === item);
                const prod = produtos.find(p => p.id === parseInt(item.produto_id));
                const total = (parseFloat(item.quantidade || 1) * parseFloat(item.valor_unitario || 0) * (1 - parseFloat(item.desconto_pct || 0) / 100));
                return (
                  <div key={globalIdx} style={{ ...cardStyle, marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: "#374151" }}>Item {idx + 1}</span>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span style={{ fontSize: 13, fontFamily: "monospace", fontWeight: 500, color: "#1E40AF" }}>{fmtMoeda(total)}</span>
                        <button onClick={() => setItens(itens.filter((_, j) => j !== globalIdx))}
                          style={{ background: "none", border: "none", color: "#EF4444", cursor: "pointer", fontSize: 12 }}>Remover</button>
                      </div>
                    </div>
                    <Grade cols={4}>
                      <div style={{ gridColumn: "span 2" }}>
                        <Label>Produto/Serviço</Label>
                        <select value={item.produto_id}
                          onChange={(e) => { const n=[...itens]; n[globalIdx]={...n[globalIdx],produto_id:e.target.value}; setItens(n); }}
                          style={inputStyle}>
                          <option value="">Selecione...</option>
                          {produtos.filter(p => fase === "IMPLANTACAO" ? p.permite_impl : p.permite_recorr)
                            .map(p => <option key={p.id} value={p.id}>{p.nome} ({p.unidade})</option>)}
                        </select>
                      </div>
                      <div>
                        <Label>Qtd</Label>
                        <input type="number" min="0.001" step="0.001" value={item.quantidade}
                          onChange={(e) => { const n=[...itens]; n[globalIdx]={...n[globalIdx],quantidade:e.target.value}; setItens(n); }}
                          style={inputStyle} />
                      </div>
                      <div>
                        <Label>Valor unit. (R$)</Label>
                        <input type="number" min="0" step="0.01" value={item.valor_unitario}
                          onChange={(e) => { const n=[...itens]; n[globalIdx]={...n[globalIdx],valor_unitario:e.target.value}; setItens(n); }}
                          style={inputStyle} />
                      </div>
                    </Grade>
                  </div>
                );
              })}
              <button onClick={() => addItem(fase)} style={btnAddStyle}>+ Adicionar item {fase === "IMPLANTACAO" ? "de implantação" : "recorrente"}</button>
            </div>
          ))}
        </div>
      )}

      {/* ABA: Parcelas */}
      {aba === "parcelas" && (
        <div>
          <p style={{ fontSize: 13, color: "#6B7280", marginBottom: 16 }}>
            Defina as parcelas conforme negociado. Os valores são livres — não precisam ser iguais ao total de implantação.
          </p>
          {parcelas.map((p, i) => (
            <div key={i} style={{ ...cardStyle, marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: "#374151" }}>Parcela {p.numero_parcela}</span>
                {parcelas.length > 1 && (
                  <button onClick={() => setParcelas(parcelas.filter((_, j) => j !== i).map((x, j) => ({ ...x, numero_parcela: j + 1 })))}
                    style={{ background: "none", border: "none", color: "#EF4444", cursor: "pointer", fontSize: 12 }}>Remover</button>
                )}
              </div>
              <Grade cols={2}>
                <Campo label="Valor (R$)" value={p.valor} type="number"
                  onChange={(e) => { const n=[...parcelas]; n[i]={...n[i],valor:e.target.value}; setParcelas(n); }} />
                <Campo label="Vencimento" value={p.data_vencimento} type="date"
                  onChange={(e) => { const n=[...parcelas]; n[i]={...n[i],data_vencimento:e.target.value}; setParcelas(n); }} />
              </Grade>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
            <button onClick={addParcela} style={btnAddStyle}>+ Adicionar parcela</button>
            <span style={{ fontSize: 14, fontWeight: 500, color: "#111827" }}>
              Total: {fmtMoeda(totalImpl)}
            </span>
          </div>
        </div>
      )}

      {/* Rodapé */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: "1.5rem" }}>
        <button onClick={() => router.back()} style={btnSecStyle}>Cancelar</button>
        <button onClick={handleSubmit} disabled={salvando} style={btnPrimStyle}>
          {salvando ? "Salvando..." : "Criar contrato"}
        </button>
      </div>
    </div>
  );
}

// Auxiliares
function Campo({ label, value, onChange, type = "text", placeholder = "" }) {
  return (
    <div>
      <Label>{label}</Label>
      <input type={type} value={value || ""} onChange={onChange} placeholder={placeholder} style={inputStyle} />
    </div>
  );
}
function Grade({ cols, children }) {
  return <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 12, marginBottom: 12 }}>{children}</div>;
}
function Label({ children }) {
  return <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#374151", marginBottom: 4 }}>{children}</label>;
}

const cardStyle     = { background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1.25rem" };
const inputStyle    = { padding: "7px 11px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 14, width: "100%", boxSizing: "border-box", color: "#111827" };
const btnPrimStyle  = { padding: "9px 22px", background: "#1E40AF", color: "#fff", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 500, cursor: "pointer" };
const btnSecStyle   = { padding: "9px 18px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 14, cursor: "pointer" };
const btnVoltarStyle= { background: "none", border: "none", color: "#6B7280", fontSize: 13, cursor: "pointer", padding: 0 };
const btnAddStyle   = { padding: "7px 14px", background: "#EFF6FF", color: "#1E40AF", border: "1px dashed #93C5FD", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const alertStyle    = { padding: "10px 16px", borderRadius: 8, fontSize: 14, marginBottom: 16, background: "#FEE2E2", color: "#B91C1C" };
