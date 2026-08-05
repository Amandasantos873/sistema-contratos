// src/components/faturamento/FaturamentoPainel.jsx
"use client";
import { useState, useEffect, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const fmtData  = (d) => d ? new Date(d + "T00:00:00").toLocaleDateString("pt-BR") : "—";

const STATUS_COR = {
  RASCUNHO:    { bg: "#F3F4F6", text: "#374151" },
  APURADA:     { bg: "#DBEAFE", text: "#1E40AF" },
  EMITIDA:     { bg: "#EDE9FE", text: "#5B21B6" },
  ENVIADA:     { bg: "#FEF3C7", text: "#92400E" },
  PAGA:        { bg: "#DCFCE7", text: "#15803D" },
  CANCELADA:   { bg: "#F3F4F6", text: "#9CA3AF" },
  INADIMPLENTE:{ bg: "#FEE2E2", text: "#B91C1C" },
};

export default function FaturamentoPainel() {
  const [faturas, setFaturas]   = useState([]);
  const [meta, setMeta]         = useState({ total: 0, paginas: 0, pagina: 1 });
  const [filtros, setFiltros]   = useState({ pagina: 1, por_pagina: 20 });
  const [loading, setLoading]   = useState(false);
  const [erro, setErro]         = useState(null);

  // Modal apuração
  const [modalApurar, setModalApurar] = useState(false);
  const [formApurar, setFormApurar]   = useState({
    dia_apuracao: "DIA_25",
    competencia: "",
    data_apuracao: "",
    data_vencimento: "",
  });
  const [apurando, setApurando]     = useState(false);
  const [resultApuracao, setResultApuracao] = useState(null);

  // Fatura selecionada para detalhe
  const [faturaSel, setFaturaSel] = useState(null);
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);

  // Modal pagamento
  const [modalPagamento, setModalPagamento] = useState(null);
  const [formPagamento, setFormPagamento]   = useState({ valor_pago: "", data_pagamento: "" });

  // Modal NF
  const [modalNF, setModalNF] = useState(null);
  const [formNF, setFormNF]   = useState({ numero_nf: "", data_emissao_nf: "" });
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams();
      Object.entries(filtros).forEach(([k, v]) => v != null && v !== "" && q.append(k, v));
      const res = await api(`/faturas?${q}`);
      setFaturas(res.dados);
      setMeta(res.meta);
    } catch (e) { setErro(e.message); }
    finally { setLoading(false); }
  }, [filtros]);

  useEffect(() => { carregar(); }, [carregar]);

  const verDetalhe = async (fatura) => {
    setLoadingDetalhe(true);
    try {
      const res = await api(`/faturas/${fatura.id}`);
      setFaturaSel(res);
    } catch (e) { setErro(e.message); }
    finally { setLoadingDetalhe(false); }
  };

  const handleApurar = async () => {
    setApurando(true);
    try {
      const res = await api("/faturamento/apurar", {
        method: "POST",
        body: JSON.stringify({
          dia_apuracao:    formApurar.dia_apuracao,
          competencia:     formApurar.competencia + "-01",
          data_apuracao:   formApurar.data_apuracao,
          data_vencimento: formApurar.data_vencimento,
        }),
      });
      setResultApuracao(res);
      carregar();
    } catch (e) { setErro(e.message); }
    finally { setApurando(false); }
  };

  const handlePagamento = async () => {
    setSalvando(true);
    try {
      await api(`/faturas/${modalPagamento.id}/pagamento`, {
        method: "PATCH",
        body: JSON.stringify({ valor_pago: parseFloat(formPagamento.valor_pago), data_pagamento: formPagamento.data_pagamento }),
      });
      setModalPagamento(null);
      carregar();
      if (faturaSel?.id === modalPagamento.id) {
        const res = await api(`/faturas/${modalPagamento.id}`);
        setFaturaSel(res);
      }
    } catch (e) { setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleRegistrarNF = async () => {
    setSalvando(true);
    try {
      await api(`/faturas/${modalNF.id}/nf`, {
        method: "PATCH",
        body: JSON.stringify({ numero_nf: formNF.numero_nf, data_emissao_nf: formNF.data_emissao_nf }),
      });
      setModalNF(null);
      carregar();
    } catch (e) { setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handlePayloadK2 = async (fatura) => {
    try {
      const res = await api(`/faturas/${fatura.id}/payload-k2`);
      const blob = new Blob([JSON.stringify(res.payload, null, 2)], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `k2_${fatura.numero_fatura}.json`; a.click();
    } catch (e) { setErro(e.message); }
  };

  const handleDescritivo = async (fatura) => {
    try {
      const res = await api(`/faturas/${fatura.id}/descritivo`);
      const linhas = [
        `DESCRITIVO DE FATURAMENTO — ${res.numero_fatura}`,
        `Cliente: ${res.cliente} | CNPJ/CPF: ${res.cnpj_cpf}`,
        `Contrato: ${res.contrato} | Modalidade: ${res.modalidade}`,
        `Competência: ${res.competencia} | Vencimento: ${res.data_vencimento}`,
        `NF nº ${res.numero_nf || "Pendente"}`, "",
        "SERVIÇOS:",
        ...res.itens_servico.map(i => `  ${i.descricao.padEnd(40)} Qtd ${i.quantidade}  ${fmtMoeda(i.valor_total)}`),
        res.volumetrias.length > 0 ? "\nVOLUMETRIA FOLHA DE PAGAMENTO:" : "",
        ...res.volumetrias.map(v => `  ${v.tipo_vinculo.padEnd(15)} ${String(v.quantidade).padStart(6)} vínculos  x  ${fmtMoeda(v.valor_unitario)}  = ${fmtMoeda(v.valor_total)}`),
        "", `TOTAL SERVIÇOS:    ${fmtMoeda(res.total_servicos)}`,
        `TOTAL VOLUMETRIA:  ${fmtMoeda(res.total_volumetria)}`,
        `VALOR TOTAL:       ${fmtMoeda(res.valor_total)}`,
      ].join("\n");
      const blob = new Blob([linhas], { type: "text/plain;charset=utf-8" });
      const url  = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `descritivo_${res.numero_fatura}.txt`; a.click();
    } catch (e) { setErro(e.message); }
  };

  const set = (k, v) => setFiltros(f => ({ ...f, [k]: v || undefined, pagina: 1 }));

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: "#111827" }}>Faturamento</h1>
          <p style={{ margin: "3px 0 0", fontSize: 13, color: "#6B7280" }}>{meta.total} fatura(s)</p>
        </div>
        <button onClick={() => setModalApurar(true)} style={btnPrimStyle}>⚡ Apurar faturas</button>
      </div>

      {/* Filtros */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <input type="month" onChange={e => set("competencia", e.target.value ? e.target.value + "-01" : "")} style={inputStyle} />
        {[
          { k: "status",       opts: [["","Todos status"],["APURADA","Apurada"],["EMITIDA","Emitida"],["ENVIADA","Enviada"],["PAGA","Paga"],["INADIMPLENTE","Inadimplente"]] },
          { k: "dia_apuracao", opts: [["","Todos dias"],["DIA_01","1º dia útil"],["DIA_15","Dia 15"],["DIA_25","Dia 25"]] },
        ].map(({ k, opts }) => (
          <select key={k} onChange={e => set(k, e.target.value)} style={inputStyle}>
            {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        ))}
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
          <input type="checkbox" onChange={e => setFiltros(f => ({...f, em_atraso: e.target.checked, pagina: 1}))} />
          Em atraso
        </label>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={() => setErro(null)} style={{ background:"none",border:"none",cursor:"pointer" }}>✕</button></div>}

      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Tabela */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
            {loading ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF" }}>Carregando...</div>
            ) : faturas.length === 0 ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF" }}>Nenhuma fatura encontrada.</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#F9FAFB", borderBottom: "1px solid #E5E7EB" }}>
                    {["Nº Fatura","Cliente","Competência","Vencimento","Total","NF","Status","Ações"].map(h => (
                      <th key={h} style={{ padding: "9px 12px", textAlign: "left", fontWeight: 500, color: "#374151", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {faturas.map((f, i) => (
                    <tr key={f.id}
                      onClick={() => verDetalhe(f)}
                      style={{ borderBottom: "1px solid #F3F4F6", background: faturaSel?.id === f.id ? "#EFF6FF" : i % 2 === 0 ? "#fff" : "#FAFAFA", cursor: "pointer" }}>
                      <td style={{ padding: "10px 12px", fontFamily: "monospace", fontWeight: 500, color: "#374151" }}>{f.numero_fatura}</td>
                      <td style={{ padding: "10px 12px", color: "#111827" }}>
                        {f.cliente_nome}
                        <div style={{ fontSize: 11, color: "#9CA3AF" }}>{f.modalidade}</div>
                      </td>
                      <td style={{ padding: "10px 12px", color: "#6B7280" }}>{fmtData(f.competencia)?.slice(3)}</td>
                      <td style={{ padding: "10px 12px", color: f.dias_atraso > 0 ? "#B91C1C" : "#6B7280" }}>
                        {fmtData(f.data_vencimento)}
                        {f.dias_atraso > 0 && <span style={{ fontSize: 11, marginLeft: 4 }}>+{f.dias_atraso}d</span>}
                      </td>
                      <td style={{ padding: "10px 12px", fontFamily: "monospace", fontWeight: 500, color: "#111827" }}>{fmtMoeda(f.valor_total)}</td>
                      <td style={{ padding: "10px 12px", fontSize: 12, color: f.numero_nf ? "#15803D" : "#9CA3AF" }}>
                        {f.numero_nf || "—"}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span style={{ ...badge, background: STATUS_COR[f.status]?.bg, color: STATUS_COR[f.status]?.text }}>{f.status}</span>
                      </td>
                      <td style={{ padding: "10px 12px" }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: "flex", gap: 4 }}>
                          {!f.numero_nf && f.status === "APURADA" && (
                            <button onClick={() => { setModalNF(f); setFormNF({ numero_nf: "", data_emissao_nf: "" }); }} style={btnSmStyle}>NF</button>
                          )}
                          {f.status !== "PAGA" && f.status !== "CANCELADA" && (
                            <button onClick={() => { setModalPagamento(f); setFormPagamento({ valor_pago: f.valor_total, data_pagamento: new Date().toISOString().split("T")[0] }); }} style={btnSmStyle}>Pago</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {meta.paginas > 1 && (
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, marginTop: 10 }}>
              <button disabled={meta.pagina === 1} onClick={() => setFiltros(f => ({...f, pagina: f.pagina - 1}))} style={btnSecStyle}>←</button>
              <span style={{ padding: "6px 12px", fontSize: 13, color: "#6B7280" }}>{meta.pagina} / {meta.paginas}</span>
              <button disabled={meta.pagina === meta.paginas} onClick={() => setFiltros(f => ({...f, pagina: f.pagina + 1}))} style={btnSecStyle}>→</button>
            </div>
          )}
        </div>

        {/* Painel lateral: detalhe da fatura */}
        {faturaSel && (
          <div style={{ width: 320, flexShrink: 0, background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <div>
                <p style={{ margin: 0, fontSize: 12, color: "#9CA3AF" }}>{faturaSel.numero_fatura}</p>
                <span style={{ ...badge, background: STATUS_COR[faturaSel.status]?.bg, color: STATUS_COR[faturaSel.status]?.text }}>{faturaSel.status}</span>
              </div>
              <button onClick={() => setFaturaSel(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#9CA3AF" }}>✕</button>
            </div>

            {loadingDetalhe ? <p style={{ color: "#9CA3AF", fontSize: 13 }}>Carregando...</p> : (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
                  {[
                    ["Serviços",   fmtMoeda(faturaSel.valor_servicos)],
                    ["Volumetria", fmtMoeda(faturaSel.valor_volumetria)],
                    ["Total",      fmtMoeda(faturaSel.valor_total)],
                    ["Vencimento", fmtData(faturaSel.data_vencimento)],
                  ].map(([k, v]) => (
                    <div key={k} style={{ background: "#F9FAFB", padding: "8px 10px", borderRadius: 8 }}>
                      <p style={{ margin: 0, fontSize: 11, color: "#9CA3AF" }}>{k}</p>
                      <p style={{ margin: "2px 0 0", fontSize: 13, fontWeight: 500, color: "#111827" }}>{v}</p>
                    </div>
                  ))}
                </div>

                {/* Itens */}
                {faturaSel.itens?.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <p style={{ fontSize: 11, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", margin: "0 0 6px" }}>Itens</p>
                    {faturaSel.itens.map(item => (
                      <div key={item.id} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #F9FAFB", fontSize: 12 }}>
                        <span style={{ color: item.eh_volumetria ? "#C2410C" : "#374151" }}>
                          {item.eh_volumetria ? "🤝 " : ""}{item.descricao}
                        </span>
                        <span style={{ fontFamily: "monospace", color: "#1E40AF" }}>{fmtMoeda(item.valor_total)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Volumetrias */}
                {faturaSel.volumetrias?.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <p style={{ fontSize: 11, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", margin: "0 0 6px" }}>Volumetria folha</p>
                    {faturaSel.volumetrias.map(v => (
                      <div key={v.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "4px 0" }}>
                        <span style={{ color: "#374151" }}>{v.tipo_vinculo} × {v.quantidade}</span>
                        <span style={{ fontFamily: "monospace", color: "#C2410C" }}>{fmtMoeda(v.valor_total)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Ações */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <button onClick={() => handleDescritivo(faturaSel)} style={btnSecStyle}>📄 Descritivo</button>
                  <button onClick={() => handlePayloadK2(faturaSel)} style={btnSecStyle}>📤 Payload K2</button>
                  {faturaSel.descricao_nf && (
                    <div style={{ background: "#F9FAFB", padding: "8px 10px", borderRadius: 8, fontSize: 11, color: "#6B7280" }}>
                      <strong>Descrição NF:</strong><br />{faturaSel.descricao_nf}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Modal: Apurar faturas */}
      {modalApurar && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 420, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>⚡ Apurar faturas em lote</h2>

            {resultApuracao ? (
              <div>
                <div style={{ background: "#DCFCE7", border: "1px solid #BBF7D0", borderRadius: 8, padding: "12px 16px", marginBottom: 16 }}>
                  <p style={{ margin: 0, fontWeight: 600, color: "#15803D" }}>Apuração concluída</p>
                  <p style={{ margin: "4px 0 0", fontSize: 13, color: "#374151" }}>
                    {resultApuracao.faturas_criadas} fatura(s) criada(s) · {fmtMoeda(resultApuracao.valor_total)}
                  </p>
                  {resultApuracao.faturas_existentes > 0 && (
                    <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6B7280" }}>
                      {resultApuracao.faturas_existentes} já existia(m)
                    </p>
                  )}
                </div>
                <button onClick={() => { setModalApurar(false); setResultApuracao(null); }} style={{ ...btnPrimStyle, width: "100%" }}>Fechar</button>
              </div>
            ) : (
              <>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div>
                    <label style={labelStyle}>Dia de apuração *</label>
                    <select value={formApurar.dia_apuracao} onChange={e => setFormApurar(f => ({...f, dia_apuracao: e.target.value}))} style={inputStyle}>
                      <option value="DIA_01">1º dia útil do mês</option>
                      <option value="DIA_15">Dia 15</option>
                      <option value="DIA_25">Dia 25 (maior volume)</option>
                    </select>
                  </div>
                  <div>
                    <label style={labelStyle}>Competência (mês de referência) *</label>
                    <input type="month" value={formApurar.competencia} onChange={e => setFormApurar(f => ({...f, competencia: e.target.value}))} style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>Data da apuração *</label>
                    <input type="date" value={formApurar.data_apuracao} onChange={e => setFormApurar(f => ({...f, data_apuracao: e.target.value}))} style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>Data de vencimento *</label>
                    <input type="date" value={formApurar.data_vencimento} onChange={e => setFormApurar(f => ({...f, data_vencimento: e.target.value}))} style={inputStyle} />
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
                  <button onClick={() => setModalApurar(false)} style={btnSecStyle}>Cancelar</button>
                  <button onClick={handleApurar} disabled={!formApurar.competencia || !formApurar.data_apuracao || !formApurar.data_vencimento || apurando} style={btnPrimStyle}>
                    {apurando ? "Apurando..." : "Apurar"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Modal: Registrar pagamento */}
      {modalPagamento && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 380, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 6px" }}>Registrar pagamento</h2>
            <p style={{ fontSize: 13, color: "#6B7280", margin: "0 0 14px" }}>{modalPagamento.numero_fatura} — {modalPagamento.cliente_nome}</p>
            <label style={labelStyle}>Valor pago (R$) *</label>
            <input type="number" step="0.01" value={formPagamento.valor_pago} onChange={e => setFormPagamento(f => ({...f, valor_pago: e.target.value}))} style={{ ...inputStyle, marginBottom: 10 }} />
            <label style={labelStyle}>Data do pagamento *</label>
            <input type="date" value={formPagamento.data_pagamento} onChange={e => setFormPagamento(f => ({...f, data_pagamento: e.target.value}))} style={{ ...inputStyle, marginBottom: 14 }} />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setModalPagamento(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handlePagamento} disabled={salvando} style={btnPrimStyle}>{salvando ? "Salvando..." : "Confirmar"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Registrar NF */}
      {modalNF && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 380, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 6px" }}>Registrar NFS-e</h2>
            <p style={{ fontSize: 13, color: "#6B7280", margin: "0 0 14px" }}>{modalNF.numero_fatura}</p>
            <label style={labelStyle}>Número da NF *</label>
            <input value={formNF.numero_nf} onChange={e => setFormNF(f => ({...f, numero_nf: e.target.value}))} style={{ ...inputStyle, marginBottom: 10 }} />
            <label style={labelStyle}>Data de emissão *</label>
            <input type="date" value={formNF.data_emissao_nf} onChange={e => setFormNF(f => ({...f, data_emissao_nf: e.target.value}))} style={{ ...inputStyle, marginBottom: 14 }} />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setModalNF(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleRegistrarNF} disabled={!formNF.numero_nf || !formNF.data_emissao_nf || salvando} style={btnPrimStyle}>{salvando ? "Salvando..." : "Registrar"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const badge       = { padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 500 };
const inputStyle  = { padding: "7px 11px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 13, background: "#fff", color: "#111827", display: "block", width: "100%", boxSizing: "border-box" };
const labelStyle  = { display: "block", fontSize: 12, fontWeight: 500, color: "#374151", marginBottom: 4 };
const btnPrimStyle= { padding: "9px 18px", background: "#1E40AF", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer" };
const btnSecStyle = { padding: "7px 14px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, cursor: "pointer", width: "100%" };
const btnSmStyle  = { padding: "4px 8px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 6, fontSize: 11, cursor: "pointer" };
const alertStyle  = { padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, background: "#FEE2E2", color: "#B91C1C", display: "flex", justifyContent: "space-between" };
