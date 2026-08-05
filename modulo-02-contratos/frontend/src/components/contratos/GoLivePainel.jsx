// src/components/contratos/GoLivePainel.jsx
"use client";
import { useState, useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const fmtData  = (d) => d ? new Date(d + "T00:00:00").toLocaleDateString("pt-BR") : "—";

export default function GoLivePainel({ contratoId }) {
  const [itens, setItens]       = useState([]);
  const [loading, setLoading]   = useState(false);
  const [erro, setErro]         = useState(null);
  const [selecionados, setSelecionados] = useState(new Set());
  const [dataGoLive, setDataGoLive]     = useState("");
  const [modalLote, setModalLote]       = useState(false);
  const [salvando, setSalvando]         = useState(false);

  const carregar = async () => {
    setLoading(true);
    try {
      const q = contratoId ? `?contrato_id=${contratoId}` : "";
      const res = await api(`/go-live/pendentes${q}`);
      setItens(res);
    } catch (e) { setErro(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { carregar(); }, [contratoId]);

  const toggleSel = (id) => {
    setSelecionados(prev => {
      const novo = new Set(prev);
      novo.has(id) ? novo.delete(id) : novo.add(id);
      return novo;
    });
  };

  const toggleTodos = () => {
    if (selecionados.size === itens.length) {
      setSelecionados(new Set());
    } else {
      setSelecionados(new Set(itens.map(i => i.item_id)));
    }
  };

  const handleGoLiveIndividual = async (item) => {
    const data = window.prompt(`Data de go-live para "${item.produto_nome}" (AAAA-MM-DD):`);
    if (!data) return;
    try {
      await api(`/contratos/${item.contrato_id}/itens/${item.item_id}/go-live`, {
        method: "PATCH",
        body: JSON.stringify({ data_goLive: data }),
      });
      carregar();
    } catch (e) { setErro(e.message); }
  };

  const handleGoLiveLote = async () => {
    if (!dataGoLive) return;
    setSalvando(true);
    try {
      // Agrupa por contrato para fazer uma chamada por contrato
      const porContrato = {};
      itens
        .filter(i => selecionados.has(i.item_id))
        .forEach(i => {
          if (!porContrato[i.contrato_id]) porContrato[i.contrato_id] = [];
          porContrato[i.contrato_id].push(i.item_id);
        });

      for (const [cid, ids] of Object.entries(porContrato)) {
        await api(`/contratos/${cid}/itens/go-live-lote`, {
          method: "PATCH",
          body: JSON.stringify({ data_goLive: dataGoLive, item_ids: ids }),
        });
      }

      setModalLote(false);
      setSelecionados(new Set());
      setDataGoLive("");
      carregar();
    } catch (e) { setErro(e.message); }
    finally { setSalvando(false); }
  };

  // Agrupa por contrato para melhor visualização
  const porContrato = itens.reduce((acc, item) => {
    const key = item.contrato_id;
    if (!acc[key]) acc[key] = { numero: item.contrato_numero, cliente: item.cliente_nome, itens: [] };
    acc[key].itens.push(item);
    return acc;
  }, {});

  return (
    <div style={{ padding: contratoId ? 0 : "2rem", maxWidth: 1000, margin: "0 auto" }}>

      {/* Cabeçalho */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: "#111827" }}>
            Acompanhamento de go-live
          </h1>
          <p style={{ margin: "3px 0 0", fontSize: 13, color: "#6B7280" }}>
            {itens.length} item(s) aguardando confirmação
          </p>
        </div>
        {selecionados.size > 0 && (
          <button onClick={() => setModalLote(true)} style={btnPrimStyle}>
            ✓ Go-live em lote ({selecionados.size} itens)
          </button>
        )}
      </div>

      {erro && (
        <div style={alertStyle}>
          {erro}
          <button onClick={() => setErro(null)} style={{ background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF" }}>Carregando...</div>
      ) : itens.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF", background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10 }}>
          Nenhum item aguardando go-live.
        </div>
      ) : (
        <div>
          {/* Cabeçalho da tabela com seleção */}
          <div style={{ background: "#F9FAFB", border: "1px solid #E5E7EB", borderRadius: "10px 10px 0 0", padding: "8px 16px", display: "flex", alignItems: "center", gap: 10 }}>
            <input type="checkbox"
              checked={selecionados.size === itens.length && itens.length > 0}
              onChange={toggleTodos} />
            <span style={{ fontSize: 13, color: "#374151", fontWeight: 500 }}>
              {selecionados.size > 0 ? `${selecionados.size} selecionado(s)` : "Selecionar todos"}
            </span>
          </div>

          {/* Grupos por contrato */}
          {Object.entries(porContrato).map(([cid, grupo]) => (
            <div key={cid} style={{ border: "1px solid #E5E7EB", borderTop: "none", background: "#fff" }}>

              {/* Header do contrato */}
              <div style={{ padding: "10px 16px", background: "#F9FAFB", borderBottom: "1px solid #F3F4F6", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 600, color: "#374151" }}>{grupo.numero}</span>
                  <span style={{ fontSize: 14, color: "#111827" }}>{grupo.cliente}</span>
                </div>
                <button
                  onClick={() => {
                    const ids = new Set([...grupo.itens.map(i => i.item_id)]);
                    setSelecionados(prev => {
                      const novo = new Set(prev);
                      const todosJaSel = grupo.itens.every(i => novo.has(i.item_id));
                      ids.forEach(id => todosJaSel ? novo.delete(id) : novo.add(id));
                      return novo;
                    });
                  }}
                  style={btnSmStyle}>
                  Selecionar contrato
                </button>
              </div>

              {/* Itens do contrato */}
              {grupo.itens.map(item => (
                <div key={item.item_id} style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid #F9FAFB",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  background: selecionados.has(item.item_id) ? "#EFF6FF" : "#fff",
                }}>
                  <input type="checkbox"
                    checked={selecionados.has(item.item_id)}
                    onChange={() => toggleSel(item.item_id)} />

                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={{ fontSize: 14, fontWeight: 500, color: "#111827" }}>{item.produto_nome}</span>
                      <span style={{ fontSize: 11, color: "#6B7280", background: "#F3F4F6", padding: "1px 6px", borderRadius: 10 }}>
                        {item.modalidade}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 16, marginTop: 3 }}>
                      <span style={{ fontSize: 12, color: "#6B7280" }}>
                        Implantação iniciada: {fmtData(item.data_inicio_impl)}
                      </span>
                      <span style={{ fontSize: 12, color: item.dias_em_implantacao > 90 ? "#B91C1C" : "#6B7280", fontWeight: item.dias_em_implantacao > 90 ? 600 : 400 }}>
                        {item.dias_em_implantacao > 90 && "⚠ "}{item.dias_em_implantacao} dias em implantação
                      </span>
                    </div>
                  </div>

                  <div style={{ textAlign: "right", marginRight: 8 }}>
                    <p style={{ margin: 0, fontSize: 13, fontFamily: "monospace", fontWeight: 500, color: "#1E40AF" }}>
                      {fmtMoeda(item.valor_total)}/mês
                    </p>
                    <p style={{ margin: "2px 0 0", fontSize: 11, color: "#9CA3AF" }}>quando ativo</p>
                  </div>

                  <button
                    onClick={() => handleGoLiveIndividual(item)}
                    style={{ ...btnSmStyle, background: "#DCFCE7", color: "#15803D", borderColor: "#BBF7D0", whiteSpace: "nowrap" }}>
                    ✓ Go-live
                  </button>
                </div>
              ))}
            </div>
          ))}

          <div style={{ border: "1px solid #E5E7EB", borderTop: "none", borderRadius: "0 0 10px 10px", height: 1 }} />
        </div>
      )}

      {/* Modal go-live em lote */}
      {modalLote && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 400, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 6px" }}>Confirmar go-live em lote</h2>
            <p style={{ fontSize: 14, color: "#6B7280", margin: "0 0 16px" }}>
              {selecionados.size} item(s) selecionado(s) entrarão em produção nesta data.
            </p>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#374151", marginBottom: 4 }}>Data de go-live *</label>
            <input
              type="date"
              value={dataGoLive}
              onChange={e => setDataGoLive(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 14, boxSizing: "border-box", marginBottom: 16 }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setModalLote(false)} style={btnSecStyle}>Cancelar</button>
              <button
                onClick={handleGoLiveLote}
                disabled={!dataGoLive || salvando}
                style={{ ...btnPrimStyle, opacity: !dataGoLive ? 0.5 : 1 }}>
                {salvando ? "Salvando..." : "Confirmar go-live"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const btnPrimStyle = { padding: "8px 16px", background: "#1E40AF", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer" };
const btnSecStyle  = { padding: "8px 16px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const btnSmStyle   = { padding: "5px 10px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 6, fontSize: 12, cursor: "pointer" };
const alertStyle   = { padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, background: "#FEE2E2", color: "#B91C1C", display: "flex", justifyContent: "space-between" };
