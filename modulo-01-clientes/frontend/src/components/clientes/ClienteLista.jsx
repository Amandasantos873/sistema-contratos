// src/components/clientes/ClienteLista.jsx
"use client";
import { useState } from "react";
import Link from "next/link";
import { useClientes, useSegmentos } from "../../hooks/useClientes";
import { fmtDocumento, fmtData, STATUS_LABEL, STATUS_COR, PORTE_LABEL } from "../../utils/formatters";

const ICONE_TIPO = { PJ: "🏢", PF: "👤" };

export default function ClienteLista() {
  const [busca, setBusca]     = useState("");
  const [buscaAtiva, setBuscaAtiva] = useState("");
  const segmentos = useSegmentos();

  const { dados, meta, filtros, loading, erro, atualizar } = useClientes();

  const handleBusca = (e) => {
    e.preventDefault();
    atualizar({ busca: buscaAtiva || undefined });
  };

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>

      {/* Cabeçalho */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0, color: "#111827" }}>Clientes</h1>
          <p style={{ margin: "4px 0 0", fontSize: 14, color: "#6B7280" }}>
            {meta.total} {meta.total === 1 ? "cliente cadastrado" : "clientes cadastrados"}
          </p>
        </div>
        <Link href="/clientes/novo" style={{
          background: "#1E40AF", color: "#fff", padding: "8px 18px",
          borderRadius: 8, textDecoration: "none", fontSize: 14, fontWeight: 500,
          display: "flex", alignItems: "center", gap: 6,
        }}>
          + Novo cliente
        </Link>
      </div>

      {/* Filtros */}
      <div style={{
        background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10,
        padding: "1rem 1.25rem", marginBottom: "1rem",
        display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end",
      }}>
        {/* Busca */}
        <form onSubmit={handleBusca} style={{ display: "flex", gap: 8, flex: "1 1 280px" }}>
          <input
            value={buscaAtiva}
            onChange={(e) => setBuscaAtiva(e.target.value)}
            placeholder="Buscar por nome, fantasia ou CNPJ/CPF..."
            style={inputStyle}
          />
          <button type="submit" style={btnSecStyle}>Buscar</button>
          {filtros.busca && (
            <button type="button" onClick={() => { setBuscaAtiva(""); atualizar({ busca: undefined }); }} style={btnSecStyle}>
              ✕
            </button>
          )}
        </form>

        {/* Status */}
        <select
          value={filtros.status || ""}
          onChange={(e) => atualizar({ status: e.target.value || undefined })}
          style={{ ...inputStyle, maxWidth: 150 }}
        >
          <option value="">Todos os status</option>
          <option value="PROSPECTO">Prospecto</option>
          <option value="ATIVO">Ativo</option>
          <option value="INATIVO">Inativo</option>
          <option value="BLOQUEADO">Bloqueado</option>
        </select>

        {/* Tipo */}
        <select
          value={filtros.tipo_pessoa || ""}
          onChange={(e) => atualizar({ tipo_pessoa: e.target.value || undefined })}
          style={{ ...inputStyle, maxWidth: 150 }}
        >
          <option value="">PF e PJ</option>
          <option value="PJ">Pessoa Jurídica</option>
          <option value="PF">Pessoa Física</option>
        </select>

        {/* Segmento */}
        <select
          value={filtros.segmento_id || ""}
          onChange={(e) => atualizar({ segmento_id: e.target.value || undefined })}
          style={{ ...inputStyle, maxWidth: 180 }}
        >
          <option value="">Todos os segmentos</option>
          {segmentos.map((s) => (
            <option key={s.id} value={s.id}>{s.nome}</option>
          ))}
        </select>
      </div>

      {/* Erro */}
      {erro && (
        <div style={{ background: "#FEE2E2", color: "#B91C1C", padding: "12px 16px", borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {erro}
        </div>
      )}

      {/* Tabela */}
      <div style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF", fontSize: 14 }}>
            Carregando...
          </div>
        ) : dados.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#9CA3AF", fontSize: 14 }}>
            Nenhum cliente encontrado.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ background: "#F9FAFB", borderBottom: "1px solid #E5E7EB" }}>
                {["Cliente", "Documento", "Segmento", "Localidade", "Contato financeiro", "Status", ""].map((h) => (
                  <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 500, color: "#374151", fontSize: 13, whiteSpace: "nowrap" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dados.map((c, i) => (
                <tr key={c.id} style={{ borderBottom: "1px solid #F3F4F6", background: i % 2 === 0 ? "#fff" : "#FAFAFA" }}>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 18 }}>{ICONE_TIPO[c.tipo_pessoa]}</span>
                      <div>
                        <div style={{ fontWeight: 500, color: "#111827" }}>{c.nome_principal}</div>
                        {c.nome_fantasia && (
                          <div style={{ fontSize: 12, color: "#9CA3AF" }}>{c.nome_fantasia}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: "12px 16px", color: "#6B7280", fontFamily: "monospace", fontSize: 13 }}>
                    {c.documento ? fmtDocumento(c.tipo_pessoa, c.documento) : "—"}
                  </td>
                  <td style={{ padding: "12px 16px", color: "#6B7280" }}>
                    {c.segmento || "—"}
                  </td>
                  <td style={{ padding: "12px 16px", color: "#6B7280" }}>
                    {c.cidade_uf || "—"}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    {c.contato_financeiro ? (
                      <div>
                        <div style={{ color: "#374151", fontSize: 13 }}>{c.contato_financeiro}</div>
                        {c.email_financeiro && (
                          <div style={{ fontSize: 12, color: "#6B7280" }}>{c.email_financeiro}</div>
                        )}
                      </div>
                    ) : (
                      <span style={{ color: "#EF4444", fontSize: 12 }}>⚠ Sem contato financeiro</span>
                    )}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{
                      padding: "3px 10px", borderRadius: 20, fontSize: 12, fontWeight: 500,
                      background: STATUS_COR[c.status]?.bg,
                      color: STATUS_COR[c.status]?.text,
                    }}>
                      {STATUS_LABEL[c.status]}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <Link href={`/clientes/${c.id}`} style={{ color: "#1E40AF", fontSize: 13, textDecoration: "none", whiteSpace: "nowrap" }}>
                      Ver detalhes →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginação */}
      {meta.paginas > 1 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, fontSize: 13, color: "#6B7280" }}>
          <span>
            Exibindo {((meta.pagina - 1) * meta.por_pagina) + 1}–{Math.min(meta.pagina * meta.por_pagina, meta.total)} de {meta.total}
          </span>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              disabled={meta.pagina === 1}
              onClick={() => atualizar({ pagina: meta.pagina - 1 })}
              style={{ ...btnSecStyle, opacity: meta.pagina === 1 ? 0.4 : 1 }}
            >
              ← Anterior
            </button>
            {Array.from({ length: Math.min(meta.paginas, 7) }, (_, i) => {
              const p = i + 1;
              return (
                <button
                  key={p}
                  onClick={() => atualizar({ pagina: p })}
                  style={{
                    ...btnSecStyle,
                    background: p === meta.pagina ? "#1E40AF" : undefined,
                    color: p === meta.pagina ? "#fff" : undefined,
                    borderColor: p === meta.pagina ? "#1E40AF" : undefined,
                    minWidth: 34,
                  }}
                >
                  {p}
                </button>
              );
            })}
            <button
              disabled={meta.pagina === meta.paginas}
              onClick={() => atualizar({ pagina: meta.pagina + 1 })}
              style={{ ...btnSecStyle, opacity: meta.pagina === meta.paginas ? 0.4 : 1 }}
            >
              Próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Estilos inline reutilizáveis
const inputStyle = {
  padding: "7px 12px", borderRadius: 7, border: "1px solid #D1D5DB",
  fontSize: 14, outline: "none", background: "#fff", color: "#111827",
  flex: 1, minWidth: 0,
};

const btnSecStyle = {
  padding: "7px 14px", borderRadius: 7, border: "1px solid #D1D5DB",
  fontSize: 13, background: "#fff", cursor: "pointer", color: "#374151",
  whiteSpace: "nowrap",
};
