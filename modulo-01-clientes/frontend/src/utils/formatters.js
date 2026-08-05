// src/utils/formatters.js

export const fmtCNPJ = (v = "") =>
  v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");

export const fmtCPF = (v = "") =>
  v.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, "$1.$2.$3-$4");

export const fmtDocumento = (tipo, doc = "") =>
  tipo === "PJ" ? fmtCNPJ(doc) : fmtCPF(doc);

export const fmtTelefone = (v = "") => {
  const d = v.replace(/\D/g, "");
  return d.length === 11
    ? d.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3")
    : d.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");
};

export const fmtCEP = (v = "") => v.replace(/^(\d{5})(\d{3})$/, "$1-$2");

export const fmtData = (iso) =>
  iso ? new Date(iso).toLocaleDateString("pt-BR") : "—";

export const STATUS_LABEL = {
  PROSPECTO: "Prospecto",
  ATIVO:     "Ativo",
  INATIVO:   "Inativo",
  BLOQUEADO: "Bloqueado",
};

export const STATUS_COR = {
  PROSPECTO: { bg: "#EEF2FF", text: "#4338CA" },
  ATIVO:     { bg: "#DCFCE7", text: "#15803D" },
  INATIVO:   { bg: "#F3F4F6", text: "#6B7280" },
  BLOQUEADO: { bg: "#FEE2E2", text: "#B91C1C" },
};

export const PORTE_LABEL = {
  MEI:     "MEI",
  MICRO:   "Micro",
  PEQUENO: "Pequeno",
  MEDIO:   "Médio",
  GRANDE:  "Grande",
};

export const UFS = [
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA",
  "MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN",
  "RS","RO","RR","SC","SP","SE","TO",
];
