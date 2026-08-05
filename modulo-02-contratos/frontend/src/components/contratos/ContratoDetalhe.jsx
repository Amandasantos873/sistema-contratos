// src/components/contratos/ContratoDetalhe.jsx
"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { contratoService } from "../../services/contratoService";

const fmtMoeda = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const fmtData  = (d) => d ? new Date(d + "T00:00:00").toLocaleDateString("pt-BR") : "—";

const MODALIDADE_COR = { ASP: { bg: "#EFF6FF", text: "#1E40AF" }, BSP: { bg: "#F5F3FF", text: "#5B21B6" }, BPO: { bg: "#FFF7ED", text: "#C2410C" } };
const STATUS_COR     = { PROPOSTA: { bg: "#FEF3C7", text: "#92400E" }, ATIVO: { bg: "#DCFCE7", text: "#15803D" }, SUSPENSO: { bg: "#FEE2E2", text: "#B91C1C" }, ENCERRADO: { bg: "#F3F4F6", text: "#6B7280" }, CANCELADO: { bg: "#F3F4F6", text: "#9CA3AF" } };
const PARCELA_COR    = { PENDENTE: { bg: "#FEF3C7", text: "#92400E" }, FATURADA: { bg: "#EFF6FF", text: "#1E40AF" }, PAGA: { bg: "#DCFCE7", text: "#15803D" }, CANCELADA: { bg: "#F3F4F6", text: "#9CA3AF" } };
const DIA_LABEL      = { DIA_01: "1º dia útil", DIA_15: "Dia 15", DIA_25: "Dia 25" };

export default function ContratoDetalhe({ contratoId }) {
  const router = useRouter();
  const [contrato, setContrato] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [aba, setAba]           = useState("resumo");
  const [modalGoLive, setModalGoLive] = useState(false);
  const [dataGoLive, setDataGoLive]   = useState("");
  const [salvando, setSalvando]       = useState(false);
  const [erro, setErro]               = useState(null);

  const carregar = () => {
    setLoading(true);
    contratoService.buscar(contratoId)
      .then(setContrato)
      .catch((e) => setErro(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { carregar(); }, [contratoId]);

  const handleGoLive = async () => {
    if (!dataGoLive) return;
    setSalvando(true);
    try {
      await contratoService.registrarGoLive(contratoId, { data_goLive: dataGoLive });
      setModalGoLive(false);
      carregar();
    } catch (e) { setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleStatusParcela = async (parcela, novoStatus) => {
    const dados = { status: novoStatus };
    if (novoStatus === "PAGA") dados.data_pagamento = new Date().toISOString().split("T")[0];
    try {
      await contratoService.atualizarParcela(contratoId, parcela.id, dados);
      carregar();
    } catch (e) { alert(e.message); }
  };

  if (loading) return <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF" }}>Carregando...</div>;
  if (erro)    return <div style={{ padding: "2rem", color: "#B91C1C" }}>{erro}</div>;
  if (!contrato) return null;

  const c = contrato;
  const itensImpl  = c.itens?.filter(i => i.fase === "IMPLANTACAO" && i.ativo) ?? [];
  const itensRecorr= c.itens?.filter(i => i.fase === "RECORRENCIA"  && i.ativo) ?? [];
  const parcelas   = c.parcelas_impl ?? [];
  const progParcelas = parcelas.length > 0
    ? Math.round((parcelas.filter(p => p.status === "PAGA").length / parcelas.length) * 100)
    : 0;

  return (
    <div style={{ padding: "2rem", maxWidth: 960, margin: "0 auto" }}>
      <button onClick={() => router.back()} style={btnVoltarStyle}>← Voltar</button>

      {/* Cabeçalho */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", margin: "16px 0 20px" }}>
        <div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
            <span style={{ fontFamily: "monospace", fontSize: 16, fontWeight: 600, color: "#111827" }}>{c.numero}</span>
            <span style={{ ...badge, background: MODALIDADE_COR[c.modalidade]?.bg, color: MODALIDADE_COR[c.modalidade]?.text }}>{c.modalidade}</span>
            <span style={{ ...badge, background: STATUS_COR[c.status]?.bg, color: STATUS_COR[c.status]?.text }}>{c.status}</span>
            <span style={{ ...badge, background: "#F3F4F6", color: "#374151" }}>
              {c.fase_atual === "IMPLANTACAO" ? "🔧 Implantação" : "🔄 Recorrência"}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 14, color: "#6B7280" }}>
            <Link href={`/clientes/${c.cliente_id}`} style={{ color: "#1E40AF", textDecoration: "none" }}>
              {c.cliente_id}
            </Link>
            {" · "}Faturamento: {DIA_LABEL[c.dia_faturamento]}
            {" · "}Prazo: {c.prazo_meses} meses
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {c.fase_atual === "IMPLANTACAO" && c.status === "ATIVO" && !c.data_goLive && (
            <button onClick={() => setModalGoLive(true)} style={btnGoLiveStyle}>
              🚀 Registrar go-live
            </button>
          )}
          <Link href={`/contratos/${contratoId}/editar`} style={btnSecLinkStyle}>Editar</Link>
        </div>
      </div>

      {/* Cards de métricas */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: "1.5rem" }}>
        {[
          { label: "Total implantação", valor: fmtMoeda(c.valor_total_impl) },
          { label: "Mensalidade",       valor: fmtMoeda(c.valor_mensal) },
          { label: "Início impl.",      valor: fmtData(c.data_inicio_impl) },
          { label: "Go-live",           valor: fmtData(c.data_goLive) },
          { label: "Fim do contrato",   valor: fmtData(c.data_fim_contrato) },
        ].map(({ label, valor }) => (
          <div key={label} style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "12px 16px" }}>
            <p style={{ margin: 0, fontSize: 11, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</p>
            <p style={{ margin: "4px 0 0", fontSize: 15, fontWeight: 500, color: "#111827" }}>{valor}</p>
          </div>
        ))}
      </div>

      {/* Abas */}
      <div style={{ display: "flex", borderBottom: "2px solid #E5E7EB", marginBottom: "1.5rem" }}>
        {[
          { id: "resumo",   label: "Resumo" },
          { id: "itens",    label: `Itens (${c.itens?.filter(i=>i.ativo).length ?? 0})` },
          { id: "parcelas", label: `Parcelas impl. (${parcelas.length})` },
        ].map(a => (
          <button key={a.id} onClick={() => setAba(a.id)} style={{
            padding: "8px 18px", border: "none", background: "none", fontSize: 14,
            fontWeight: aba === a.id ? 600 : 400,
            color: aba === a.id ? "#1E40AF" : "#6B7280",
            borderBottom: aba === a.id ? "2px solid #1E40AF" : "2px solid transparent",
            cursor: "pointer", marginBottom: -2,
          }}>{a.label}</button>
        ))}
      </div>

      {/* ABA: Resumo */}
      {aba === "resumo" && (
        <div style={cardStyle}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
            {[
              ["Responsável comercial",   c.responsavel_comercial   || "—"],
              ["Responsável implantação", c.responsavel_implantacao || "—"],
              ["Nº proposta",             c.numero_proposta         || "—"],
              ["Data assinatura",         fmtData(c.data_assinatura)],
              ["Início recorrência",      fmtData(c.data_inicio_recorrencia)],
              ["Dia de faturamento",      DIA_LABEL[c.dia_faturamento]],
            ].map(([k, v]) => (
              <div key={k}>
                <p style={{ margin: 0, fontSize: 11, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.04em" }}>{k}</p>
                <p style={{ margin: "3px 0 0", fontSize: 14, color: "#111827" }}>{v}</p>
              </div>
            ))}
          </div>
          {c.observacoes && (
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #F3F4F6" }}>
              <p style={{ margin: 0, fontSize: 11, color: "#9CA3AF", textTransform: "uppercase" }}>Observações</p>
              <p style={{ margin: "4px 0 0", fontSize: 14, color: "#374151" }}>{c.observacoes}</p>
            </div>
          )}
        </div>
      )}

      {/* ABA: Itens */}
      {aba === "itens" && (
        <div>
          {[["IMPLANTACAO","🔧 Itens de implantação", itensImpl], ["RECORRENCIA","🔄 Itens recorrentes", itensRecorr]].map(([fase, titulo, lista]) => (
            <div key={fase} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", margin: "0 0 10px" }}>{titulo}</h3>
              {lista.length === 0 ? (
                <p style={{ fontSize: 13, color: "#9CA3AF" }}>Nenhum item.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
                  <thead><tr style={{ background: "#F9FAFB" }}>
                    {["Produto","Unidade","Qtd","Valor unit.","Desc.%","Total"].map(h => (
                      <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontWeight: 500, color: "#374151" }}>{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {lista.map(item => (
                      <tr key={item.id} style={{ borderTop: "1px solid #F3F4F6" }}>
                        <td style={{ padding: "10px 14px", color: "#111827" }}>{item.produto?.nome}</td>
                        <td style={{ padding: "10px 14px", color: "#6B7280" }}>{item.produto?.unidade}</td>
                        <td style={{ padding: "10px 14px", color: "#6B7280", fontFamily: "monospace" }}>{item.quantidade}</td>
                        <td style={{ padding: "10px 14px", fontFamily: "monospace" }}>{fmtMoeda(item.valor_unitario)}</td>
                        <td style={{ padding: "10px 14px", color: "#6B7280" }}>{item.desconto_pct}%</td>
                        <td style={{ padding: "10px 14px", fontFamily: "monospace", fontWeight: 500, color: "#1E40AF" }}>{fmtMoeda(item.valor_total)}</td>
                      </tr>
                    ))}
                    <tr style={{ borderTop: "2px solid #E5E7EB", background: "#F9FAFB" }}>
                      <td colSpan={5} style={{ padding: "8px 14px", fontWeight: 500, color: "#374151", textAlign: "right" }}>Total</td>
                      <td style={{ padding: "8px 14px", fontFamily: "monospace", fontWeight: 600, color: "#111827" }}>
                        {fmtMoeda(lista.reduce((a, i) => a + parseFloat(i.valor_total), 0))}
                      </td>
                    </tr>
                  </tbody>
                </table>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ABA: Parcelas */}
      {aba === "parcelas" && (
        <div>
          {parcelas.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#6B7280", marginBottom: 6 }}>
                <span>Progresso de pagamento</span>
                <span>{parcelas.filter(p => p.status === "PAGA").length}/{parcelas.length} pagas</span>
              </div>
              <div style={{ height: 8, background: "#E5E7EB", borderRadius: 4, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${progParcelas}%`, background: "#10B981", borderRadius: 4, transition: "width 0.3s" }} />
              </div>
            </div>
          )}
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
            <thead><tr style={{ background: "#F9FAFB" }}>
              {["Parcela","Valor","Vencimento","Status","Faturada em","Paga em","Ações"].map(h => (
                <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontWeight: 500, color: "#374151" }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {parcelas.map(p => (
                <tr key={p.id} style={{ borderTop: "1px solid #F3F4F6" }}>
                  <td style={{ padding: "10px 14px", fontWeight: 500 }}>{p.numero_parcela}</td>
                  <td style={{ padding: "10px 14px", fontFamily: "monospace" }}>{fmtMoeda(p.valor)}</td>
                  <td style={{ padding: "10px 14px", color: "#6B7280" }}>{fmtData(p.data_vencimento)}</td>
                  <td style={{ padding: "10px 14px" }}>
                    <span style={{ ...badge, background: PARCELA_COR[p.status]?.bg, color: PARCELA_COR[p.status]?.text }}>
                      {p.status}
                    </span>
                  </td>
                  <td style={{ padding: "10px 14px", color: "#6B7280", fontSize: 12 }}>{fmtData(p.data_faturamento)}</td>
                  <td style={{ padding: "10px 14px", color: "#6B7280", fontSize: 12 }}>{fmtData(p.data_pagamento)}</td>
                  <td style={{ padding: "10px 14px" }}>
                    {p.status === "PENDENTE" && (
                      <button onClick={() => handleStatusParcela(p, "PAGA")}
                        style={{ fontSize: 12, color: "#15803D", background: "none", border: "none", cursor: "pointer" }}>
                        Marcar paga
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Go-live */}
      {modalGoLive && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 380, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 8px" }}>🚀 Registrar go-live</h2>
            <p style={{ fontSize: 14, color: "#6B7280", margin: "0 0 16px" }}>
              Ao confirmar, o contrato entra na fase de recorrência e o faturamento mensal passa a ser gerado.
            </p>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#374151", marginBottom: 4 }}>Data do go-live *</label>
            <input type="date" value={dataGoLive} onChange={e => setDataGoLive(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 14, boxSizing: "border-box", marginBottom: 16 }} />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setModalGoLive(false)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleGoLive} disabled={!dataGoLive || salvando}
                style={{ ...btnSecStyle, background: "#1E40AF", color: "#fff", borderColor: "#1E40AF", opacity: !dataGoLive ? 0.5 : 1 }}>
                {salvando ? "Salvando..." : "Confirmar go-live"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const badge         = { padding: "2px 9px", borderRadius: 20, fontSize: 11, fontWeight: 500 };
const cardStyle     = { background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1.25rem" };
const btnVoltarStyle= { background: "none", border: "none", color: "#6B7280", fontSize: 13, cursor: "pointer", padding: 0 };
const btnSecStyle   = { padding: "7px 16px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const btnSecLinkStyle = { padding: "7px 16px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, textDecoration: "none", display: "inline-block" };
const btnGoLiveStyle  = { padding: "7px 16px", background: "#059669", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, cursor: "pointer", fontWeight: 500 };
