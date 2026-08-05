// src/components/contas-receber/ContasReceberPainel.jsx
"use client";
import { useState, useEffect, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = v => Number(v||0).toLocaleString("pt-BR", { style:"currency", currency:"BRL" });
const fmtData  = d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR") : "—";

const STATUS_COR = {
  ABERTA:       { bg:"#EFF6FF", text:"#1E40AF" },
  RECEBIDA:     { bg:"#DCFCE7", text:"#15803D" },
  PARCIAL:      { bg:"#FEF3C7", text:"#92400E" },
  VENCIDA:      { bg:"#FEE2E2", text:"#B91C1C" },
  NEGOCIADA:    { bg:"#EDE9FE", text:"#5B21B6" },
  INADIMPLENTE: { bg:"#FEE2E2", text:"#B91C1C" },
  CANCELADA:    { bg:"#F3F4F6", text:"#9CA3AF" },
};

const FAIXA_COR = {
  A_VENCER: { bg:"#DCFCE7", text:"#15803D", label:"A vencer" },
  "1_A_30": { bg:"#FEF3C7", text:"#92400E", label:"1–30 dias" },
  "31_A_60":{ bg:"#FED7AA", text:"#9A3412", label:"31–60 dias" },
  "61_A_90":{ bg:"#FEE2E2", text:"#B91C1C", label:"61–90 dias" },
  ACIMA_90: { bg:"#FEE2E2", text:"#7F1D1D", label:"+90 dias" },
};

const FORMAS = ["BOLETO","PIX","TED","DOC","DEPOSITO","CARTAO","OUTROS"];

export default function ContasReceberPainel() {
  const [lista,  setLista]  = useState([]);
  const [meta,   setMeta]   = useState({ total:0, paginas:0, pagina:1 });
  const [aging,  setAging]  = useState([]);
  const [filtros,setFiltros]= useState({ pagina:1, por_pagina:20 });
  const [loading,setLoading]= useState(false);
  const [erro,   setErro]   = useState(null);
  const [sel,    setSel]    = useState(null);   // cobrança selecionada
  const [loadDet,setLoadDet]= useState(false);

  // Modal recebimento
  const [modalRec, setModalRec] = useState(null);
  const [formRec,  setFormRec]  = useState({ data_recebimento:"", valor:"", forma:"PIX", identificador:"", observacoes:"" });
  const [salvando, setSalvando] = useState(false);

  // Modal negociação
  const [modalNeg, setModalNeg] = useState(null);
  const [formNeg,  setFormNeg]  = useState({ valor_negociado:"", num_parcelas:1, motivo:"" });

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams();
      Object.entries(filtros).forEach(([k,v]) => v!=null && v!=="" && q.append(k,v));
      const [res, ag] = await Promise.all([api(`/contas-receber?${q}`), api("/contas-receber/aging")]);
      setLista(res.dados); setMeta(res.meta); setAging(ag);
    } catch(e){ setErro(e.message); }
    finally { setLoading(false); }
  }, [filtros]);

  useEffect(() => { carregar(); }, [carregar]);

  const verDetalhe = async (item) => {
    setLoadDet(true);
    try { setSel(await api(`/contas-receber/${item.id}`)); }
    catch(e){ setErro(e.message); }
    finally { setLoadDet(false); }
  };

  const handleReceber = async () => {
    setSalvando(true);
    try {
      await api(`/contas-receber/${modalRec.id}/recebimentos`, {
        method:"POST",
        body: JSON.stringify({ ...formRec, valor: parseFloat(formRec.valor) }),
      });
      setModalRec(null); carregar();
      if (sel?.id === modalRec.id) setSel(await api(`/contas-receber/${modalRec.id}`));
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleNegociar = async () => {
    setSalvando(true);
    try {
      await api(`/contas-receber/${modalNeg.id}/negociacoes`, {
        method:"POST",
        body: JSON.stringify({ ...formNeg, valor_negociado: parseFloat(formNeg.valor_negociado) }),
      });
      setModalNeg(null); carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const set = (k,v) => setFiltros(f => ({...f,[k]:v||undefined,pagina:1}));

  return (
    <div style={{ padding:"2rem", maxWidth:1100, margin:"0 auto" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1.25rem" }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0, color:"#111827" }}>Contas a Receber</h1>
          <p style={{ margin:"3px 0 0", fontSize:13, color:"#6B7280" }}>{meta.total} cobrança(s)</p>
        </div>
      </div>

      {/* Aging cards */}
      <div style={{ display:"flex", gap:10, marginBottom:16, flexWrap:"wrap" }}>
        {aging.map(a => (
          <div key={a.faixa} onClick={() => set("faixa_aging", a.faixa)}
            style={{ flex:"1 1 140px", background: FAIXA_COR[a.faixa]?.bg||"#F9FAFB", border:"0.5px solid #E5E7EB", borderRadius:10, padding:"12px 14px", cursor:"pointer" }}>
            <div style={{ fontSize:11, color: FAIXA_COR[a.faixa]?.text||"#374151", fontWeight:500, marginBottom:4 }}>
              {FAIXA_COR[a.faixa]?.label || a.faixa}
            </div>
            <div style={{ fontSize:18, fontWeight:600, color:"#111827" }}>{a.quantidade}</div>
            <div style={{ fontSize:12, color:"#6B7280", fontFamily:"monospace" }}>{fmtMoeda(a.valor_total)}</div>
          </div>
        ))}
        {filtros.faixa_aging && (
          <button onClick={() => set("faixa_aging","")} style={{ alignSelf:"center", padding:"6px 12px", background:"#fff", border:"1px solid #D1D5DB", borderRadius:8, fontSize:12, cursor:"pointer" }}>
            ✕ Limpar filtro
          </button>
        )}
      </div>

      {/* Filtros */}
      <div style={{ display:"flex", gap:10, flexWrap:"wrap", marginBottom:12 }}>
        <select onChange={e => set("status",e.target.value)} style={inputStyle}>
          <option value="">Todos os status</option>
          {["ABERTA","PARCIAL","VENCIDA","RECEBIDA","NEGOCIADA","INADIMPLENTE"].map(s =>
            <option key={s} value={s}>{s}</option>
          )}
        </select>
        <input type="month" onChange={e => set("competencia", e.target.value ? e.target.value+"-01":"")} style={inputStyle} />
        <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:13 }}>
          <input type="checkbox" onChange={e => setFiltros(f=>({...f,em_atraso:e.target.checked,pagina:1}))} />
          Em atraso
        </label>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={()=>setErro(null)} style={{background:"none",border:"none",cursor:"pointer"}}>✕</button></div>}

      <div style={{ display:"flex", gap:16, alignItems:"flex-start" }}>
        {/* Tabela */}
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ background:"#fff", border:"1px solid #E5E7EB", borderRadius:10, overflow:"hidden" }}>
            {loading ? (
              <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Carregando...</div>
            ) : lista.length === 0 ? (
              <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Nenhuma cobrança encontrada.</div>
            ) : (
              <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                <thead>
                  <tr style={{ background:"#F9FAFB", borderBottom:"1px solid #E5E7EB" }}>
                    {["Nº","Cliente","Competência","Vencimento","Valor","Saldo","Situação","Ações"].map(h =>
                      <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontWeight:500, color:"#374151", whiteSpace:"nowrap" }}>{h}</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {lista.map((c,i) => (
                    <tr key={c.id} onClick={()=>verDetalhe(c)}
                      style={{ borderBottom:"1px solid #F3F4F6", background: sel?.id===c.id?"#EFF6FF": i%2===0?"#fff":"#FAFAFA", cursor:"pointer" }}>
                      <td style={{ padding:"9px 12px", fontFamily:"monospace", fontSize:11 }}>{c.numero_cobranca}</td>
                      <td style={{ padding:"9px 12px" }}>{c.cliente_nome}<div style={{fontSize:11,color:"#9CA3AF"}}>{c.modalidade}</div></td>
                      <td style={{ padding:"9px 12px", color:"#6B7280" }}>{fmtData(c.competencia)?.slice(3)}</td>
                      <td style={{ padding:"9px 12px", color: c.dias_atraso>0?"#B91C1C":"#6B7280" }}>
                        {fmtData(c.data_vencimento)}{c.dias_atraso>0 && <span style={{fontSize:11,marginLeft:4}}>+{c.dias_atraso}d</span>}
                      </td>
                      <td style={{ padding:"9px 12px", fontFamily:"monospace", fontWeight:500 }}>{fmtMoeda(c.valor_original)}</td>
                      <td style={{ padding:"9px 12px", fontFamily:"monospace", color: Number(c.valor_saldo)>0?"#B91C1C":"#15803D" }}>{fmtMoeda(c.valor_saldo)}</td>
                      <td style={{ padding:"9px 12px" }}>
                        <span style={{ ...badge, background:STATUS_COR[c.status]?.bg, color:STATUS_COR[c.status]?.text }}>{c.status}</span>
                      </td>
                      <td style={{ padding:"9px 12px" }} onClick={e=>e.stopPropagation()}>
                        <div style={{ display:"flex", gap:4 }}>
                          {!["RECEBIDA","CANCELADA"].includes(c.status) && (
                            <button onClick={()=>{ setModalRec(c); setFormRec({data_recebimento:new Date().toISOString().split("T")[0], valor:c.valor_saldo, forma:"PIX", identificador:"", observacoes:""}) }} style={btnSmStyle}>Baixar</button>
                          )}
                          {["VENCIDA","INADIMPLENTE"].includes(c.status) && (
                            <button onClick={()=>{ setModalNeg(c); setFormNeg({valor_negociado:c.valor_saldo,num_parcelas:1,motivo:""}) }} style={{...btnSmStyle,color:"#5B21B6",borderColor:"#DDD6FE"}}>Negociar</button>
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
        </div>

        {/* Painel lateral */}
        {sel && (
          <div style={{ width:300, flexShrink:0, background:"#fff", border:"1px solid #E5E7EB", borderRadius:10, padding:"1rem" }}>
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:12 }}>
              <div>
                <p style={{ margin:0, fontSize:11, color:"#9CA3AF", fontFamily:"monospace" }}>{sel.numero_cobranca}</p>
                <span style={{ ...badge, background:STATUS_COR[sel.status]?.bg, color:STATUS_COR[sel.status]?.text, marginTop:4 }}>{sel.status}</span>
              </div>
              <button onClick={()=>setSel(null)} style={{ background:"none", border:"none", cursor:"pointer", color:"#9CA3AF" }}>✕</button>
            </div>
            {loadDet ? <p style={{color:"#9CA3AF",fontSize:13}}>Carregando...</p> : (
              <>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:12 }}>
                  {[["Original",fmtMoeda(sel.valor_original)],["Recebido",fmtMoeda(sel.valor_recebido)],["Saldo",fmtMoeda(sel.valor_saldo)],["Vencimento",fmtData(sel.data_vencimento)]].map(([k,v])=>(
                    <div key={k} style={{ background:"#F9FAFB", padding:"8px 10px", borderRadius:8 }}>
                      <p style={{ margin:0, fontSize:11, color:"#9CA3AF" }}>{k}</p>
                      <p style={{ margin:"2px 0 0", fontSize:13, fontWeight:500, color:"#111827" }}>{v}</p>
                    </div>
                  ))}
                </div>

                {sel.recebimentos?.length > 0 && (
                  <div style={{ marginBottom:12 }}>
                    <p style={{ fontSize:11, fontWeight:600, color:"#6B7280", textTransform:"uppercase", margin:"0 0 6px" }}>Recebimentos</p>
                    {sel.recebimentos.map(r => (
                      <div key={r.id} style={{ display:"flex", justifyContent:"space-between", fontSize:12, padding:"5px 0", borderBottom:"1px solid #F9FAFB" }}>
                        <span style={{ color:"#374151" }}>{fmtData(r.data_recebimento)} · {r.forma}</span>
                        <span style={{ fontFamily:"monospace", color:"#15803D" }}>{fmtMoeda(r.valor)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {sel.negociacoes?.length > 0 && (
                  <div style={{ marginBottom:12 }}>
                    <p style={{ fontSize:11, fontWeight:600, color:"#6B7280", textTransform:"uppercase", margin:"0 0 6px" }}>Negociações</p>
                    {sel.negociacoes.map(n => (
                      <div key={n.id} style={{ background:"#F5F3FF", padding:"8px 10px", borderRadius:8, fontSize:12 }}>
                        <div style={{ fontWeight:500, color:"#5B21B6" }}>{n.status}</div>
                        <div style={{ color:"#374151" }}>{n.num_parcelas}x · {fmtMoeda(n.valor_negociado)}</div>
                        <div style={{ color:"#9CA3AF", fontSize:11 }}>{n.motivo}</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Modal: Baixar pagamento */}
      {modalRec && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.45)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:50 }}>
          <div style={{ background:"#fff", borderRadius:12, padding:"1.5rem", width:400, maxWidth:"90vw" }}>
            <h2 style={{ fontSize:16, fontWeight:600, margin:"0 0 6px" }}>Registrar recebimento</h2>
            <p style={{ fontSize:13, color:"#6B7280", margin:"0 0 14px" }}>{modalRec.numero_cobranca}</p>
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              <div><label style={labelStyle}>Data do recebimento *</label><input type="date" value={formRec.data_recebimento} onChange={e=>setFormRec(f=>({...f,data_recebimento:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Valor recebido (R$) *</label><input type="number" step="0.01" value={formRec.valor} onChange={e=>setFormRec(f=>({...f,valor:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Forma de recebimento *</label>
                <select value={formRec.forma} onChange={e=>setFormRec(f=>({...f,forma:e.target.value}))} style={inputStyle}>
                  {FORMAS.map(fo=><option key={fo} value={fo}>{fo}</option>)}
                </select>
              </div>
              <div><label style={labelStyle}>Identificador (código da transação)</label><input value={formRec.identificador} onChange={e=>setFormRec(f=>({...f,identificador:e.target.value}))} placeholder="Código PIX, NSU, etc." style={inputStyle}/></div>
            </div>
            <div style={{ display:"flex", justifyContent:"flex-end", gap:8, marginTop:16 }}>
              <button onClick={()=>setModalRec(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleReceber} disabled={!formRec.data_recebimento||!formRec.valor||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Confirmar"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Negociação */}
      {modalNeg && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.45)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:50 }}>
          <div style={{ background:"#fff", borderRadius:12, padding:"1.5rem", width:400, maxWidth:"90vw" }}>
            <h2 style={{ fontSize:16, fontWeight:600, margin:"0 0 6px" }}>Registrar negociação</h2>
            <p style={{ fontSize:13, color:"#6B7280", margin:"0 0 14px" }}>{modalNeg.numero_cobranca} · {fmtMoeda(modalNeg.valor_saldo)} em aberto</p>
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              <div><label style={labelStyle}>Valor negociado (R$) *</label><input type="number" step="0.01" value={formNeg.valor_negociado} onChange={e=>setFormNeg(f=>({...f,valor_negociado:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Número de parcelas</label><input type="number" min="1" max="60" value={formNeg.num_parcelas} onChange={e=>setFormNeg(f=>({...f,num_parcelas:parseInt(e.target.value)}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Motivo da negociação *</label><textarea value={formNeg.motivo} onChange={e=>setFormNeg(f=>({...f,motivo:e.target.value}))} rows={2} placeholder="Descreva o motivo..." style={{...inputStyle,resize:"vertical"}}/></div>
            </div>
            <div style={{ display:"flex", justifyContent:"flex-end", gap:8, marginTop:16 }}>
              <button onClick={()=>setModalNeg(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleNegociar} disabled={!formNeg.valor_negociado||!formNeg.motivo||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Registrar"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const badge      = { padding:"2px 8px", borderRadius:20, fontSize:11, fontWeight:500, display:"inline-flex" };
const inputStyle = { padding:"7px 11px", border:"1px solid #D1D5DB", borderRadius:7, fontSize:13, background:"#fff", color:"#111827", width:"100%", boxSizing:"border-box", display:"block" };
const labelStyle = { display:"block", fontSize:12, fontWeight:500, color:"#374151", marginBottom:4 };
const btnPrimStyle={ padding:"9px 18px", background:"#1E40AF", color:"#fff", border:"none", borderRadius:8, fontSize:13, fontWeight:500, cursor:"pointer" };
const btnSecStyle = { padding:"7px 14px", background:"#fff", color:"#374151", border:"1px solid #D1D5DB", borderRadius:8, fontSize:13, cursor:"pointer" };
const btnSmStyle  = { padding:"4px 8px", background:"#fff", color:"#374151", border:"1px solid #D1D5DB", borderRadius:6, fontSize:11, cursor:"pointer" };
const alertStyle  = { padding:"10px 14px", borderRadius:8, fontSize:13, marginBottom:12, background:"#FEE2E2", color:"#B91C1C", display:"flex", justifyContent:"space-between" };
