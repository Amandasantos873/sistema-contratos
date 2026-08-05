// src/components/produtos/ProdutoCatalogo.jsx
"use client";
import { useState, useEffect, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...opts })
    .then(r => r.ok ? (r.status === 204 ? null : r.json()) : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = (v) => v != null ? Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—";

const STATUS_COR = {
  ATIVO:         { bg: "#DCFCE7", text: "#15803D" },
  DESCONTINUADO: { bg: "#FEE2E2", text: "#B91C1C" },
  SUSPENSO:      { bg: "#FEF3C7", text: "#92400E" },
};
const MOD_COR = {
  ASP: { bg: "#EFF6FF", text: "#1E40AF" },
  BSP: { bg: "#F5F3FF", text: "#5B21B6" },
  BPO: { bg: "#FFF7ED", text: "#C2410C" },
};

export default function ProdutoCatalogo() {
  const [dados, setDados]     = useState([]);
  const [meta, setMeta]       = useState({ total: 0, paginas: 0, pagina: 1 });
  const [filtros, setFiltros] = useState({ pagina: 1, por_pagina: 30 });
  const [loading, setLoading] = useState(false);
  const [erro, setErro]       = useState(null);
  const [produtoSelecionado, setProdutoSelecionado] = useState(null);
  const [usoContratos, setUsoContratos]   = useState([]);
  const [loadingUso, setLoadingUso]       = useState(false);
  const [modalDescontinuar, setModalDescontinuar] = useState(null);
  const [motivoDesc, setMotivoDesc]       = useState("");
  const [salvando, setSalvando]           = useState(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams();
      Object.entries(filtros).forEach(([k, v]) => v != null && q.append(k, v));
      const res = await api(`/produtos?${q}`);
      setDados(res.dados);
      setMeta(res.meta);
    } catch (e) { setErro(e.message); }
    finally { setLoading(false); }
  }, [filtros]);

  useEffect(() => { carregar(); }, [carregar]);

  const verUso = async (produto) => {
    setProdutoSelecionado(produto);
    setLoadingUso(true);
    try {
      const uso = await api(`/produtos/${produto.id}/uso`);
      setUsoContratos(uso);
    } catch { setUsoContratos([]); }
    finally { setLoadingUso(false); }
  };

  const handleDescontinuar = async () => {
    if (!modalDescontinuar || motivoDesc.length < 10) return;
    setSalvando(true);
    try {
      await api(`/produtos/${modalDescontinuar.id}/descontinuar`, {
        method: "PATCH",
        body: JSON.stringify({ motivo: motivoDesc }),
      });
      setModalDescontinuar(null);
      setMotivoDesc("");
      carregar();
    } catch (e) { setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleReativar = async (produto) => {
    try {
      await api(`/produtos/${produto.id}/reativar`, { method: "PATCH" });
      carregar();
    } catch (e) { setErro(e.message); }
  };

  const set = (k, v) => setFiltros(f => ({ ...f, [k]: v || undefined, pagina: 1 }));

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>

      {/* Cabeçalho */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: "#111827" }}>Catálogo de produtos e serviços</h1>
          <p style={{ margin: "3px 0 0", fontSize: 13, color: "#6B7280" }}>{meta.total} produto(s)</p>
        </div>
        <button onClick={() => window.location.href = "/produtos/novo"} style={btnPrimStyle}>+ Novo produto</button>
      </div>

      {/* Filtros */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <input
          placeholder="Buscar por nome ou código..."
          onChange={e => set("busca", e.target.value)}
          style={{ ...inputStyle, flex: "1 1 240px" }}
        />
        {[
          { key: "modalidade", opts: [["", "Todas modalidades"], ["ASP","ASP"], ["BSP","BSP"], ["BPO","BPO"]] },
          { key: "status",     opts: [["", "Todos os status"], ["ATIVO","Ativo"], ["DESCONTINUADO","Descontinuado"], ["SUSPENSO","Suspenso"]] },
        ].map(({ key, opts }) => (
          <select key={key} onChange={e => set(key, e.target.value)} style={{ ...inputStyle, maxWidth: 180 }}>
            {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        ))}
      </div>

      {erro && <div style={alertStyle}>{erro} <button onClick={() => setErro(null)} style={{ background:"none",border:"none",cursor:"pointer",float:"right" }}>✕</button></div>}

      {/* Layout dividido: tabela + painel de uso */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Tabela */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
            {loading ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF", fontSize: 14 }}>Carregando...</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#F9FAFB", borderBottom: "1px solid #E5E7EB" }}>
                    {["Código","Nome","Modalidade","Fase","Contratos ativos","Valor médio","Status","Ações"].map(h => (
                      <th key={h} style={{ padding: "9px 12px", textAlign: "left", fontWeight: 500, color: "#374151", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dados.map((p, i) => (
                    <tr key={p.id}
                      onClick={() => verUso(p)}
                      style={{
                        borderBottom: "1px solid #F3F4F6",
                        background: produtoSelecionado?.id === p.id ? "#EFF6FF" : i % 2 === 0 ? "#fff" : "#FAFAFA",
                        cursor: "pointer",
                      }}>
                      <td style={{ padding: "10px 12px", fontFamily: "monospace", color: "#6B7280", fontSize: 12 }}>{p.codigo}</td>
                      <td style={{ padding: "10px 12px" }}>
                        <span style={{ fontWeight: 500, color: "#111827" }}>{p.nome}</span>
                        {p.status === "DESCONTINUADO" && p.substituto_nome && (
                          <div style={{ fontSize: 11, color: "#9CA3AF" }}>→ {p.substituto_nome}</div>
                        )}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span style={{ ...badge, background: MOD_COR[p.modalidade]?.bg, color: MOD_COR[p.modalidade]?.text }}>{p.modalidade}</span>
                      </td>
                      <td style={{ padding: "10px 12px", fontSize: 12, color: "#6B7280" }}>
                        {[p.permite_impl && "Impl.", p.permite_recorr && "Recorr."].filter(Boolean).join(" · ")}
                      </td>
                      <td style={{ padding: "10px 12px", textAlign: "center" }}>
                        {p.contratos_ativos > 0 ? (
                          <span style={{ fontWeight: 600, color: "#1E40AF" }}>{p.contratos_ativos}</span>
                        ) : (
                          <span style={{ color: "#9CA3AF" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "10px 12px", fontFamily: "monospace", color: "#374151" }}>
                        {fmtMoeda(p.valor_medio_praticado)}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span style={{ ...badge, background: STATUS_COR[p.status]?.bg, color: STATUS_COR[p.status]?.text }}>
                          {p.status}
                        </span>
                      </td>
                      <td style={{ padding: "10px 12px" }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: "flex", gap: 6 }}>
                          {p.status === "ATIVO" && (
                            <button onClick={() => setModalDescontinuar(p)} style={btnSmStyle}>Descontinuar</button>
                          )}
                          {p.status !== "ATIVO" && (
                            <button onClick={() => handleReativar(p)} style={{ ...btnSmStyle, color: "#15803D", borderColor: "#BBF7D0" }}>Reativar</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Paginação */}
          {meta.paginas > 1 && (
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, marginTop: 10 }}>
              <button disabled={meta.pagina === 1} onClick={() => setFiltros(f => ({...f, pagina: f.pagina - 1}))} style={btnSecStyle}>←</button>
              <span style={{ padding: "6px 12px", fontSize: 13, color: "#6B7280" }}>{meta.pagina} / {meta.paginas}</span>
              <button disabled={meta.pagina === meta.paginas} onClick={() => setFiltros(f => ({...f, pagina: f.pagina + 1}))} style={btnSecStyle}>→</button>
            </div>
          )}
        </div>

        {/* Painel lateral: uso em contratos */}
        {produtoSelecionado && (
          <div style={{ width: 340, flexShrink: 0, background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <p style={{ margin: 0, fontSize: 12, color: "#9CA3AF" }}>Uso em contratos</p>
                <p style={{ margin: "2px 0 0", fontSize: 14, fontWeight: 500, color: "#111827" }}>{produtoSelecionado.nome}</p>
              </div>
              <button onClick={() => setProdutoSelecionado(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#9CA3AF", fontSize: 16 }}>✕</button>
            </div>

            {loadingUso ? (
              <p style={{ fontSize: 13, color: "#9CA3AF" }}>Carregando...</p>
            ) : usoContratos.length === 0 ? (
              <p style={{ fontSize: 13, color: "#9CA3AF" }}>Nenhum contrato ativo usa este produto.</p>
            ) : (
              <>
                <p style={{ fontSize: 12, color: "#6B7280", margin: "0 0 10px" }}>
                  {usoContratos.length} contrato(s) ativo(s)
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {usoContratos.map(u => (
                    <div key={u.contrato_id} style={{ padding: "10px 12px", background: "#F9FAFB", borderRadius: 8, border: "1px solid #F3F4F6" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontFamily: "monospace", fontSize: 12, color: "#374151", fontWeight: 500 }}>{u.contrato_numero}</span>
                        <span style={{ fontSize: 11, color: "#6B7280" }}>{u.item_fase === "IMPLANTACAO" ? "🔧 Impl." : "🔄 Recorr."}</span>
                      </div>
                      <p style={{ margin: "3px 0 0", fontSize: 13, color: "#111827" }}>{u.cliente_nome}</p>
                      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                        <span style={{ fontSize: 12, color: "#6B7280" }}>Qtd {u.quantidade}</span>
                        <span style={{ fontSize: 12, fontFamily: "monospace", color: "#1E40AF", fontWeight: 500 }}>{fmtMoeda(u.valor_total)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Modal descontinuar */}
      {modalDescontinuar && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 420, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 6px" }}>Descontinuar produto</h2>
            <p style={{ fontSize: 14, color: "#6B7280", margin: "0 0 4px" }}>
              <strong>{modalDescontinuar.nome}</strong>
            </p>
            {modalDescontinuar.contratos_ativos > 0 && (
              <div style={{ background: "#FEE2E2", color: "#B91C1C", padding: "8px 12px", borderRadius: 8, fontSize: 13, margin: "8px 0" }}>
                ⚠ Este produto está em {modalDescontinuar.contratos_ativos} contrato(s) ativo(s). Encerre ou substitua o item nos contratos primeiro.
              </div>
            )}
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#374151", margin: "12px 0 4px" }}>
              Motivo *
            </label>
            <textarea
              value={motivoDesc}
              onChange={e => setMotivoDesc(e.target.value)}
              rows={3}
              placeholder="Descreva o motivo da descontinuação (mínimo 10 caracteres)..."
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 14, boxSizing: "border-box", resize: "vertical" }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
              <button onClick={() => { setModalDescontinuar(null); setMotivoDesc(""); }} style={btnSecStyle}>Cancelar</button>
              <button
                onClick={handleDescontinuar}
                disabled={motivoDesc.length < 10 || modalDescontinuar.contratos_ativos > 0 || salvando}
                style={{ ...btnSecStyle, background: "#B91C1C", color: "#fff", borderColor: "#B91C1C",
                  opacity: (motivoDesc.length < 10 || modalDescontinuar.contratos_ativos > 0) ? 0.5 : 1 }}
              >
                {salvando ? "Salvando..." : "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const badge       = { padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 500 };
const inputStyle  = { padding: "7px 11px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 13, background: "#fff", color: "#111827" };
const btnPrimStyle= { background: "#1E40AF", color: "#fff", padding: "7px 16px", borderRadius: 8, border: "none", fontSize: 13, fontWeight: 500, cursor: "pointer" };
const btnSecStyle = { padding: "7px 16px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const btnSmStyle  = { padding: "4px 10px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 6, fontSize: 12, cursor: "pointer" };
const alertStyle  = { padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, background: "#FEE2E2", color: "#B91C1C" };
