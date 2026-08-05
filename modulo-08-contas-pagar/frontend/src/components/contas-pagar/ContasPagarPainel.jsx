// src/components/contas-pagar/ContasPagarPainel.jsx
"use client";
import { useState, useEffect, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = v => Number(v||0).toLocaleString("pt-BR", { style:"currency", currency:"BRL" });
const fmtData  = d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR") : "—";

const STATUS_COR = {
  LANCADA:              { bg:"#F3F4F6", text:"#374151" },
  AGUARDANDO_APROVACAO: { bg:"#FEF3C7", text:"#92400E" },
  APROVADA:             { bg:"#DBEAFE", text:"#1E40AF" },
  PAGA:                 { bg:"#DCFCE7", text:"#15803D" },
  CONCILIADA:           { bg:"#D1FAE5", text:"#065F46" },
  CANCELADA:            { bg:"#F3F4F6", text:"#9CA3AF" },
  REPROVADA:            { bg:"#FEE2E2", text:"#B91C1C" },
};

const TIPO_COR = {
  FOLHA:         "#3B82F6",
  BENEFICIO:     "#8B5CF6",
  FORNECEDOR:    "#F59E0B",
  IMPOSTO:       "#EF4444",
  ADMINISTRATIVA:"#6B7280",
  COMISSAO:      "#10B981",
  OUTROS:        "#9CA3AF",
};

const FORMAS_PAG = ["PIX","TED","BOLETO","CHEQUE","DEBITO_AUTOMATICO","OUTROS"];

export default function ContasPagarPainel() {
  const [lista,       setLista]       = useState([]);
  const [meta,        setMeta]        = useState({ total:0, paginas:0, pagina:1 });
  const [categorias,  setCategorias]  = useState([]);
  const [centros,     setCentros]     = useState([]);
  const [fornecedores,setFornecedores]= useState([]);
  const [filtros,     setFiltros]     = useState({ pagina:1, por_pagina:20 });
  const [loading,     setLoading]     = useState(false);
  const [erro,        setErro]        = useState(null);

  // Modais
  const [modalNova,  setModalNova]  = useState(false);
  const [modalPagar, setModalPagar] = useState(null);
  const [modalAprv,  setModalAprv]  = useState(null);
  const [salvando,   setSalvando]   = useState(false);

  const [formNova, setFormNova] = useState({
    categoria_id:"", centro_custo_id:"", fornecedor_id:"",
    descricao:"", competencia:"", data_vencimento:"",
    valor:"", numero_documento:"", observacoes:""
  });
  const [formPagar, setFormPagar] = useState({
    data_pagamento:"", valor_pago:"", forma_pagamento:"PIX",
    banco_pagamento:"", identificador_pag:""
  });
  const [formAprv, setFormAprv] = useState({ aprovador:1, decisao:"APROVADO", observacao:"" });

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams();
      Object.entries(filtros).forEach(([k,v]) => v!=null && v!=="" && q.append(k,v));
      const res = await api(`/contas-pagar?${q}`);
      setLista(res.dados); setMeta(res.meta);
    } catch(e){ setErro(e.message); }
    finally { setLoading(false); }
  }, [filtros]);

  useEffect(() => {
    carregar();
    Promise.all([
      api("/categorias-despesa"),
      api("/centros-custo"),
      api("/fornecedores"),
    ]).then(([cats, cts, fns]) => {
      setCategorias(cats); setCentros(cts); setFornecedores(fns);
    });
  }, [carregar]);

  const handleNova = async () => {
    setSalvando(true);
    try {
      await api("/contas-pagar", {
        method:"POST",
        body: JSON.stringify({ ...formNova, valor: parseFloat(formNova.valor), categoria_id: parseInt(formNova.categoria_id), centro_custo_id: parseInt(formNova.centro_custo_id), fornecedor_id: formNova.fornecedor_id || null })
      });
      setModalNova(false); carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handlePagar = async () => {
    setSalvando(true);
    try {
      await api(`/contas-pagar/${modalPagar.id}/pagar`, {
        method:"PATCH",
        body: JSON.stringify({ ...formPagar, valor_pago: parseFloat(formPagar.valor_pago) })
      });
      setModalPagar(null); carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleAprovar = async () => {
    setSalvando(true);
    try {
      await api(`/contas-pagar/${modalAprv.id}/aprovar`, {
        method:"PATCH",
        body: JSON.stringify(formAprv)
      });
      setModalAprv(null); carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleConciliar = async (id) => {
    try { await api(`/contas-pagar/${id}/conciliar`, { method:"PATCH" }); carregar(); }
    catch(e){ setErro(e.message); }
  };

  const set = (k,v) => setFiltros(f => ({...f,[k]:v||undefined,pagina:1}));

  // Totais por status
  const totais = lista.reduce((acc, d) => {
    acc[d.status] = (acc[d.status]||0) + Number(d.valor);
    return acc;
  }, {});

  return (
    <div style={{ padding:"2rem", maxWidth:1100, margin:"0 auto" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1.25rem" }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0, color:"#111827" }}>Contas a Pagar</h1>
          <p style={{ margin:"3px 0 0", fontSize:13, color:"#6B7280" }}>{meta.total} despesa(s)</p>
        </div>
        <button onClick={()=>setModalNova(true)} style={btnPrimStyle}>+ Nova despesa</button>
      </div>

      {/* Cards de resumo */}
      <div style={{ display:"flex", gap:10, marginBottom:16, flexWrap:"wrap" }}>
        {[
          ["Aguard. aprovação","AGUARDANDO_APROVACAO","#92400E","#FEF3C7"],
          ["Aprovadas","APROVADA","#1E40AF","#DBEAFE"],
          ["Pagas","PAGA","#15803D","#DCFCE7"],
          ["Em atraso","ATRASO","#B91C1C","#FEE2E2"],
        ].map(([label, key, color, bg]) => (
          <div key={key} style={{ flex:"1 1 160px", background:bg, border:"0.5px solid #E5E7EB", borderRadius:10, padding:"12px 14px" }}>
            <div style={{ fontSize:11, color, fontWeight:500, marginBottom:4 }}>{label}</div>
            <div style={{ fontSize:18, fontWeight:600, color:"#111827" }}>
              {key==="ATRASO" ? lista.filter(d=>d.dias_atraso>0).length : lista.filter(d=>d.status===key).length}
            </div>
            <div style={{ fontSize:12, color:"#6B7280", fontFamily:"monospace" }}>
              {fmtMoeda(key==="ATRASO" ? lista.filter(d=>d.dias_atraso>0).reduce((s,d)=>s+Number(d.valor),0) : totais[key]||0)}
            </div>
          </div>
        ))}
      </div>

      {/* Filtros */}
      <div style={{ display:"flex", gap:10, flexWrap:"wrap", marginBottom:12 }}>
        <select onChange={e=>set("status",e.target.value)} style={inputStyle}>
          <option value="">Todos os status</option>
          {["LANCADA","AGUARDANDO_APROVACAO","APROVADA","PAGA","CONCILIADA","REPROVADA"].map(s=><option key={s} value={s}>{s.replace("_"," ")}</option>)}
        </select>
        <select onChange={e=>set("tipo",e.target.value)} style={inputStyle}>
          <option value="">Todos os tipos</option>
          {["FOLHA","BENEFICIO","FORNECEDOR","IMPOSTO","ADMINISTRATIVA","COMISSAO"].map(t=><option key={t} value={t}>{t}</option>)}
        </select>
        <select onChange={e=>set("centro_custo_id",e.target.value)} style={inputStyle}>
          <option value="">Todos os centros</option>
          {centros.map(c=><option key={c.id} value={c.id}>{c.nome}</option>)}
        </select>
        <input type="month" onChange={e=>set("competencia",e.target.value?e.target.value+"-01":"")} style={inputStyle}/>
        <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:13 }}>
          <input type="checkbox" onChange={e=>setFiltros(f=>({...f,em_atraso:e.target.checked,pagina:1}))}/>
          Em atraso
        </label>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={()=>setErro(null)} style={{background:"none",border:"none",cursor:"pointer"}}>✕</button></div>}

      <div style={{ background:"#fff", border:"1px solid #E5E7EB", borderRadius:10, overflow:"hidden" }}>
        {loading ? (
          <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Carregando...</div>
        ) : lista.length===0 ? (
          <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Nenhuma despesa encontrada.</div>
        ) : (
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
            <thead>
              <tr style={{ background:"#F9FAFB", borderBottom:"1px solid #E5E7EB" }}>
                {["Nº","Descrição","Categoria","Centro de Custo","Competência","Vencimento","Valor","Status","Ações"].map(h=>
                  <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontWeight:500, color:"#374151", whiteSpace:"nowrap" }}>{h}</th>
                )}
              </tr>
            </thead>
            <tbody>
              {lista.map((d,i)=>(
                <tr key={d.id} style={{ borderBottom:"1px solid #F3F4F6", background:i%2===0?"#fff":"#FAFAFA" }}>
                  <td style={{ padding:"9px 12px", fontFamily:"monospace", fontSize:11 }}>{d.numero_despesa}</td>
                  <td style={{ padding:"9px 12px", maxWidth:180 }}>
                    <div style={{ fontWeight:500, color:"#111827", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{d.descricao}</div>
                    {d.fornecedor_nome && <div style={{ fontSize:11, color:"#9CA3AF" }}>{d.fornecedor_nome}</div>}
                  </td>
                  <td style={{ padding:"9px 12px" }}>
                    <span style={{ background: TIPO_COR[d.categoria_tipo]+"22", color: TIPO_COR[d.categoria_tipo], padding:"2px 8px", borderRadius:20, fontSize:11, fontWeight:500 }}>{d.categoria_tipo}</span>
                    <div style={{ fontSize:11, color:"#9CA3AF", marginTop:2 }}>{d.categoria_nome}</div>
                  </td>
                  <td style={{ padding:"9px 12px", fontSize:12, color:"#6B7280" }}>{d.centro_custo_nome}</td>
                  <td style={{ padding:"9px 12px", color:"#6B7280" }}>{fmtData(d.competencia)?.slice(3)}</td>
                  <td style={{ padding:"9px 12px", color:d.dias_atraso>0?"#B91C1C":"#6B7280" }}>
                    {fmtData(d.data_vencimento)}{d.dias_atraso>0&&<span style={{fontSize:11,marginLeft:4}}>+{d.dias_atraso}d</span>}
                  </td>
                  <td style={{ padding:"9px 12px", fontFamily:"monospace", fontWeight:500 }}>{fmtMoeda(d.valor)}</td>
                  <td style={{ padding:"9px 12px" }}>
                    <span style={{ padding:"2px 8px", borderRadius:20, fontSize:11, fontWeight:500, background:STATUS_COR[d.status]?.bg, color:STATUS_COR[d.status]?.text }}>
                      {d.status.replace("_"," ")}
                    </span>
                    {d.conciliado && <span style={{ marginLeft:4, fontSize:10, color:"#065F46" }}>✓</span>}
                  </td>
                  <td style={{ padding:"9px 12px" }}>
                    <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
                      {d.status==="AGUARDANDO_APROVACAO" && (
                        <button onClick={()=>{ setModalAprv(d); setFormAprv({aprovador:1,decisao:"APROVADO",observacao:""}); }} style={{...btnSmStyle,color:"#1E40AF",borderColor:"#BFDBFE"}}>Aprovar</button>
                      )}
                      {d.status==="APROVADA" && (
                        <button onClick={()=>{ setModalPagar(d); setFormPagar({data_pagamento:new Date().toISOString().split("T")[0],valor_pago:d.valor,forma_pagamento:"PIX",banco_pagamento:"",identificador_pag:""}); }} style={{...btnSmStyle,color:"#15803D",borderColor:"#BBF7D0"}}>Pagar</button>
                      )}
                      {d.status==="PAGA" && !d.conciliado && (
                        <button onClick={()=>handleConciliar(d.id)} style={{...btnSmStyle,color:"#065F46",borderColor:"#D1FAE5"}}>Conciliar</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {meta.paginas>1 && (
        <div style={{ display:"flex", justifyContent:"flex-end", gap:6, marginTop:10 }}>
          <button disabled={meta.pagina===1} onClick={()=>setFiltros(f=>({...f,pagina:f.pagina-1}))} style={btnSecStyle}>←</button>
          <span style={{ padding:"6px 12px", fontSize:13, color:"#6B7280" }}>{meta.pagina}/{meta.paginas}</span>
          <button disabled={meta.pagina===meta.paginas} onClick={()=>setFiltros(f=>({...f,pagina:f.pagina+1}))} style={btnSecStyle}>→</button>
        </div>
      )}

      {/* Modal nova despesa */}
      {modalNova && (
        <div style={ovStyle}>
          <div style={modalStyle}>
            <h2 style={{ fontSize:16, fontWeight:600, margin:"0 0 16px" }}>Nova despesa</h2>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:10 }}>
              <div><label style={labelStyle}>Categoria *</label>
                <select value={formNova.categoria_id} onChange={e=>setFormNova(f=>({...f,categoria_id:e.target.value}))} style={inputStyle}>
                  <option value="">Selecione...</option>
                  {categorias.map(c=><option key={c.id} value={c.id}>{c.tipo} — {c.nome}</option>)}
                </select>
              </div>
              <div><label style={labelStyle}>Centro de custo *</label>
                <select value={formNova.centro_custo_id} onChange={e=>setFormNova(f=>({...f,centro_custo_id:e.target.value}))} style={inputStyle}>
                  <option value="">Selecione...</option>
                  {centros.map(c=><option key={c.id} value={c.id}>{c.nome}</option>)}
                </select>
              </div>
            </div>
            <div style={{ marginBottom:10 }}><label style={labelStyle}>Descrição *</label><input value={formNova.descricao} onChange={e=>setFormNova(f=>({...f,descricao:e.target.value}))} placeholder="Descrição da despesa" style={inputStyle}/></div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10, marginBottom:10 }}>
              <div><label style={labelStyle}>Competência *</label><input type="month" value={formNova.competencia} onChange={e=>setFormNova(f=>({...f,competencia:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Vencimento *</label><input type="date" value={formNova.data_vencimento} onChange={e=>setFormNova(f=>({...f,data_vencimento:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Valor (R$) *</label><input type="number" step="0.01" value={formNova.valor} onChange={e=>setFormNova(f=>({...f,valor:e.target.value}))} style={inputStyle}/></div>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:10 }}>
              <div><label style={labelStyle}>Fornecedor</label>
                <select value={formNova.fornecedor_id} onChange={e=>setFormNova(f=>({...f,fornecedor_id:e.target.value}))} style={inputStyle}>
                  <option value="">Nenhum</option>
                  {fornecedores.map(f=><option key={f.id} value={f.id}>{f.razao_social}</option>)}
                </select>
              </div>
              <div><label style={labelStyle}>Nº documento</label><input value={formNova.numero_documento} onChange={e=>setFormNova(f=>({...f,numero_documento:e.target.value}))} placeholder="NF, recibo..." style={inputStyle}/></div>
            </div>
            <div style={{ display:"flex", justifyContent:"flex-end", gap:8, marginTop:14, paddingTop:14, borderTop:"1px solid #F3F4F6" }}>
              <button onClick={()=>setModalNova(false)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleNova} disabled={!formNova.categoria_id||!formNova.centro_custo_id||!formNova.descricao||!formNova.valor||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Lançar despesa"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal aprovar */}
      {modalAprv && (
        <div style={ovStyle}>
          <div style={modalStyle}>
            <h2 style={{ fontSize:16, fontWeight:600, margin:"0 0 6px" }}>Aprovação de despesa</h2>
            <p style={{ fontSize:13, color:"#6B7280", margin:"0 0 14px" }}>{modalAprv.numero_despesa} · {fmtMoeda(modalAprv.valor)}</p>
            <div style={{ marginBottom:10 }}><label style={labelStyle}>Número do aprovador *</label>
              <select value={formAprv.aprovador} onChange={e=>setFormAprv(f=>({...f,aprovador:parseInt(e.target.value)}))} style={inputStyle}>
                <option value={1}>1º aprovador</option>
                <option value={2}>2º aprovador</option>
              </select>
            </div>
            <div style={{ marginBottom:10 }}><label style={labelStyle}>Decisão *</label>
              <select value={formAprv.decisao} onChange={e=>setFormAprv(f=>({...f,decisao:e.target.value}))} style={inputStyle}>
                <option value="APROVADO">Aprovar</option>
                <option value="REPROVADO">Reprovar</option>
              </select>
            </div>
            <div style={{ marginBottom:14 }}><label style={labelStyle}>Observação</label><textarea value={formAprv.observacao} onChange={e=>setFormAprv(f=>({...f,observacao:e.target.value}))} rows={2} style={{...inputStyle,resize:"vertical"}}/></div>
            <div style={{ display:"flex", justifyContent:"flex-end", gap:8 }}>
              <button onClick={()=>setModalAprv(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleAprovar} disabled={salvando} style={formAprv.decisao==="REPROVADO"?{...btnPrimStyle,background:"#B91C1C"}:btnPrimStyle}>{salvando?"Salvando...":formAprv.decisao==="APROVADO"?"Aprovar":"Reprovar"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal pagar */}
      {modalPagar && (
        <div style={ovStyle}>
          <div style={modalStyle}>
            <h2 style={{ fontSize:16, fontWeight:600, margin:"0 0 6px" }}>Registrar pagamento</h2>
            <p style={{ fontSize:13, color:"#6B7280", margin:"0 0 14px" }}>{modalPagar.numero_despesa} · {fmtMoeda(modalPagar.valor)}</p>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:10 }}>
              <div><label style={labelStyle}>Data do pagamento *</label><input type="date" value={formPagar.data_pagamento} onChange={e=>setFormPagar(f=>({...f,data_pagamento:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Valor pago (R$) *</label><input type="number" step="0.01" value={formPagar.valor_pago} onChange={e=>setFormPagar(f=>({...f,valor_pago:e.target.value}))} style={inputStyle}/></div>
            </div>
            <div style={{ marginBottom:10 }}><label style={labelStyle}>Forma de pagamento *</label>
              <select value={formPagar.forma_pagamento} onChange={e=>setFormPagar(f=>({...f,forma_pagamento:e.target.value}))} style={inputStyle}>
                {FORMAS_PAG.map(fp=><option key={fp} value={fp}>{fp}</option>)}
              </select>
            </div>
            <div style={{ marginBottom:14 }}><label style={labelStyle}>Identificador da transação</label><input value={formPagar.identificador_pag} onChange={e=>setFormPagar(f=>({...f,identificador_pag:e.target.value}))} placeholder="Código da transação no banco" style={inputStyle}/></div>
            <div style={{ display:"flex", justifyContent:"flex-end", gap:8 }}>
              <button onClick={()=>setModalPagar(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handlePagar} disabled={!formPagar.data_pagamento||!formPagar.valor_pago||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Confirmar pagamento"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inputStyle  = { padding:"7px 11px", border:"1px solid #D1D5DB", borderRadius:7, fontSize:13, background:"#fff", color:"#111827", width:"100%", boxSizing:"border-box", display:"block" };
const labelStyle  = { display:"block", fontSize:12, fontWeight:500, color:"#374151", marginBottom:4 };
const btnPrimStyle= { padding:"9px 18px", background:"#1E40AF", color:"#fff", border:"none", borderRadius:8, fontSize:13, fontWeight:500, cursor:"pointer" };
const btnSecStyle = { padding:"7px 14px", background:"#fff", color:"#374151", border:"1px solid #D1D5DB", borderRadius:8, fontSize:13, cursor:"pointer" };
const btnSmStyle  = { padding:"4px 8px", background:"#fff", border:"1px solid #D1D5DB", borderRadius:6, fontSize:11, cursor:"pointer" };
const alertStyle  = { padding:"10px 14px", borderRadius:8, fontSize:13, marginBottom:12, background:"#FEE2E2", color:"#B91C1C", display:"flex", justifyContent:"space-between" };
const ovStyle     = { position:"fixed", inset:0, background:"rgba(0,0,0,0.45)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:50 };
const modalStyle  = { background:"#fff", borderRadius:12, padding:"1.5rem", width:480, maxWidth:"90vw", maxHeight:"90vh", overflowY:"auto" };
