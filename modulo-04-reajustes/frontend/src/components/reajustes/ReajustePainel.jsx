// src/components/reajustes/ReajustePainel.jsx
"use client";
import { useState, useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...opts })
    .then(r => r.ok ? (r.status === 204 ? null : r.json()) : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const fmtData  = (d) => d ? new Date(d + "T00:00:00").toLocaleDateString("pt-BR") : "—";
const fmtPct   = (v) => v != null ? `${Number(v).toFixed(4)}%` : "—";

const STATUS_COR = {
  CALCULADO:            { bg: "#F3F4F6", text: "#374151" },
  AGUARDANDO_APROVACAO: { bg: "#FEF3C7", text: "#92400E" },
  APROVADO:             { bg: "#DBEAFE", text: "#1E40AF" },
  REPROVADO:            { bg: "#FEE2E2", text: "#B91C1C" },
  COMUNICADO:           { bg: "#EDE9FE", text: "#5B21B6" },
  EFETIVADO:            { bg: "#DCFCE7", text: "#15803D" },
  CANCELADO:            { bg: "#F3F4F6", text: "#9CA3AF" },
};

const STATUS_LABEL = {
  CALCULADO:            "Calculado",
  AGUARDANDO_APROVACAO: "Aguard. aprovação",
  APROVADO:             "Aprovado",
  REPROVADO:            "Reprovado",
  COMUNICADO:           "Comunicado",
  EFETIVADO:            "Efetivado",
  CANCELADO:            "Cancelado",
};

const PROXIMAS_ACOES = {
  CALCULADO:            { label: "Enviar para aprovação", acao: "enviar-aprovacao" },
  AGUARDANDO_APROVACAO: { label: "Aprovar", acao: "aprovar" },
  APROVADO:             { label: "Registrar comunicação", acao: "comunicar" },
  COMUNICADO:           { label: "Efetivar", acao: "efetivar" },
};

export default function ReajustePainel() {
  const [pendentes, setPendentes] = useState([]);
  const [loading, setLoading]     = useState(false);
  const [apenasVencidos, setApenasVencidos] = useState(false);

  // Modal calcular
  const [modalCalc, setModalCalc] = useState(null);
  const [formCalc, setFormCalc]   = useState({ indice: "INPC", data_efetivacao: "" });

  // Modal reajuste selecionado
  const [reajusteSel, setReajusteSel] = useState(null);
  const [itensReajuste, setItensReajuste] = useState([]);
  const [motivoReprovacao, setMotivoReprovacao] = useState("");
  const [dataComunicacao, setDataComunicacao]   = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro]         = useState(null);

  const carregar = async () => {
    setLoading(true);
    try {
      const res = await api(`/reajustes/pendentes?apenas_vencidos=${apenasVencidos}`);
      setPendentes(res);
    } catch (e) { setErro(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { carregar(); }, [apenasVencidos]);

  const abrirReajusteContrato = async (contratoId) => {
    try {
      const lista = await api(`/reajustes/contrato/${contratoId}`);
      const ultimo = lista[lista.length - 1];
      if (ultimo) {
        setReajusteSel(ultimo);
        setItensReajuste(ultimo.itens || []);
      }
    } catch (e) { setErro(e.message); }
  };

  const handleCalcular = async () => {
    if (!modalCalc || !formCalc.data_efetivacao) return;
    setSalvando(true);
    try {
      const res = await api("/reajustes", {
        method: "POST",
        body: JSON.stringify({
          contrato_id:     modalCalc.contrato_id,
          indice:          formCalc.indice,
          data_efetivacao: formCalc.data_efetivacao,
        }),
      });
      setReajusteSel(res);
      setItensReajuste(res.itens || []);
      setModalCalc(null);
      carregar();
    } catch (e) { setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleAcao = async (acao) => {
    if (!reajusteSel) return;
    setSalvando(true);
    setErro(null);
    try {
      let body = {};
      if (acao === "aprovar")   body = { itens: [] };
      if (acao === "reprovar")  body = { motivo: motivoReprovacao };
      if (acao === "comunicar") body = { data_comunicacao: dataComunicacao };

      const res = await api(`/reajustes/${reajusteSel.id}/${acao}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setReajusteSel(res);
      setItensReajuste(res.itens || []);
      carregar();
    } catch (e) { setErro(e.message); }
    finally { setSalvando(false); }
  };

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>

      {/* Cabeçalho */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: "#111827" }}>Reajustes contratuais</h1>
          <p style={{ margin: "3px 0 0", fontSize: 13, color: "#6B7280" }}>
            {pendentes.length} contrato(s) monitorado(s)
          </p>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
          <input type="checkbox" checked={apenasVencidos} onChange={e => setApenasVencidos(e.target.checked)} />
          Mostrar apenas vencidos
        </label>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={() => setErro(null)} style={btnFecharStyle}>✕</button></div>}

      {/* Layout: tabela + painel lateral */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Tabela de pendentes */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
            {loading ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF", fontSize: 14 }}>Carregando...</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#F9FAFB", borderBottom: "1px solid #E5E7EB" }}>
                    {["Contrato","Cliente","Modalidade","Mensalidade","Próx. reajuste","Atraso","Situação",""].map(h => (
                      <th key={h} style={{ padding: "9px 12px", textAlign: "left", fontWeight: 500, color: "#374151", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pendentes.map((p, i) => {
                    const vencido = p.dias_atraso > 0;
                    const emAndamento = !!p.status_em_andamento;
                    return (
                      <tr key={p.contrato_id}
                        onClick={() => emAndamento && abrirReajusteContrato(p.contrato_id)}
                        style={{
                          borderBottom: "1px solid #F3F4F6",
                          background: i % 2 === 0 ? "#fff" : "#FAFAFA",
                          cursor: emAndamento ? "pointer" : "default",
                        }}>
                        <td style={{ padding: "10px 12px", fontFamily: "monospace", fontWeight: 500, color: "#374151" }}>{p.contrato_numero}</td>
                        <td style={{ padding: "10px 12px", color: "#111827" }}>{p.cliente_nome}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <span style={{ ...badge, background: "#EFF6FF", color: "#1E40AF" }}>{p.modalidade}</span>
                        </td>
                        <td style={{ padding: "10px 12px", fontFamily: "monospace" }}>{fmtMoeda(p.valor_mensal)}</td>
                        <td style={{ padding: "10px 12px", color: vencido ? "#B91C1C" : "#374151" }}>
                          {fmtData(p.proximo_reajuste)}
                        </td>
                        <td style={{ padding: "10px 12px" }}>
                          {vencido ? (
                            <span style={{ color: "#B91C1C", fontWeight: 500 }}>+{p.dias_atraso}d</span>
                          ) : (
                            <span style={{ color: "#9CA3AF" }}>{Math.abs(p.dias_atraso)}d</span>
                          )}
                        </td>
                        <td style={{ padding: "10px 12px" }}>
                          {emAndamento ? (
                            <span style={{ ...badge, background: STATUS_COR[p.status_em_andamento]?.bg, color: STATUS_COR[p.status_em_andamento]?.text }}>
                              {STATUS_LABEL[p.status_em_andamento]}
                            </span>
                          ) : (
                            <span style={{ color: "#9CA3AF", fontSize: 12 }}>Sem reajuste</span>
                          )}
                        </td>
                        <td style={{ padding: "10px 12px" }} onClick={e => e.stopPropagation()}>
                          {!emAndamento ? (
                            <button onClick={() => setModalCalc(p)} style={btnSmStyle}>Calcular</button>
                          ) : (
                            <button onClick={() => abrirReajusteContrato(p.contrato_id)} style={btnSmStyle}>Ver</button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Painel lateral: detalhe do reajuste */}
        {reajusteSel && (
          <div style={{ width: 360, flexShrink: 0, background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <div>
                <p style={{ margin: 0, fontSize: 12, color: "#9CA3AF" }}>Reajuste {reajusteSel.numero_reajuste}º</p>
                <span style={{ ...badge, background: STATUS_COR[reajusteSel.status]?.bg, color: STATUS_COR[reajusteSel.status]?.text }}>
                  {STATUS_LABEL[reajusteSel.status]}
                </span>
              </div>
              <button onClick={() => setReajusteSel(null)} style={btnFecharStyle}>✕</button>
            </div>

            {/* Resumo financeiro */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
              {[
                ["Índice",       reajusteSel.indice],
                ["% calculado",  fmtPct(reajusteSel.percentual_calculado)],
                ["% aplicado",   fmtPct(reajusteSel.percentual_aplicado)],
                ["Efetivação",   fmtData(reajusteSel.data_efetivacao)],
                ["Atual",        fmtMoeda(reajusteSel.valor_mensal_anterior)],
                ["Novo",         fmtMoeda(reajusteSel.valor_mensal_novo)],
              ].map(([k, v]) => (
                <div key={k} style={{ background: "#F9FAFB", padding: "8px 10px", borderRadius: 8 }}>
                  <p style={{ margin: 0, fontSize: 11, color: "#9CA3AF" }}>{k}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 13, fontWeight: 500, color: "#111827" }}>{v}</p>
                </div>
              ))}
            </div>

            {/* Itens */}
            <p style={{ fontSize: 12, fontWeight: 600, color: "#374151", margin: "0 0 8px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Itens
            </p>
            <div style={{ maxHeight: 200, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
              {itensReajuste.map(item => (
                <div key={item.id} style={{ padding: "8px 10px", background: item.usa_dissidio ? "#FFF7ED" : "#F9FAFB", borderRadius: 8, border: "1px solid #F3F4F6" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 12, color: "#374151" }}>
                      {item.usa_dissidio ? "🤝 Mão de obra (dissídio)" : "📦 Item padrão"}
                    </span>
                    <span style={{ fontSize: 11, color: "#6B7280" }}>{fmtPct(item.percentual_aplicado)}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 3 }}>
                    <span style={{ fontSize: 12, color: "#9CA3AF" }}>{fmtMoeda(item.valor_anterior)}</span>
                    <span style={{ fontSize: 12, fontWeight: 500, color: "#15803D" }}>→ {fmtMoeda(item.valor_novo)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Ações do fluxo */}
            {PROXIMAS_ACOES[reajusteSel.status] && (
              <div>
                {reajusteSel.status === "AGUARDANDO_APROVACAO" && (
                  <div style={{ marginBottom: 8 }}>
                    <button onClick={() => handleAcao("aprovar")} disabled={salvando}
                      style={{ ...btnPrimStyle, width: "100%", marginBottom: 6 }}>
                      {salvando ? "Salvando..." : "✓ Aprovar reajuste"}
                    </button>
                    <div>
                      <input
                        placeholder="Motivo da reprovação..."
                        value={motivoReprovacao}
                        onChange={e => setMotivoReprovacao(e.target.value)}
                        style={{ ...inputStyle, marginBottom: 4 }}
                      />
                      <button
                        onClick={() => handleAcao("reprovar")}
                        disabled={motivoReprovacao.length < 10 || salvando}
                        style={{ ...btnDangerStyle, width: "100%", opacity: motivoReprovacao.length < 10 ? 0.5 : 1 }}>
                        ✕ Reprovar
                      </button>
                    </div>
                  </div>
                )}

                {reajusteSel.status === "APROVADO" && (
                  <div>
                    <label style={{ fontSize: 12, color: "#374151", display: "block", marginBottom: 4 }}>Data da comunicação ao cliente</label>
                    <input type="date" value={dataComunicacao} onChange={e => setDataComunicacao(e.target.value)} style={{ ...inputStyle, marginBottom: 6 }} />
                    <button onClick={() => handleAcao("comunicar")} disabled={!dataComunicacao || salvando}
                      style={{ ...btnPrimStyle, width: "100%", opacity: !dataComunicacao ? 0.5 : 1 }}>
                      {salvando ? "Salvando..." : "📧 Registrar comunicação"}
                    </button>
                  </div>
                )}

                {reajusteSel.status === "COMUNICADO" && (
                  <button onClick={() => handleAcao("efetivar")} disabled={salvando}
                    style={{ ...btnPrimStyle, width: "100%", background: "#059669" }}>
                    {salvando ? "Salvando..." : "⚡ Efetivar reajuste"}
                  </button>
                )}

                {reajusteSel.status === "CALCULADO" && (
                  <button onClick={() => handleAcao("enviar-aprovacao")} disabled={salvando}
                    style={{ ...btnPrimStyle, width: "100%" }}>
                    {salvando ? "Salvando..." : "→ Enviar para aprovação"}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal: Calcular reajuste */}
      {modalCalc && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 400, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 4px" }}>Calcular reajuste</h2>
            <p style={{ fontSize: 13, color: "#6B7280", margin: "0 0 16px" }}>{modalCalc.cliente_nome} · {modalCalc.contrato_numero}</p>

            <label style={labelStyle}>Índice *</label>
            <select value={formCalc.indice} onChange={e => setFormCalc(f => ({...f, indice: e.target.value}))} style={inputStyle}>
              <option value="INPC">INPC (principal)</option>
              <option value="IPCA">IPCA</option>
              <option value="IGPM">IGPM</option>
              <option value="FIXO">Fixo (negociado)</option>
            </select>

            <label style={{ ...labelStyle, marginTop: 12 }}>Data de efetivação *</label>
            <input type="date" value={formCalc.data_efetivacao}
              onChange={e => setFormCalc(f => ({...f, data_efetivacao: e.target.value}))}
              style={inputStyle} />

            <p style={{ fontSize: 12, color: "#9CA3AF", margin: "10px 0 14px" }}>
              Itens de mão de obra alocada (BPO) serão calculados automaticamente pelo dissídio da categoria.
            </p>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setModalCalc(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleCalcular} disabled={!formCalc.data_efetivacao || salvando} style={btnPrimStyle}>
                {salvando ? "Calculando..." : "Calcular"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const badge          = { padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 500 };
const inputStyle     = { padding: "7px 11px", border: "1px solid #D1D5DB", borderRadius: 7, fontSize: 14, width: "100%", boxSizing: "border-box", color: "#111827", display: "block" };
const labelStyle     = { display: "block", fontSize: 12, fontWeight: 500, color: "#374151", marginBottom: 4 };
const btnPrimStyle   = { padding: "9px 18px", background: "#1E40AF", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer" };
const btnSecStyle    = { padding: "9px 16px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const btnSmStyle     = { padding: "4px 10px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 6, fontSize: 12, cursor: "pointer" };
const btnDangerStyle = { padding: "8px 16px", background: "#B91C1C", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const btnFecharStyle = { background: "none", border: "none", color: "#9CA3AF", cursor: "pointer", fontSize: 15 };
const alertStyle     = { padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, background: "#FEE2E2", color: "#B91C1C", display: "flex", justifyContent: "space-between" };
