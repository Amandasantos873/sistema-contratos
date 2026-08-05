// src/pages/clientes/novo.jsx  — Cadastro
import ClienteForm from "../../components/clientes/ClienteForm";
export default function NovoClientePage() {
  return <ClienteForm />;
}


// ----------------------------------------------------------------
// src/pages/clientes/[id]/index.jsx  — Detalhe
// ----------------------------------------------------------------
// import ClienteDetalhe from "../../../components/clientes/ClienteDetalhe";
// export default function ClienteDetalhePage({ params }) {
//   return <ClienteDetalhe clienteId={params.id} />;
// }


// ----------------------------------------------------------------
// src/pages/clientes/[id]/editar.jsx  — Edição
// ----------------------------------------------------------------
// "use client";
// import { useState, useEffect } from "react";
// import ClienteForm from "../../../components/clientes/ClienteForm";
// import { clienteService } from "../../../services/clienteService";
//
// export default function EditarClientePage({ params }) {
//   const [cliente, setCliente] = useState(null);
//
//   useEffect(() => {
//     clienteService.buscar(params.id).then(setCliente);
//   }, [params.id]);
//
//   if (!cliente) return <div style={{ padding: "2rem" }}>Carregando...</div>;
//   return <ClienteForm clienteInicial={cliente} />;
// }
