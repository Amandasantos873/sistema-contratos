// src/services/clienteService.js
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

export const clienteService = {
  listar: (params = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v != null && q.append(k, v));
    return request(`/clientes/?${q}`);
  },
  buscar:      (id)          => request(`/clientes/${id}`),
  criar:       (dados)       => request("/clientes/", { method: "POST", body: JSON.stringify(dados) }),
  atualizar:   (id, dados)   => request(`/clientes/${id}`, { method: "PATCH", body: JSON.stringify(dados) }),
  inativar:    (id, motivo)  => request(`/clientes/${id}/inativar`, { method: "PATCH", body: JSON.stringify({ motivo }) }),

  adicionarEndereco: (cid, dados) => request(`/clientes/${cid}/enderecos`, { method: "POST", body: JSON.stringify(dados) }),
  atualizarEndereco: (cid, eid, dados) => request(`/clientes/${cid}/enderecos/${eid}`, { method: "PATCH", body: JSON.stringify(dados) }),

  adicionarContato: (cid, dados) => request(`/clientes/${cid}/contatos`, { method: "POST", body: JSON.stringify(dados) }),
  atualizarContato: (cid, coid, dados) => request(`/clientes/${cid}/contatos/${coid}`, { method: "PATCH", body: JSON.stringify(dados) }),
  removerContato:   (cid, coid) => request(`/clientes/${cid}/contatos/${coid}`, { method: "DELETE" }),

  segmentos: () => request("/clientes/segmentos"),
  consultarCep: (cep) => request(`/clientes/cep/${cep}`),
};
