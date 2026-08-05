// src/hooks/useClientes.js
import { useState, useEffect, useCallback } from "react";
import { clienteService } from "../services/clienteService";

export function useClientes(filtrosIniciais = {}) {
  const [dados, setDados]       = useState([]);
  const [meta, setMeta]         = useState({ total: 0, pagina: 1, por_pagina: 20, paginas: 0 });
  const [filtros, setFiltros]   = useState({ pagina: 1, por_pagina: 20, ...filtrosIniciais });
  const [loading, setLoading]   = useState(false);
  const [erro, setErro]         = useState(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro(null);
    try {
      const res = await clienteService.listar(filtros);
      setDados(res.dados);
      setMeta(res.meta);
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  }, [filtros]);

  useEffect(() => { carregar(); }, [carregar]);

  const atualizar = (novosFiltros) =>
    setFiltros((f) => ({ ...f, ...novosFiltros, pagina: novosFiltros.pagina ?? 1 }));

  return { dados, meta, filtros, loading, erro, atualizar, recarregar: carregar };
}

export function useSegmentos() {
  const [segmentos, setSegmentos] = useState([]);
  useEffect(() => {
    clienteService.segmentos().then(setSegmentos).catch(() => {});
  }, []);
  return segmentos;
}
