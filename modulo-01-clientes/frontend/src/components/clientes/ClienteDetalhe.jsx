// src/components/clientes/ClienteDetalhe.jsx
"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { clienteService } from "../../services/clienteService";
import {
  fmtDocumento, fmtTelefone, fmtCEP, fmtData,
  STATUS_LABEL, STATUS_COR, PORTE_LABEL,
} from "../../utils/formatters";

export default function ClienteDetalhe({ clienteId }) {
  const router = useRouter();
  const [cliente, setCliente]       = useState(null);
  const [loading, setLoading]       = useState(true);
  const [erro, setErro]             = useState(null);
  const [aba, setAba]               = useState("info");
  const [modalInativar, setModalInativar] = useState(false);
  const [motivoInativar, setMotivoInativar] = useState("");
  const [salvandoInativar, setSalvandoInativar] = useState(false);

  useEffect(() => {
    clienteService.buscar(clienteId)
      .then(setCliente)
      .catch((e) => setErro(e.message))
      .finally(() => setLoading(false));
  }, [clienteId]);

  const handleInativar = async () => {
    if (motivoInativar.length < 10) return;
    setSalvandoInativar(true);
    try {
      const atualizado = await clienteService.inativar(clienteId, motivoInativar);
      setCliente(atualizado);
      setModalInativar(false);
    } catch (e) {
      alert(e.message);
    } finally {
      setSalvandoInativar(false);
    }
  };

  if (loading) return <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF" }}>Carregando...</div>;
  if (erro)    return <div style={{ padding: "2rem", color: "#B91C1C" }}>{erro}</div>;
  if (!cliente) return null;

  const isPJ = cliente.tipo_pessoa === "PJ";
  const cor  = STATUS_COR[cliente.status] ?? {};
  const endAtivos  = cliente.enderecos?.filter((e) => e.ativo)  ?? [];
  const conAtivos  = cliente.contatos?.filter((c) => c.ativo)   ?? [];

  return (
    <div style={{ padding: "2rem", maxWidth: 960, margin: "0 auto" }}>

      {/* Voltar */}
      <button onClick={() => router.back()} style={btnVoltarStyle}>← Voltar</button>

      {/* Cabeçalho */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", margin: "16px 0 24px" }}>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <div style={{
            width: 52, height: 52, borderRadius: 12,
            background: "#EFF6FF", display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: 24,
          }}>
            {isPJ ? "🏢" : "👤"}
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: "#111827" }}>
              {isPJ ? cliente.razao_social : cliente.nome_completo}
            </h1>
            {cliente.nome_fantasia && (
              <p style={{ margin: "2px 0 0", fontSize: 14, color: "#6B7280" }}>{cliente.nome_fantasia}</p>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 6, alignItems: "center" }}>
              <span style={{
                padding: "3px 10px", borderRadius: 20, fontSize: 12, fontWeight: 500,
                background: cor.bg, color: cor.text,
              }}>
                {STATUS_LABEL[cliente.status]}
              </span>
              {cliente.segmento && (
                <span style={{ fontSize: 12, color: "#6B7280" }}>• {cliente.segmento?.nome ?? ""}</span>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <Link href={`/clientes/${clienteId}/editar`} style={btnSecLinkStyle}>Editar</Link>
          {cliente.status === "ATIVO" && (
            <button onClick={() => setModalInativar(true)} style={{ ...btnSecStyle, color: "#B91C1C", borderColor: "#FCA5A5" }}>
              Inativar
            </button>
          )}
        </div>
      </div>

      {/* Alertas */}
      {!conAtivos.some((c) => c.is_financeiro) && (
        <div style={{ background: "#FFFBEB", border: "1px solid #FDE68A", borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 13, color: "#92400E" }}>
          ⚠ Este cliente não possui contato financeiro cadastrado. Adicione um antes de emitir faturas.
        </div>
      )}

      {/* Abas */}
      <div style={{ display: "flex", borderBottom: "2px solid #E5E7EB", marginBottom: "1.5rem" }}>
        {[
          { id: "info",      label: "Informações" },
          { id: "enderecos", label: `Endereços (${endAtivos.length})` },
          { id: "contatos",  label: `Contatos (${conAtivos.length})` },
        ].map((a) => (
          <button key={a.id} onClick={() => setAba(a.id)} style={{
            padding: "8px 18px", border: "none", background: "none", fontSize: 14,
            fontWeight: aba === a.id ? 600 : 400,
            color: aba === a.id ? "#1E40AF" : "#6B7280",
            borderBottom: aba === a.id ? "2px solid #1E40AF" : "2px solid transparent",
            cursor: "pointer", marginBottom: -2,
          }}>
            {a.label}
          </button>
        ))}
      </div>

      {/* ABA: Informações */}
      {aba === "info" && (
        <div style={cardStyle}>
          <Grade>
            <Info label="Tipo"       value={isPJ ? "Pessoa Jurídica" : "Pessoa Física"} />
            <Info label="Documento"  value={fmtDocumento(cliente.tipo_pessoa, isPJ ? cliente.cnpj : cliente.cpf)} mono />
            {isPJ && <Info label="Insc. estadual"  value={cliente.inscricao_estadual  || "—"} />}
            {isPJ && <Info label="Insc. municipal" value={cliente.inscricao_municipal || "—"} />}
            <Info label="Porte"    value={PORTE_LABEL[cliente.porte] ?? "—"} />
            <Info label="Origem"   value={cliente.origem      || "—"} />
            <Info label="Cadastro" value={fmtData(cliente.criado_em)} />
          </Grade>
          {cliente.observacoes && (
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #F3F4F6" }}>
              <span style={labelInfoStyle}>Observações</span>
              <p style={{ margin: "4px 0 0", fontSize: 14, color: "#374151" }}>{cliente.observacoes}</p>
            </div>
          )}
          {cliente.motivo_inativacao && (
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #F3F4F6" }}>
              <span style={{ ...labelInfoStyle, color: "#B91C1C" }}>Motivo da inativação</span>
              <p style={{ margin: "4px 0 0", fontSize: 14, color: "#374151" }}>{cliente.motivo_inativacao}</p>
              <p style={{ margin: "4px 0 0", fontSize: 12, color: "#9CA3AF" }}>em {fmtData(cliente.inativado_em)} por {cliente.inativado_por}</p>
            </div>
          )}
        </div>
      )}

      {/* ABA: Endereços */}
      {aba === "enderecos" && (
        <div>
          {endAtivos.length === 0 ? (
            <p style={{ color: "#9CA3AF", fontSize: 14 }}>Nenhum endereço cadastrado.</p>
          ) : endAtivos.map((e) => (
            <div key={e.id} style={{ ...cardStyle, marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "#6B7280", textTransform: "uppercase" }}>
                  {e.tipo} {e.principal && "⭐"}
                </span>
              </div>
              <p style={{ margin: 0, fontSize: 14, color: "#111827" }}>
                {e.logradouro}, {e.numero}{e.complemento ? ` — ${e.complemento}` : ""}
              </p>
              <p style={{ margin: "2px 0 0", fontSize: 14, color: "#6B7280" }}>
                {e.bairro} · {e.cidade}/{e.uf} · CEP {fmtCEP(e.cep)}
              </p>
            </div>
          ))}
          <Link href={`/clientes/${clienteId}/editar?aba=enderecos`} style={btnAddLinkStyle}>
            + Adicionar endereço
          </Link>
        </div>
      )}

      {/* ABA: Contatos */}
      {aba === "contatos" && (
        <div>
          {conAtivos.length === 0 ? (
            <p style={{ color: "#9CA3AF", fontSize: 14 }}>Nenhum contato cadastrado.</p>
          ) : conAtivos.map((c) => (
            <div key={c.id} style={{ ...cardStyle, marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <p style={{ margin: 0, fontWeight: 500, fontSize: 15, color: "#111827" }}>
                    {c.nome} {c.principal && "⭐"}
                  </p>
                  {(c.cargo || c.departamento) && (
                    <p style={{ margin: "2px 0 4px", fontSize: 13, color: "#6B7280" }}>
                      {[c.cargo, c.departamento].filter(Boolean).join(" · ")}
                    </p>
                  )}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                    {c.email    && <span style={tagStyle}>{c.email}</span>}
                    {c.telefone && <span style={tagStyle}>{fmtTelefone(c.telefone)}</span>}
                    {c.whatsapp && <span style={tagStyle}>WhatsApp: {fmtTelefone(c.whatsapp)}</span>}
                  </div>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, justifyContent: "flex-end" }}>
                  {c.is_financeiro && <Badge cor="#DCFCE7" texto="💰 Financeiro" />}
                  {c.is_contrato   && <Badge cor="#EFF6FF" texto="📋 Contrato" />}
                  {c.is_tecnico    && <Badge cor="#FEF3C7" texto="🔧 Técnico" />}
                  {c.is_comercial  && <Badge cor="#F5F3FF" texto="🤝 Comercial" />}
                </div>
              </div>
            </div>
          ))}
          <Link href={`/clientes/${clienteId}/editar?aba=contatos`} style={btnAddLinkStyle}>
            + Adicionar contato
          </Link>
        </div>
      )}

      {/* Modal inativar */}
      {modalInativar && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
        }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "1.5rem", width: 420, maxWidth: "90vw" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 8px", color: "#111827" }}>Inativar cliente</h2>
            <p style={{ fontSize: 14, color: "#6B7280", margin: "0 0 16px" }}>
              Informe o motivo da inativação. Esta ação pode ser revertida.
            </p>
            <textarea
              value={motivoInativar}
              onChange={(e) => setMotivoInativar(e.target.value)}
              rows={4}
              placeholder="Descreva o motivo (mínimo 10 caracteres)..."
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 14, boxSizing: "border-box", resize: "vertical" }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
              <button onClick={() => setModalInativar(false)} style={btnSecStyle}>Cancelar</button>
              <button
                onClick={handleInativar}
                disabled={motivoInativar.length < 10 || salvandoInativar}
                style={{ ...btnSecStyle, background: "#B91C1C", color: "#fff", borderColor: "#B91C1C", opacity: motivoInativar.length < 10 ? 0.5 : 1 }}
              >
                {salvandoInativar ? "Salvando..." : "Confirmar inativação"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Componentes auxiliares
function Info({ label, value, mono }) {
  return (
    <div>
      <span style={labelInfoStyle}>{label}</span>
      <p style={{ margin: "3px 0 0", fontSize: 14, color: "#111827", fontFamily: mono ? "monospace" : undefined }}>
        {value || "—"}
      </p>
    </div>
  );
}
function Grade({ children }) {
  return <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 16 }}>{children}</div>;
}
function Badge({ cor, texto }) {
  return <span style={{ padding: "2px 8px", background: cor, borderRadius: 20, fontSize: 11, fontWeight: 500, color: "#374151" }}>{texto}</span>;
}

const cardStyle       = { background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, padding: "1.25rem" };
const labelInfoStyle  = { fontSize: 12, fontWeight: 500, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.04em" };
const tagStyle        = { fontSize: 12, background: "#F3F4F6", color: "#374151", padding: "2px 8px", borderRadius: 6 };
const btnVoltarStyle  = { background: "none", border: "none", color: "#6B7280", fontSize: 13, cursor: "pointer", padding: 0 };
const btnSecStyle     = { padding: "7px 16px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, cursor: "pointer" };
const btnSecLinkStyle = { padding: "7px 16px", background: "#fff", color: "#374151", border: "1px solid #D1D5DB", borderRadius: 8, fontSize: 13, textDecoration: "none", display: "inline-block" };
const btnAddLinkStyle = { display: "inline-block", marginTop: 8, padding: "8px 16px", background: "#EFF6FF", color: "#1E40AF", border: "1px dashed #93C5FD", borderRadius: 8, fontSize: 13, textDecoration: "none" };
