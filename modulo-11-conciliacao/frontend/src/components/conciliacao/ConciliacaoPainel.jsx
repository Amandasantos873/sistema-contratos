// src/components/conciliacao/ConciliacaoPainel.jsx
"use client";
import { useState, useEffect, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts={}) =>
  fetch(`${BASE}${path}`, { headers:{"Content-Type":"application/json"}, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e=>{ throw new Error(e.detail||"Erro"); }));

const fmtM = v => Number(v||0).toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
const fmtD = d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR") : "—";

const ST_COR = {
  PENDENTE:    {bg:"#FEF3C7",text:"#92400E"},
  CONCILIADO:  {bg:"#DCFCE7",text:"#15803D"},
  IGNORADO:    {bg:"#F3F4F6",text:"#9CA3AF"},
  DIVERGENTE:  {bg:"#FEE2E2",text:"#B91C1C"},
};

export default function ConciliacaoPainel() {
  const [conta,     setConta]     = useState(null);
  const [extrato,   setExtrato]   = useState([]);
  const [meta,      setMeta]      = useState({total:0,paginas:1,pagina:1});
  const [filtros,   setFiltros]   = useState({pagina:1,por_pagina:30,status:"PENDENTE"});
  const [loading,   setLoading]   = useState(false);
  const [erro,      setErro]      = useState(null);

  // Modal novo lançamento
  const [modalNovo, setModalNovo] = useState(false);
  const [formNovo,  setFormNovo]  = useState({
    data_lancamento:"", tipo:"CREDITO", valor:"", descricao:"", documento:"", saldo_apos:""
  });
  const [salvando, setSalvando] = useState(false);

  // Sugestões
  const [sugestoes,   setSugestoes]   = useState({});
  const [loadSug,     setLoadSug]     = useState({});
  const [expandido,   setExpandido]   = useState(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams();
      Object.entries(filtros).forEach(([k,v]) => v!=null&&v!==""&&q.append(k,v));
      const [ct, ext] = await Promise.all([
        api("/conciliacao/conta"),
        api(`/conciliacao/extrato?${q}`),
      ]);
      setConta(ct[0]||null);
      setExtrato(ext.dados);
      setMeta(ext.meta);
    } catch(e){ setErro(e.message); }
    finally { setLoading(false); }
  }, [filtros]);

  useEffect(() => { carregar(); }, [carregar]);

  const verSugestoes = async (lancamento) => {
    if (expandido === lancamento.id) { setExpandido(null); return; }
    setExpandido(lancamento.id);
    if (sugestoes[lancamento.id]) return;
    setLoadSug(s=>({...s,[lancamento.id]:true}));
    try {
      const res = await api(`/conciliacao/extrato/${lancamento.id}/sugestoes`);
      setSugestoes(s=>({...s,[lancamento.id]:res}));
    } catch(e){ setErro(e.message); }
    finally { setLoadSug(s=>({...s,[lancamento.id]:false})); }
  };

  const handleConciliar = async (extrato_id, sug) => {
    try {
      await api(`/conciliacao/extrato/${extrato_id}/conciliar`, {
        method:"POST",
        body: JSON.stringify({
          origem_id:     sug.origem_id,
          origem:        sug.origem,
          origem_numero: sug.origem_numero,
        })
      });
      setSugestoes(s=>{ const n={...s}; delete n[extrato_id]; return n; });
      setExpandido(null);
      carregar();
    } catch(e){ setErro(e.message); }
  };

  const handleIgnorar = async (id) => {
    try {
      await api(`/conciliacao/extrato/${id}/ignorar`, { method:"POST", body:JSON.stringify({motivo:"Lançamento ignorado pelo usuário"}) });
      carregar();
    } catch(e){ setErro(e.message); }
  };

  const handleDivergente = async (id) => {
    try {
      await api(`/conciliacao/extrato/${id}/divergente`, { method:"POST" });
      carregar();
    } catch(e){ setErro(e.message); }
  };

  const handleNovo = async () => {
    setSalvando(true);
    try {
      await api("/conciliacao/extrato", {
        method:"POST",
        body: JSON.stringify({...formNovo, valor:parseFloat(formNovo.valor), saldo_apos:formNovo.saldo_apos?parseFloat(formNovo.saldo_apos):null})
      });
      setModalNovo(false);
      setFormNovo({data_lancamento:"",tipo:"CREDITO",valor:"",descricao:"",documento:"",saldo_apos:""});
      carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const set = (k,v) => setFiltros(f=>({...f,[k]:v||undefined,pagina:1}));

  return (
    <div style={{padding:"2rem",maxWidth:1100,margin:"0 auto"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"1.25rem"}}>
        <div>
          <h1 style={{fontSize:20,fontWeight:600,margin:0,color:"#111827"}}>Conciliação Bancária</h1>
          <p style={{margin:"3px 0 0",fontSize:13,color:"#6B7280"}}>Extrato × Lançamentos do sistema</p>
        </div>
        <button onClick={()=>setModalNovo(true)} style={btnPrimStyle}>+ Lançamento</button>
      </div>

      {/* Posição da conta */}
      {conta && (
        <div style={{background:"#fff",border:"1px solid #E5E7EB",borderRadius:10,padding:"14px 18px",marginBottom:16}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",gap:10}}>
            <div>
              <div style={{fontSize:13,fontWeight:500,color:"#111827"}}>{conta.banco} — Ag. {conta.agencia} · C/C {conta.conta}</div>
              <div style={{fontSize:12,color:"#6B7280",marginTop:2}}>Saldo atual: <strong style={{color:"#111827",fontFamily:"monospace"}}>{fmtM(conta.saldo_atual)}</strong></div>
            </div>
            <div style={{display:"flex",gap:10}}>
              {[
                ["Pendentes",   conta.pendentes,   "#92400E","#FEF3C7"],
                ["Conciliados", conta.conciliados,  "#15803D","#DCFCE7"],
                ["Divergentes", conta.divergentes,  "#B91C1C","#FEE2E2"],
              ].map(([l,v,tc,bg])=>(
                <div key={l} style={{background:bg,padding:"6px 12px",borderRadius:8,textAlign:"center"}}>
                  <div style={{fontSize:11,color:tc}}>{l}</div>
                  <div style={{fontSize:16,fontWeight:600,color:"#111827"}}>{v}</div>
                </div>
              ))}
            </div>
          </div>
          {(Number(conta.creditos_pendentes)>0 || Number(conta.debitos_pendentes)>0) && (
            <div style={{display:"flex",gap:16,marginTop:10,fontSize:12,color:"#6B7280"}}>
              <span>Créditos pendentes: <strong style={{color:"#15803D",fontFamily:"monospace"}}>{fmtM(conta.creditos_pendentes)}</strong></span>
              <span>Débitos pendentes: <strong style={{color:"#B91C1C",fontFamily:"monospace"}}>{fmtM(conta.debitos_pendentes)}</strong></span>
            </div>
          )}
        </div>
      )}

      {/* Filtros */}
      <div style={{display:"flex",gap:10,flexWrap:"wrap",marginBottom:12}}>
        {[["PENDENTE","Pendentes"],["CONCILIADO","Conciliados"],["DIVERGENTE","Divergentes"],["IGNORADO","Ignorados"],["","Todos"]].map(([v,l])=>(
          <button key={v} onClick={()=>set("status",v)}
            style={{...btnSmStyle, background:filtros.status===v?"#185FA5":"#fff", color:filtros.status===v?"#fff":"#374151", borderColor:filtros.status===v?"#185FA5":"#D1D5DB"}}>
            {l}
          </button>
        ))}
        <select onChange={e=>set("tipo",e.target.value)} style={inputStyle}>
          <option value="">Todos</option>
          <option value="CREDITO">Créditos</option>
          <option value="DEBITO">Débitos</option>
        </select>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={()=>setErro(null)} style={{background:"none",border:"none",cursor:"pointer"}}>✕</button></div>}

      {/* Lista do extrato */}
      <div style={{display:"flex",flexDirection:"column",gap:6}}>
        {loading ? (
          <div style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Carregando...</div>
        ) : extrato.length===0 ? (
          <div style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Nenhum lançamento encontrado.</div>
        ) : extrato.map(e=>(
          <div key={e.id} style={{background:"#fff",border:"1px solid #E5E7EB",borderRadius:10,overflow:"hidden"}}>
            {/* Linha principal */}
            <div style={{display:"flex",alignItems:"center",gap:12,padding:"12px 16px"}}>
              {/* Tipo */}
              <div style={{width:56,height:40,borderRadius:8,display:"flex",alignItems:"center",justifyContent:"center",background:e.tipo==="CREDITO"?"#DCFCE7":"#FEE2E2",flexShrink:0}}>
                <span style={{fontSize:16}}>{e.tipo==="CREDITO"?"↓":"↑"}</span>
              </div>
              {/* Info */}
              <div style={{flex:1,minWidth:0}}>
                <div style={{fontSize:13,fontWeight:500,color:"#111827",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{e.descricao}</div>
                <div style={{fontSize:11,color:"#9CA3AF",marginTop:2}}>
                  {fmtD(e.data_lancamento)}
                  {e.documento && <span style={{marginLeft:8}}>Doc: {e.documento}</span>}
                  {e.origem_numero && <span style={{marginLeft:8,color:"#15803D"}}>→ {e.origem_numero}</span>}
                </div>
              </div>
              {/* Valor */}
              <div style={{textAlign:"right",flexShrink:0}}>
                <div style={{fontSize:15,fontWeight:600,fontFamily:"monospace",color:e.tipo==="CREDITO"?"#15803D":"#B91C1C"}}>
                  {e.tipo==="CREDITO"?"+":"-"}{fmtM(e.valor)}
                </div>
              </div>
              {/* Status */}
              <span style={{...badge,background:ST_COR[e.status_conciliacao]?.bg,color:ST_COR[e.status_conciliacao]?.text,flexShrink:0}}>
                {e.status_conciliacao}
              </span>
              {/* Ações */}
              {e.status_conciliacao==="PENDENTE" && (
                <div style={{display:"flex",gap:4,flexShrink:0}}>
                  <button onClick={()=>verSugestoes(e)} style={{...btnSmStyle,color:"#185FA5",borderColor:"#BFDBFE",background:expandido===e.id?"#EFF6FF":"#fff"}}>
                    {loadSug[e.id]?"...":"🔍 Sugestões"}
                  </button>
                  <button onClick={()=>handleIgnorar(e.id)} style={{...btnSmStyle,color:"#9CA3AF"}}>Ignorar</button>
                  <button onClick={()=>handleDivergente(e.id)} style={{...btnSmStyle,color:"#B91C1C",borderColor:"#FECACA"}}>⚠</button>
                </div>
              )}
            </div>

            {/* Sugestões expandidas */}
            {expandido===e.id && (
              <div style={{borderTop:"1px solid #E5E7EB",background:"#F8FAFC",padding:"12px 16px"}}>
                <p style={{fontSize:12,fontWeight:500,color:"#374151",margin:"0 0 8px"}}>
                  Sugestões automáticas — valor ± R$ 0,10 · data ± 3 dias
                </p>
                {!sugestoes[e.id] || sugestoes[e.id].length===0 ? (
                  <div style={{fontSize:12,color:"#9CA3AF",padding:"8px 0"}}>
                    Nenhuma sugestão encontrada.
                    <button onClick={()=>handleIgnorar(e.id)} style={{marginLeft:10,...btnSmStyle,fontSize:11}}>Ignorar lançamento</button>
                  </div>
                ) : (
                  <div style={{display:"flex",flexDirection:"column",gap:6}}>
                    {sugestoes[e.id].map((s,i)=>(
                      <div key={i} style={{display:"flex",alignItems:"center",gap:12,background:"#fff",border:"1px solid #E5E7EB",borderRadius:8,padding:"10px 14px"}}>
                        <div style={{flex:1}}>
                          <div style={{fontSize:12,fontWeight:500,color:"#111827"}}>{s.descricao}</div>
                          <div style={{fontSize:11,color:"#9CA3AF",marginTop:2}}>
                            {s.origem} · {s.origem_numero} · {fmtD(s.data_ref)}
                            <span style={{marginLeft:8,background:"#EFF6FF",color:"#185FA5",padding:"1px 6px",borderRadius:10}}>
                              score: {s.score}
                            </span>
                          </div>
                        </div>
                        <div style={{fontFamily:"monospace",fontWeight:500,color:"#111827"}}>{fmtM(s.valor)}</div>
                        <button onClick={()=>handleConciliar(e.id,s)} style={{...btnSmStyle,background:"#185FA5",color:"#fff",borderColor:"#185FA5"}}>
                          ✓ Confirmar
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Paginação */}
      {meta.paginas>1 && (
        <div style={{display:"flex",justifyContent:"flex-end",gap:6,marginTop:10}}>
          <button disabled={meta.pagina===1} onClick={()=>setFiltros(f=>({...f,pagina:f.pagina-1}))} style={btnSecStyle}>←</button>
          <span style={{padding:"6px 12px",fontSize:13,color:"#6B7280"}}>{meta.pagina}/{meta.paginas}</span>
          <button disabled={meta.pagina===meta.paginas} onClick={()=>setFiltros(f=>({...f,pagina:f.pagina+1}))} style={btnSecStyle}>→</button>
        </div>
      )}

      {/* Modal novo lançamento */}
      {modalNovo && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.45)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:50}}>
          <div style={{background:"#fff",borderRadius:12,padding:"1.5rem",width:460,maxWidth:"90vw"}}>
            <h2 style={{fontSize:16,fontWeight:600,margin:"0 0 16px"}}>Novo lançamento do extrato</h2>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
              <div><label style={labelStyle}>Data *</label><input type="date" value={formNovo.data_lancamento} onChange={e=>setFormNovo(f=>({...f,data_lancamento:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Tipo *</label>
                <select value={formNovo.tipo} onChange={e=>setFormNovo(f=>({...f,tipo:e.target.value}))} style={inputStyle}>
                  <option value="CREDITO">Crédito (entrada)</option>
                  <option value="DEBITO">Débito (saída)</option>
                </select>
              </div>
            </div>
            <div style={{marginBottom:10}}><label style={labelStyle}>Descrição *</label><input value={formNovo.descricao} onChange={e=>setFormNovo(f=>({...f,descricao:e.target.value}))} placeholder="Descrição conforme extrato do banco" style={inputStyle}/></div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
              <div><label style={labelStyle}>Valor (R$) *</label><input type="number" step="0.01" value={formNovo.valor} onChange={e=>setFormNovo(f=>({...f,valor:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Saldo após</label><input type="number" step="0.01" value={formNovo.saldo_apos} onChange={e=>setFormNovo(f=>({...f,saldo_apos:e.target.value}))} placeholder="Saldo do extrato" style={inputStyle}/></div>
            </div>
            <div style={{display:"flex",justifyContent:"flex-end",gap:8}}>
              <button onClick={()=>setModalNovo(false)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleNovo} disabled={!formNovo.data_lancamento||!formNovo.valor||!formNovo.descricao||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Lançar"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const badge      = {padding:"2px 8px",borderRadius:20,fontSize:11,fontWeight:500,display:"inline-flex"};
const inputStyle = {padding:"7px 11px",border:"1px solid #D1D5DB",borderRadius:7,fontSize:13,background:"#fff",color:"#111827",width:"100%",boxSizing:"border-box",display:"block"};
const labelStyle = {display:"block",fontSize:12,fontWeight:500,color:"#374151",marginBottom:4};
const btnPrimStyle={padding:"9px 18px",background:"#185FA5",color:"#fff",border:"none",borderRadius:8,fontSize:13,fontWeight:500,cursor:"pointer"};
const btnSecStyle ={padding:"7px 14px",background:"#fff",color:"#374151",border:"1px solid #D1D5DB",borderRadius:8,fontSize:13,cursor:"pointer"};
const btnSmStyle  ={padding:"5px 10px",background:"#fff",border:"1px solid #D1D5DB",borderRadius:6,fontSize:12,cursor:"pointer"};
const alertStyle  ={padding:"10px 14px",borderRadius:8,fontSize:13,marginBottom:12,background:"#FEE2E2",color:"#B91C1C",display:"flex",justifyContent:"space-between"};
