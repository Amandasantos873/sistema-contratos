// src/components/comissoes/ComissoesPainel.jsx
"use client";
import { useState, useEffect, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts={}) =>
  fetch(`${BASE}${path}`, { headers:{"Content-Type":"application/json"}, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e=>{ throw new Error(e.detail||"Erro"); }));

const fmtM = v => Number(v||0).toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
const fmtD = d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR") : "—";

const ST_COR = {
  REGISTRADA:           {bg:"#F3F4F6",text:"#374151"},
  AGUARDANDO_APROVACAO: {bg:"#FEF3C7",text:"#92400E"},
  APROVADA:             {bg:"#DBEAFE",text:"#1E40AF"},
  PAGA:                 {bg:"#DCFCE7",text:"#15803D"},
  CANCELADA:            {bg:"#F3F4F6",text:"#9CA3AF"},
  REPROVADA:            {bg:"#FEE2E2",text:"#B91C1C"},
};

const FORMAS = ["PIX","TED","DOC","BOLETO","CHEQUE","OUTROS"];

export default function ComissoesPainel() {
  const [lista,    setLista]    = useState([]);
  const [parceiros,setParceiros]= useState([]);
  const [resumo,   setResumo]   = useState(null);
  const [meta,     setMeta]     = useState({total:0,paginas:1,pagina:1});
  const [filtros,  setFiltros]  = useState({pagina:1,por_pagina:20});
  const [loading,  setLoading]  = useState(false);
  const [erro,     setErro]     = useState(null);
  const [aba,      setAba]      = useState("comissoes"); // comissoes | parceiros

  // Modais
  const [modalNova,     setModalNova]     = useState(false);
  const [modalParceiro, setModalParceiro] = useState(false);
  const [modalAprovar,  setModalAprovar]  = useState(null);
  const [modalPagar,    setModalPagar]    = useState(null);
  const [salvando,      setSalvando]      = useState(false);

  const [formNova, setFormNova] = useState({
    parceiro_id:"", contrato_id:"", tipo_calculo:"FIXO",
    percentual:"", valor_base:"", valor_comissao:"", motivo:""
  });
  const [formParceiro, setFormParceiro] = useState({
    nome:"", tipo_pessoa:"PF", cpf_cnpj:"", email:"",
    telefone:"", pix_chave:"", valor_fixo_padrao:""
  });
  const [formAprovar, setFormAprovar] = useState({decisao:"APROVADA", motivo_reprovacao:""});
  const [formPagar,   setFormPagar]   = useState({data_pagamento:"", forma_pagamento:"PIX", identificador_pag:""});

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams();
      Object.entries(filtros).forEach(([k,v])=>v!=null&&v!==""&&q.append(k,v));
      const [res, res2] = await Promise.all([
        api(`/comissoes?${q}`),
        api("/comissoes/resumo"),
      ]);
      setLista(res.dados); setMeta(res.meta); setResumo(res2);
    } catch(e){ setErro(e.message); }
    finally { setLoading(false); }
  }, [filtros]);

  useEffect(() => {
    carregar();
    api("/parceiros").then(setParceiros).catch(()=>{});
  }, [carregar]);

  const handleNova = async () => {
    setSalvando(true);
    try {
      await api("/comissoes", {
        method:"POST",
        body: JSON.stringify({
          ...formNova,
          valor_comissao: parseFloat(formNova.valor_comissao),
          percentual: formNova.percentual ? parseFloat(formNova.percentual) : null,
          valor_base: formNova.valor_base ? parseFloat(formNova.valor_base) : null,
        })
      });
      setModalNova(false); carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleParceiro = async () => {
    setSalvando(true);
    try {
      const novo = await api("/parceiros", {
        method:"POST",
        body: JSON.stringify({...formParceiro, valor_fixo_padrao: formParceiro.valor_fixo_padrao?parseFloat(formParceiro.valor_fixo_padrao):null})
      });
      setParceiros(p=>[...p, novo]);
      setModalParceiro(false);
      setFormParceiro({nome:"",tipo_pessoa:"PF",cpf_cnpj:"",email:"",telefone:"",pix_chave:"",valor_fixo_padrao:""});
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handleAprovar = async () => {
    setSalvando(true);
    try {
      await api(`/comissoes/${modalAprovar.id}/aprovar`, {method:"PATCH", body:JSON.stringify(formAprovar)});
      setModalAprovar(null); carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const handlePagar = async () => {
    setSalvando(true);
    try {
      await api(`/comissoes/${modalPagar.id}/pagar`, {method:"PATCH", body:JSON.stringify(formPagar)});
      setModalPagar(null); carregar();
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  return (
    <div style={{padding:"2rem",maxWidth:1100,margin:"0 auto"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"1.25rem"}}>
        <div>
          <h1 style={{fontSize:20,fontWeight:600,margin:0,color:"#111827"}}>Comissões</h1>
          <p style={{margin:"3px 0 0",fontSize:13,color:"#6B7280"}}>Indicações de parceiros</p>
        </div>
        <div style={{display:"flex",gap:8}}>
          <button onClick={()=>setModalParceiro(true)} style={btnSecStyle}>+ Parceiro</button>
          <button onClick={()=>setModalNova(true)} style={btnPrimStyle}>+ Comissão</button>
        </div>
      </div>

      {/* Cards de resumo */}
      {resumo && (
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
          {[
            ["Aguard. aprovação", resumo.aguardando, "#92400E","#FEF3C7"],
            ["Aprovadas",         resumo.aprovadas,  "#1E40AF","#DBEAFE"],
            ["Valor a pagar",     null,               "#1E40AF","#DBEAFE"],
            ["Total pago",        null,               "#15803D","#DCFCE7"],
          ].map(([label,v,tc,bg],i)=>(
            <div key={label} style={{background:bg,borderRadius:10,padding:"12px 14px"}}>
              <div style={{fontSize:11,color:tc,fontWeight:500,marginBottom:4}}>{label}</div>
              <div style={{fontSize:18,fontWeight:600,color:"#111827",fontFamily:"monospace"}}>
                {i<2 ? v : i===2 ? fmtM(resumo.valor_aprovado) : fmtM(resumo.valor_pago)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Abas */}
      <div style={{display:"flex",borderBottom:"1px solid #E5E7EB",marginBottom:16}}>
        {[["comissoes","Comissões"],["parceiros","Parceiros"]].map(([id,label])=>(
          <div key={id} onClick={()=>setAba(id)} style={{padding:"9px 18px",fontSize:13,cursor:"pointer",borderBottom:aba===id?"2px solid #185FA5":"2px solid transparent",color:aba===id?"#185FA5":"#6B7280",fontWeight:aba===id?500:400,marginBottom:"-1px"}}>{label}</div>
        ))}
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={()=>setErro(null)} style={{background:"none",border:"none",cursor:"pointer"}}>✕</button></div>}

      {/* COMISSÕES */}
      {aba==="comissoes" && (
        <>
          <div style={{display:"flex",gap:8,marginBottom:12,flexWrap:"wrap"}}>
            {[["","Todas"],["AGUARDANDO_APROVACAO","Aguardando"],["APROVADA","Aprovadas"],["PAGA","Pagas"],["REPROVADA","Reprovadas"]].map(([v,l])=>(
              <button key={v} onClick={()=>setFiltros(f=>({...f,status:v||undefined,pagina:1}))}
                style={{...btnSmStyle,background:filtros.status===v||(!filtros.status&&v==="")?"#185FA5":"#fff",color:filtros.status===v||(!filtros.status&&v==="")?"#fff":"#374151",borderColor:filtros.status===v||(!filtros.status&&v==="")?"#185FA5":"#D1D5DB"}}>
                {l}
              </button>
            ))}
          </div>

          <div style={{background:"#fff",border:"1px solid #E5E7EB",borderRadius:10,overflow:"hidden"}}>
            {loading ? <div style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Carregando...</div> :
            lista.length===0 ? <div style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Nenhuma comissão encontrada.</div> : (
              <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
                <thead>
                  <tr style={{background:"#F9FAFB",borderBottom:"1px solid #E5E7EB"}}>
                    {["Nº","Parceiro","Contrato/Cliente","Valor","Data","Status","Ações"].map(h=>(
                      <th key={h} style={{padding:"9px 12px",textAlign:"left",fontWeight:500,color:"#374151",whiteSpace:"nowrap",fontSize:11}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {lista.map((c,i)=>(
                    <tr key={c.id} style={{borderBottom:"1px solid #F3F4F6",background:i%2===0?"#fff":"#FAFAFA"}}>
                      <td style={{padding:"9px 12px",fontFamily:"monospace",fontSize:11}}>{c.numero_comissao}</td>
                      <td style={{padding:"9px 12px"}}>
                        <div style={{fontWeight:500,color:"#111827"}}>{c.parceiro_nome}</div>
                        {c.pix_chave && <div style={{fontSize:11,color:"#9CA3AF"}}>PIX: {c.pix_chave}</div>}
                      </td>
                      <td style={{padding:"9px 12px"}}>
                        <div style={{fontSize:12,color:"#374151"}}>{c.contrato_numero}</div>
                        <div style={{fontSize:11,color:"#9CA3AF"}}>{c.cliente_nome}</div>
                      </td>
                      <td style={{padding:"9px 12px",fontFamily:"monospace",fontWeight:500}}>{fmtM(c.valor_comissao)}</td>
                      <td style={{padding:"9px 12px",fontSize:12,color:"#6B7280"}}>{fmtD(c.data_registro)}</td>
                      <td style={{padding:"9px 12px"}}>
                        <span style={{...badge,background:ST_COR[c.status]?.bg,color:ST_COR[c.status]?.text}}>{c.status.replace("_"," ")}</span>
                      </td>
                      <td style={{padding:"9px 12px"}}>
                        <div style={{display:"flex",gap:4}}>
                          {c.status==="AGUARDANDO_APROVACAO" && (
                            <button onClick={()=>{setModalAprovar(c);setFormAprovar({decisao:"APROVADA",motivo_reprovacao:""});}} style={{...btnSmStyle,color:"#1E40AF",borderColor:"#BFDBFE"}}>Aprovar</button>
                          )}
                          {c.status==="APROVADA" && (
                            <button onClick={()=>{setModalPagar(c);setFormPagar({data_pagamento:new Date().toISOString().split("T")[0],forma_pagamento:"PIX",identificador_pag:""});}} style={{...btnSmStyle,color:"#15803D",borderColor:"#BBF7D0"}}>Pagar</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {/* PARCEIROS */}
      {aba==="parceiros" && (
        <div style={{background:"#fff",border:"1px solid #E5E7EB",borderRadius:10,overflow:"hidden"}}>
          {parceiros.length===0 ? <div style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Nenhum parceiro cadastrado.</div> : (
            <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
              <thead>
                <tr style={{background:"#F9FAFB",borderBottom:"1px solid #E5E7EB"}}>
                  {["Nome","Tipo","Documento","Contato","PIX/Banco","Valor padrão"].map(h=>(
                    <th key={h} style={{padding:"9px 12px",textAlign:"left",fontWeight:500,color:"#374151",fontSize:11}}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parceiros.map((p,i)=>(
                  <tr key={p.id} style={{borderBottom:"1px solid #F3F4F6",background:i%2===0?"#fff":"#FAFAFA"}}>
                    <td style={{padding:"9px 12px",fontWeight:500,color:"#111827"}}>{p.nome}</td>
                    <td style={{padding:"9px 12px"}}><span style={{...badge,background:"#EFF6FF",color:"#185FA5"}}>{p.tipo_pessoa}</span></td>
                    <td style={{padding:"9px 12px",fontFamily:"monospace",fontSize:12,color:"#6B7280"}}>{p.cpf_cnpj||"—"}</td>
                    <td style={{padding:"9px 12px",fontSize:12,color:"#6B7280"}}>{p.email||p.telefone||"—"}</td>
                    <td style={{padding:"9px 12px",fontSize:12,color:"#6B7280"}}>{p.pix_chave||"—"}</td>
                    <td style={{padding:"9px 12px",fontFamily:"monospace"}}>{p.valor_fixo_padrao?fmtM(p.valor_fixo_padrao):"—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal nova comissão */}
      {modalNova && (
        <div style={ovStyle}>
          <div style={modalStyle}>
            <h2 style={{fontSize:16,fontWeight:600,margin:"0 0 16px"}}>Registrar comissão</h2>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
              <div><label style={labelStyle}>Parceiro *</label>
                <select value={formNova.parceiro_id} onChange={e=>setFormNova(f=>({...f,parceiro_id:e.target.value}))} style={inputStyle}>
                  <option value="">Selecione...</option>
                  {parceiros.map(p=><option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </div>
              <div><label style={labelStyle}>ID do Contrato *</label>
                <input value={formNova.contrato_id} onChange={e=>setFormNova(f=>({...f,contrato_id:e.target.value}))} placeholder="UUID do contrato" style={inputStyle}/>
              </div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
              <div><label style={labelStyle}>Tipo de cálculo</label>
                <select value={formNova.tipo_calculo} onChange={e=>setFormNova(f=>({...f,tipo_calculo:e.target.value}))} style={inputStyle}>
                  <option value="FIXO">Valor fixo</option>
                  <option value="PERCENTUAL">Percentual</option>
                </select>
              </div>
              <div><label style={labelStyle}>Valor da comissão (R$) *</label>
                <input type="number" step="0.01" value={formNova.valor_comissao} onChange={e=>setFormNova(f=>({...f,valor_comissao:e.target.value}))} style={inputStyle}/>
              </div>
            </div>
            <div style={{marginBottom:14}}><label style={labelStyle}>Motivo / Descrição da indicação *</label>
              <textarea value={formNova.motivo} onChange={e=>setFormNova(f=>({...f,motivo:e.target.value}))} rows={2} placeholder="Ex: Cliente indicado pelo parceiro em reunião de networking" style={{...inputStyle,resize:"vertical"}}/>
            </div>
            <div style={{display:"flex",justifyContent:"flex-end",gap:8}}>
              <button onClick={()=>setModalNova(false)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleNova} disabled={!formNova.parceiro_id||!formNova.contrato_id||!formNova.valor_comissao||!formNova.motivo||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Registrar"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal novo parceiro */}
      {modalParceiro && (
        <div style={ovStyle}>
          <div style={modalStyle}>
            <h2 style={{fontSize:16,fontWeight:600,margin:"0 0 16px"}}>Cadastrar parceiro</h2>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
              <div><label style={labelStyle}>Nome *</label><input value={formParceiro.nome} onChange={e=>setFormParceiro(f=>({...f,nome:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>Tipo</label>
                <select value={formParceiro.tipo_pessoa} onChange={e=>setFormParceiro(f=>({...f,tipo_pessoa:e.target.value}))} style={inputStyle}>
                  <option value="PF">Pessoa Física</option>
                  <option value="PJ">Pessoa Jurídica</option>
                </select>
              </div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
              <div><label style={labelStyle}>CPF/CNPJ</label><input value={formParceiro.cpf_cnpj} onChange={e=>setFormParceiro(f=>({...f,cpf_cnpj:e.target.value}))} style={inputStyle}/></div>
              <div><label style={labelStyle}>E-mail</label><input type="email" value={formParceiro.email} onChange={e=>setFormParceiro(f=>({...f,email:e.target.value}))} style={inputStyle}/></div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
              <div><label style={labelStyle}>Chave PIX</label><input value={formParceiro.pix_chave} onChange={e=>setFormParceiro(f=>({...f,pix_chave:e.target.value}))} placeholder="CPF, e-mail, telefone ou chave aleatória" style={inputStyle}/></div>
              <div><label style={labelStyle}>Valor fixo padrão (R$)</label><input type="number" step="0.01" value={formParceiro.valor_fixo_padrao} onChange={e=>setFormParceiro(f=>({...f,valor_fixo_padrao:e.target.value}))} style={inputStyle}/></div>
            </div>
            <div style={{display:"flex",justifyContent:"flex-end",gap:8}}>
              <button onClick={()=>setModalParceiro(false)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleParceiro} disabled={!formParceiro.nome||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Cadastrar"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal aprovar */}
      {modalAprovar && (
        <div style={ovStyle}>
          <div style={{...modalStyle,maxWidth:400}}>
            <h2 style={{fontSize:16,fontWeight:600,margin:"0 0 6px"}}>Aprovação de comissão</h2>
            <p style={{fontSize:13,color:"#6B7280",margin:"0 0 14px"}}>{modalAprovar.numero_comissao} · {fmtM(modalAprovar.valor_comissao)} · {modalAprovar.parceiro_nome}</p>
            <div style={{marginBottom:10}}><label style={labelStyle}>Decisão *</label>
              <select value={formAprovar.decisao} onChange={e=>setFormAprovar(f=>({...f,decisao:e.target.value}))} style={inputStyle}>
                <option value="APROVADA">Aprovar</option>
                <option value="REPROVADA">Reprovar</option>
              </select>
            </div>
            {formAprovar.decisao==="REPROVADA" && (
              <div style={{marginBottom:10}}><label style={labelStyle}>Motivo da reprovação *</label>
                <textarea value={formAprovar.motivo_reprovacao} onChange={e=>setFormAprovar(f=>({...f,motivo_reprovacao:e.target.value}))} rows={2} style={{...inputStyle,resize:"vertical"}}/>
              </div>
            )}
            <div style={{display:"flex",justifyContent:"flex-end",gap:8,marginTop:14}}>
              <button onClick={()=>setModalAprovar(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handleAprovar} disabled={salvando} style={formAprovar.decisao==="REPROVADA"?{...btnPrimStyle,background:"#B91C1C"}:btnPrimStyle}>{salvando?"Salvando...":formAprovar.decisao==="APROVADA"?"Aprovar":"Reprovar"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal pagar */}
      {modalPagar && (
        <div style={ovStyle}>
          <div style={{...modalStyle,maxWidth:400}}>
            <h2 style={{fontSize:16,fontWeight:600,margin:"0 0 6px"}}>Registrar pagamento</h2>
            <p style={{fontSize:13,color:"#6B7280",margin:"0 0 14px"}}>{modalPagar.parceiro_nome} · {fmtM(modalPagar.valor_comissao)}</p>
            {modalPagar.pix_chave && <div style={{background:"#F0FDF4",border:"1px solid #BBF7D0",borderRadius:8,padding:"8px 12px",marginBottom:12,fontSize:12,color:"#15803D"}}>PIX: {modalPagar.pix_chave}</div>}
            <div style={{marginBottom:10}}><label style={labelStyle}>Data do pagamento *</label><input type="date" value={formPagar.data_pagamento} onChange={e=>setFormPagar(f=>({...f,data_pagamento:e.target.value}))} style={inputStyle}/></div>
            <div style={{marginBottom:10}}><label style={labelStyle}>Forma *</label>
              <select value={formPagar.forma_pagamento} onChange={e=>setFormPagar(f=>({...f,forma_pagamento:e.target.value}))} style={inputStyle}>
                {FORMAS.map(fo=><option key={fo} value={fo}>{fo}</option>)}
              </select>
            </div>
            <div style={{marginBottom:14}}><label style={labelStyle}>Identificador</label><input value={formPagar.identificador_pag} onChange={e=>setFormPagar(f=>({...f,identificador_pag:e.target.value}))} placeholder="Código da transação" style={inputStyle}/></div>
            <div style={{display:"flex",justifyContent:"flex-end",gap:8}}>
              <button onClick={()=>setModalPagar(null)} style={btnSecStyle}>Cancelar</button>
              <button onClick={handlePagar} disabled={!formPagar.data_pagamento||salvando} style={btnPrimStyle}>{salvando?"Salvando...":"Confirmar pagamento"}</button>
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
const ovStyle     ={position:"fixed",inset:0,background:"rgba(0,0,0,0.45)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:50};
const modalStyle  ={background:"#fff",borderRadius:12,padding:"1.5rem",width:480,maxWidth:"90vw",maxHeight:"90vh",overflowY:"auto"};
