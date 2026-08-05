// src/components/validacao/ValidacaoPainel.jsx
"use client";
import { useState, useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = (v) => v != null ? Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—";
const fmtData  = (d) => d ? new Date(d).toLocaleDateString("pt-BR") : "—";

const SEV_COR = {
  CRITICO: { bg: "#FEE2E2", text: "#B91C1C", icon: "🔴" },
  ATENCAO: { bg: "#FEF3C7", text: "#92400E", icon: "🟡" },
  INFO:    { bg: "#EFF6FF", text: "#1E40AF", icon: "🔵" },
};

const STATUS_VAL_COR = {
  APROVADA:    { bg: "#DCFCE7", text: "#15803D" },
  COM_ALERTAS: { bg: "#FEF3C7", text: "#92400E" },
  BLOQUEADA:   { bg: "#FEE2E2", text: "#B91C1C" },
  JUSTIFICADA: { bg: "#EDE9FE", text: "#5B21B6" },
};

export default function ValidacaoPainel() {
  const [alertas, setAlertas]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [erro, setErro]         = useState(null);

  // Validar fatura
  const [faturaIdValidar, setFaturaIdValidar] = useState("");
  const [validando, setValidando]             = useState(false);
  const [resultValidacao, setResultValidacao] = useState(null);
  const [comIA, setComIA]                     = useState(false);

  // Justificativas
  const [justificativas, setJustificativas] = useState({});
  const [emitindo, setEmitindo]             = useState(false);

  const carregarAlertas = async () => {
    setLoading(true);
    try {
      const res = await api("/validacao/alertas");
      setAlertas(res);
    } catch (e) { setErro(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { carregarAlertas(); }, []);

  const handleValidar = async () => {
    if (!faturaIdValidar.trim()) return;
    setValidando(true);
    setResultValidacao(null);
    try {
      const res = await api(`/faturas/${faturaIdValidar}/validar?com_ia=${comIA}`, { method: "POST" });
      setResultValidacao(res);
      carregarAlertas();
    } catch (e) { setErro(e.message); }
    finally { setValidando(false); }
  };

  const handleJustificarAlerta = async (alertaId) => {
    const just = justificativas[alertaId];
    if (!just || just.length < 15) return;
    try {
      await api(`/validacao/alertas/${alertaId}/justificar`, {
        method: "PATCH",
        body: JSON.stringify({ justificativa: just }),
      });
      carregarAlertas();
      setJustificativas(j => { const n = {...j}; delete n[alertaId]; return n; });
    } catch (e) { setErro(e.message); }
  };

  const handleEmitirComRessalva = async () => {
    if (!resultValidacao) return;
    const criticos = resultValidacao.alertas.filter(a => a.severidade === "CRITICO" && a.status === "ABERTO");
    const todos_just = criticos.every(a => justificativas[a.id]?.length >= 15);
    if (!todos_just) {
      setErro("Todos os alertas críticos precisam de justificativa (mínimo 15 caracteres).");
      return;
    }
    setEmitindo(true);
    try {
      await api(`/faturas/${faturaIdValidar}/emitir-com-ressalva`, {
        method: "POST",
        body: JSON.stringify({
          justificativas: criticos.map(a => ({ alerta_id: a.id, justificativa: justificativas[a.id] }))
        }),
      });
      setResultValidacao(prev => ({ ...prev, status: "JUSTIFICADA" }));
      carregarAlertas();
    } catch (e) { setErro(e.message); }
    finally { setEmitindo(false); }
  };

  // Agrupa alertas do painel por severidade
  const criticos = alertas.filter(a => a.severidade === "CRITICO");
  const atencoes = alertas.filter(a => a.severidade === "ATENCAO");

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>

      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: "#111827" }}>Validação de faturamento</h1>
        <p style={{ margin: "3px 0 0", fontSize: 13, color: "#6B7280" }}>
          {criticos.length} alerta(s) crítico(s) · {atencoes.length} atenção(ões) em aberto
        </p>
      </div>

      {erro && (
        <div style={{ ...alertStyle, display: "flex", justifyContent: "space-between" }}>
          {erro}
          <button onClick={() => setErro(null)} style={{ background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Coluna esquerda: validar fatura + resultado */}
        <div style={{ width: 360, flexShrink: 0 }}>
          <div style={cardStyle}>
            <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 14px", color: "#111827" }}>Validar fatura</h2>
            <label style={labelStyle}>ID da fatura *</label>
            <input
              value={faturaIdValidar}
              onChange={e => setFaturaIdValidar(e.target.value)}
              placeholder="UUID da fatura..."
              style={{ ...inputStyle, marginBottom: 10 }}
            />
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, marginBottom: 12, cursor: "pointer" }}>
              <input type="checkbox" checked={comIA} onChange={e => setComIA(e.target.checked)} />
              Incluir análise de anomalias (Claude API)
            </label>
            <button onClick={handleValidar} disabled={!faturaIdValidar || validando} style={{ ...btnPrimStyle, width: "100%" }}>
              {validando ? "Validando..." : "Executar validação"}
            </button>
          </div>

          {/* Resultado da validação */}
          {resultValidacao && (
            <div style={{ ...cardStyle, marginTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Resultado</h3>
                <span style={{ ...badge, background: STATUS_VAL_COR[resultValidacao.status]?.bg, color: STATUS_VAL_COR[resultValidacao.status]?.text }}>
                  {resultValidacao.status}
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 14 }}>
                {[
                  ["Críticos", resultValidacao.total_criticos, "#B91C1C"],
                  ["Atenção",  resultValidacao.total_atencao,  "#92400E"],
                  ["Info",     resultValidacao.total_info,     "#1E40AF"],
                ].map(([k, v, color]) => (
                  <div key={k} style={{ background: "#F9FAFB", padding: "8px 10px", borderRadius: 8, textAlign: "center" }}>
                    <p style={{ margin: 0, fontSize: 20, fontWeight: 700, color }}>{v}</p>
                    <p style={{ margin: 0, fontSize: 11, color: "#9CA3AF" }}>{k}</p>
                  </div>
                ))}
              </div>

              {/* Alertas do resultado com campo de justificativa */}
              <div style={{ maxHeight: 320, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
                {resultValidacao.alertas.map(alerta => (
                  <div key={alerta.id} style={{
                    padding: "10px 12px", borderRadius: 8,
                    background: SEV_COR[alerta.severidade]?.bg,
                    border: `1px solid ${alerta.severidade === "CRITICO" ? "#FECACA" : "#FDE68A"}`,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: SEV_COR[alerta.severidade]?.text }}>
                        {SEV_COR[alerta.severidade]?.icon} {alerta.codigo}
                      </span>
                      {alerta.status === "JUSTIFICADO" && (
                        <span style={{ fontSize: 11, color: "#15803D" }}>✓ Justificado</span>
                      )}
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: "#374151" }}>{alerta.detalhe}</p>

                    {alerta.valor_esperado != null && (
                      <p style={{ margin: "3px 0 0", fontSize: 11, color: "#6B7280" }}>
                        Esperado: {fmtMoeda(alerta.valor_esperado)} · Encontrado: {fmtMoeda(alerta.valor_encontrado)}
                      </p>
                    )}

                    {alerta.status === "ABERTO" && resultValidacao.status === "BLOQUEADA" && (
                      <div style={{ marginTop: 6 }}>
                        <input
                          placeholder="Justificativa (mín. 15 caracteres)..."
                          value={justificativas[alerta.id] || ""}
                          onChange={e => setJustificativas(j => ({...j, [alerta.id]: e.target.value}))}
                          style={{ ...inputStyle, fontSize: 12, padding: "5px 8px" }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Botão emitir com ressalva */}
              {resultValidacao.status === "BLOQUEADA" && (
                <button
                  onClick={handleEmitirComRessalva}
                  disabled={emitindo}
                  style={{ ...btnDangerStyle, width: "100%", marginTop: 12 }}>
                  {emitindo ? "Processando..." : "⚠ Emitir com ressalva"}
                </button>
              )}

              {/* Análise IA */}
              {resultValidacao.analise_ia?.anomalias?.length > 0 && (
                <div style={{ marginTop: 12, padding: "10px 12px", background: "#F5F3FF", borderRadius: 8 }}>
                  <p style={{ margin: "0 0 6px", fontSize: 12, fontWeight: 600, color: "#5B21B6" }}>
                    🤖 Anomalias detectadas pela IA
                  </p>
                  {resultValidacao.analise_ia.anomalias.map((a, i) => (
                    <p key={i} style={{ margin: "3px 0", fontSize: 12, color: "#374151" }}>
                      {SEV_COR[a.severidade]?.icon} {a.codigo}: {a.detalhe}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Coluna direita: painel de alertas abertos */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ ...cardStyle, marginBottom: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h2 style={{ fontSize: 14, fontWeight: 600, margin: 0, color: "#111827" }}>
                Alertas abertos em todas as faturas
              </h2>
              <button onClick={carregarAlertas} style={btnSmStyle}>↻ Atualizar</button>
            </div>

            {loading ? (
              <p style={{ color: "#9CA3AF", fontSize: 13 }}>Carregando...</p>
            ) : alertas.length === 0 ? (
              <div style={{ padding: "2rem", textAlign: "center" }}>
                <p style={{ fontSize: 32, margin: "0 0 8px" }}>✅</p>
                <p style={{ color: "#15803D", fontSize: 14, fontWeight: 500 }}>Nenhum alerta em aberto</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 600, overflowY: "auto" }}>
                {alertas.map(a => (
                  <div key={a.alerta_id} style={{
                    padding: "12px 14px", borderRadius: 8,
                    background: SEV_COR[a.severidade]?.bg,
                    border: `1px solid ${a.severidade === "CRITICO" ? "#FECACA" : "#FDE68A"}`,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 3 }}>
                          <span style={{ fontSize: 12, fontWeight: 600, color: SEV_COR[a.severidade]?.text }}>
                            {SEV_COR[a.severidade]?.icon} {a.codigo}
                          </span>
                          <span style={{ fontSize: 11, fontFamily: "monospace", color: "#6B7280" }}>{a.numero_fatura}</span>
                          <span style={{ fontSize: 11, color: "#9CA3AF" }}>·</span>
                          <span style={{ fontSize: 11, color: "#6B7280" }}>{a.cliente_nome}</span>
                        </div>
                        <p style={{ margin: 0, fontSize: 13, color: "#374151" }}>{a.detalhe}</p>
                        {a.valor_esperado != null && (
                          <p style={{ margin: "3px 0 0", fontSize: 11, color: "#6B7280" }}>
                            Esperado: {fmtMoeda(a.valor_esperado)} · Encontrado: {fmtMoeda(a.valor_encontrado)}
                          </p>
                        )}
                      </div>
                      <div style={{ marginLeft: 10, textAlign: "right", flexShrink: 0 }}>
                        <p style={{ margin: 0, fontSize: 11, color: "#9CA3AF" }}>
                          {new Date(a.criado_em).toLocaleDateString("pt-BR")}
                        </p>
                        <span style={{ fontSize: 11, color: "#9CA3AF" }}>
                          {a.competencia ? new Date(a.competencia + "T00:00:00").toLocaleDateString("pt-BR", { month: "2-digit", year: "numeric" }) : ""}
                        </span>
                      </div>
                    </div>

                    {/* Campo de justificativa inline */}
                    <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                      <input
                        placeholder="Justificativa para resolver este alerta..."
                        value={justificativas[a.alerta_id] || ""}
                        onChange={e => setJustificativas(j => ({...j, [a.alerta_id]: e.target.value}))}
                        style={{ ...inputStyle, flex: 1, fontSize: 12, padding: "5px 8px" }}
                      />
                      <button
                        onClick={() => handleJustificarAlerta(a.alerta_id)}
                        disabled={!justificativas[a.alerta_id] || justificativas[a.alerta_id].length < 15}
                        style={{ ...btnSmStyle, whiteSpace: "nowrap", opacity: (!justificativas[a.alerta_id] || justificativas[a.alerta_id].length < 15) ? 0.5 : 1 }}>
                        Justificar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const badge        = { padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 500 };
const cardStyle    = { background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1.25rem" };
const inputStyle   = { padding: "7px 11px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 13, background: "#fff", color: "#111827", width: "100%", boxSizing: "border-box", display: "block" };
const labelStyle   = { display: "block", fontSize: 12, fontWeight: 500, color: "#374151", marginBottom: 4 };
const btnPrimStyle = { padding: "9px 18px", background: "#1E40AF", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer" };
const btnDangerStyle = { padding: "9px 18px", background: "#B91C1C", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer" };
const btnSmStyle   = { padding: "5px 10px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 6, fontSize: 12, cursor: "pointer" };
const alertStyle   = { padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, background: "#FEE2E2", color: "#B91C1C" };
