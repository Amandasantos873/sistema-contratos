// ================================================================
// src/services/contratoService.js
// ================================================================
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const contratoService = {
  listar:   (params = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v != null && q.append(k, v));
    return request(`/contratos/?${q}`);
  },
  buscar:          (id)          => request(`/contratos/${id}`),
  criar:           (dados)       => request("/contratos/", { method: "POST", body: JSON.stringify(dados) }),
  atualizar:       (id, dados)   => request(`/contratos/${id}`, { method: "PATCH", body: JSON.stringify(dados) }),
  registrarGoLive: (id, dados)   => request(`/contratos/${id}/go-live`, { method: "PATCH", body: JSON.stringify(dados) }),
  aFaturar:        (dia)         => request(`/contratos/a-faturar?dia_faturamento=${dia}`),

  adicionarItem:  (cid, dados)        => request(`/contratos/${cid}/itens`, { method: "POST", body: JSON.stringify(dados) }),
  removerItem:    (cid, iid)          => request(`/contratos/${cid}/itens/${iid}`, { method: "DELETE" }),

  adicionarParcela: (cid, dados)       => request(`/contratos/${cid}/parcelas`, { method: "POST", body: JSON.stringify(dados) }),
  atualizarParcela: (cid, pid, dados)  => request(`/contratos/${cid}/parcelas/${pid}`, { method: "PATCH", body: JSON.stringify(dados) }),

  produtos: (modalidade, fase) => {
    const q = new URLSearchParams();
    if (modalidade) q.append("modalidade", modalidade);
    if (fase) q.append("fase", fase);
    return request(`/contratos/produtos?${q}`);
  },
};
