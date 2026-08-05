// src/components/contratos/ContratoLista.jsx
"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { contratoService } from "../../services/contratoService";

const MODALIDADE_COR = {
  ASP: { bg: "#EFF6FF", text: "#1E40AF" },
  BSP: { bg: "#F5F3FF", text: "#5B21B6" },
  BPO: { bg: "#FFF7ED", text: "#C2410C" },
};
const STATUS_COR = {
  PROPOSTA:  { bg: "#FEF3C7", text: "#92400E" },
  ATIVO:     { bg: "#DCFCE7", text: "#15803D" },
  SUSPENSO:  { bg: "#FEE2E2", text: "#B91C1C" },
  ENCERRADO: { bg: "#F3F4F6", text: "#6B7280" },
  CANCELADO: { bg: "#F3F4F6", text: "#9CA3AF" },
};
const FASE_LABEL = { IMPLANTACAO: "🔧 Implantação", RECORRENCIA: "🔄 Recorrência" };
const DIA_LABEL  = { DIA_01: "1º dia útil", DIA_15: "Dia 15", DIA_25: "Dia 25" };

const fmtMoeda = (v) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const fmtData  = (d) => d ? new Date(d + "T00:00:00").toLocaleDateString("pt-BR") : "—";

export default function ContratoLista({ clienteId }) {
  const [dados, setDados]     = useState([]);
  const [meta, setMeta]       = useState({ total: 0, pagina: 1, por_pagina: 20, paginas: 0 });
  const [filtros, setFiltros] = useState({ pagina: 1, por_pagina: 20, cliente_id: clienteId });
  const [loading, setLoading] = useState(false);
  const [erro, setErro]       = useState(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const res = await contratoService.listar(filtros);
      setDados(res.dados);
      setMeta(res.meta);
    } catch (e) { setErro(e.message); }
    finally { setLoading(false); }
  }, [filtros]);

  useEffect(() => { carregar(); }, [carregar]);
  const set = (k, v) => setFiltros((f) => ({ ...f, [k]: v || undefined, pagina: 1 }));

  return (
    <div style={{ padding: clienteId ? 0 : "2rem", maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: "#111827" }}>Contratos</h1>
          <p style={{ margin: "3px 0 0", fontSize: 13, color: "#6B7280" }}>{meta.total} contrato(s)</p>
        </div>
        <Link href={clienteId ? `/contratos/novo?cliente_id=${clienteId}` : "/contratos/novo"}
          style={btnPrimStyle}>+ Novo contrato</Link>
      </div>

      {/* Filtros */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 12 }}>
        {[
          { label: "Modalidade", key: "modalidade", opts: [["","Todas"],["ASP","ASP"],["BSP","BSP"],["BPO","BPO"]] },
          { label: "Status", key: "status", opts: [["","Todos"],["PROPOSTA","Proposta"],["ATIVO","Ativo"],["SUSPENSO","Suspenso"],["ENCERRADO","Encerrado"]] },
          { label: "Fase", key: "fase", opts: [["","Todas"],["IMPLANTACAO","Implantação"],["RECORRENCIA","Recorrência"]] },
          { label: "Dia fat.", key: "dia_faturamento", opts: [["","Todos"],["DIA_01","1º dia"],["DIA_15","Dia 15"],["DIA_25","Dia 25"]] },
        ].map(({ label, key, opts }) => (
          <select key={key} onChange={(e) => set(key, e.target.value)} style={selStyle}>
            {opts.map(([v, l]) => <option key={v} value={v}>{l === "Todas" || l === "Todos" || l === "Todas" ? label + ": " + l : l}</option>)}
          </select>
        ))}
      </div>

      {erro && <div style={alertStyle("#FEE2E2","#B91C1C")}>{erro}</div>}

      <div style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF", fontSize: 14 }}>Carregando...</div>
        ) : dados.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF", fontSize: 14 }}>Nenhum contrato encontrado.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#F9FAFB", borderBottom: "1px solid #E5E7EB" }}>
                {["Número","Cliente","Modalidade","Fase","Dia fat.","Valor impl.","Valor mensal","Fim","Status",""].map(h => (
                  <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontWeight: 500, color: "#374151", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dados.map((c, i) => {
                const diasFim = c.dias_ate_fim;
                const alertaFim = diasFim !== null && diasFim <= 60;
                return (
                  <tr key={c.id} style={{ borderBottom: "1px solid #F3F4F6", background: i % 2 === 0 ? "#fff" : "#FAFAFA" }}>
                    <td style={{ padding: "11px 14px", fontFamily: "monospace", color: "#374151", fontWeight: 500 }}>{c.numero}</td>
                    <td style={{ padding: "11px 14px", color: "#111827" }}>{c.cliente_nome}</td>
                    <td style={{ padding: "11px 14px" }}>
                      <span style={{ ...badgeStyle, background: MODALIDADE_COR[c.modalidade]?.bg, color: MODALIDADE_COR[c.modalidade]?.text }}>
                        {c.modalidade}
                      </span>
                    </td>
                    <td style={{ padding: "11px 14px", color: "#6B7280", fontSize: 12 }}>{FASE_LABEL[c.fase_atual]}</td>
                    <td style={{ padding: "11px 14px", color: "#6B7280" }}>{DIA_LABEL[c.dia_faturamento]}</td>
                    <td style={{ padding: "11px 14px", color: "#374151", fontFamily: "monospace" }}>{fmtMoeda(c.valor_total_impl)}</td>
                    <td style={{ padding: "11px 14px", color: "#374151", fontFamily: "monospace" }}>{fmtMoeda(c.valor_mensal)}</td>
                    <td style={{ padding: "11px 14px" }}>
                      {c.data_fim_contrato ? (
                        <span style={{ color: alertaFim ? "#B91C1C" : "#6B7280", fontSize: 12 }}>
                          {alertaFim && "⚠ "}{fmtData(c.data_fim_contrato)}
                          {diasFim !== null && <span style={{ color: "#9CA3AF" }}> ({diasFim}d)</span>}
                        </span>
                      ) : "—"}
                    </td>
                    <td style={{ padding: "11px 14px" }}>
                      <span style={{ ...badgeStyle, background: STATUS_COR[c.status]?.bg, color: STATUS_COR[c.status]?.text }}>
                        {c.status}
                      </span>
                    </td>
                    <td style={{ padding: "11px 14px" }}>
                      <Link href={`/contratos/${c.id}`} style={{ color: "#1E40AF", fontSize: 12, textDecoration: "none" }}>
                        Ver →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {meta.paginas > 1 && (
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, marginTop: 12 }}>
          <button disabled={meta.pagina === 1} onClick={() => setFiltros(f => ({...f, pagina: f.pagina - 1}))} style={btnSecStyle}>←</button>
          <span style={{ padding: "6px 12px", fontSize: 13, color: "#6B7280" }}>{meta.pagina} / {meta.paginas}</span>
          <button disabled={meta.pagina === meta.paginas} onClick={() => setFiltros(f => ({...f, pagina: f.pagina + 1}))} style={btnSecStyle}>→</button>
        </div>
      )}
    </div>
  );
}

const badgeStyle  = { padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 500 };
const selStyle    = { padding: "6px 10px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 13, background: "#fff" };
const btnPrimStyle = { background: "#1E40AF", color: "#fff", padding: "7px 16px", borderRadius: 8, textDecoration: "none", fontSize: 13, fontWeight: 500 };
const btnSecStyle  = { padding: "6px 12px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 13, background: "#fff", cursor: "pointer" };
const alertStyle   = (bg, color) => ({ padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, background: bg, color });
