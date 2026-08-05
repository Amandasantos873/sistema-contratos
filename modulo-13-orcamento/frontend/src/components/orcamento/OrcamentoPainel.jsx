// src/components/orcamento/OrcamentoPainel.jsx
"use client";
import { useState, useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path, opts={}) =>
  fetch(`${BASE}${path}`, { headers:{"Content-Type":"application/json"}, ...opts })
    .then(r => r.ok ? r.json() : r.json().then(e=>{ throw new Error(e.detail||"Erro"); }));

const fmtM = v => Number(v||0).toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
const fmtP = v => `${Number(v||0).toFixed(1)}%`;
const fmtMs= d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR",{month:"short"}).replace(".","").toUpperCase() : "—";
const cor  = v => Number(v)>=0 ? "#15803D" : "#B91C1C";
const bgCor= v => Number(v)>=0 ? "#DCFCE7" : "#FEE2E2";

const MODALIDADES = ["ASP","BSP","BPO","TOTAL"];
const TIPOS_DESP  = ["FOLHA","BENEFICIO","FORNECEDOR","IMPOSTO","ADMINISTRATIVA","COMISSAO"];

export default function OrcamentoPainel() {
  const [orcamentos, setOrcamentos] = useState([]);
  const [orcAtivo,   setOrcAtivo]   = useState(null);
  const [resumo,     setResumo]     = useState([]);
  const [receitas,   setReceitas]   = useState([]);
  const [despesas,   setDespesas]   = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [erro,       setErro]       = useState(null);
  const [aba,        setAba]        = useState("painel");  // painel | receitas | despesas | setup
  const [anoSel,     setAnoSel]     = useState(new Date().getFullYear());

  // Setup
  const [modalSetup,  setModalSetup]  = useState(false);
  const [formSetup,   setFormSetup]   = useState({ ano: new Date().getFullYear()+1, descricao:"" });
  const [metas,       setMetas]       = useState({ ASP:"", BSP:"", BPO:"" });
  const [metasDesp,   setMetasDesp]   = useState({});
  const [categorias,  setCategorias]  = useState([]);
  const [centros,     setCentros]     = useState([]);
  const [salvando,    setSalvando]    = useState(false);
  const [stepSetup,   setStepSetup]   = useState(1); // 1=criar, 2=receita, 3=despesa

  const carregar = async (ano) => {
    setLoading(true);
    try {
      const [orcs, res, rec, desp] = await Promise.all([
        api("/orcamentos"),
        api(`/orcamentos/resumo?ano=${ano}`),
        api(`/orcamentos/realizado/receita?ano=${ano}&modalidade=TOTAL`),
        api(`/orcamentos/realizado/despesa?ano=${ano}`),
      ]);
      setOrcamentos(orcs);
      setOrcAtivo(orcs.find(o=>o.ano===ano&&o.status==="ATIVO")||null);
      setResumo(res);
      setReceitas(rec);
      setDespesas(desp);
    } catch(e){ setErro(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    carregar(anoSel);
    Promise.all([api("/categorias-despesa"), api("/centros-custo")])
      .then(([cats,cts])=>{ setCategorias(cats); setCentros(cts); });
  }, [anoSel]);

  const handleCriarOrcamento = async () => {
    setSalvando(true);
    try {
      const novo = await api("/orcamentos", {method:"POST", body:JSON.stringify(formSetup)});
      // Define metas de receita
      for (const mod of MODALIDADES.filter(m=>m!=="TOTAL")) {
        const val = parseFloat(metas[mod]);
        if (val > 0) {
          await api(`/orcamentos/${novo.id}/receita`, {method:"POST", body:JSON.stringify({modalidade:mod, valor_anual:val})});
        }
      }
      // Total = soma das modalidades
      const totalAnual = Object.values(metas).reduce((s,v)=>s+parseFloat(v||0),0);
      if (totalAnual > 0) {
        await api(`/orcamentos/${novo.id}/receita`, {method:"POST", body:JSON.stringify({modalidade:"TOTAL", valor_anual:totalAnual})});
      }
      // Metas de despesa
      for (const [key, val] of Object.entries(metasDesp)) {
        const [cat_id, cc_id] = key.split("_");
        if (parseFloat(val) > 0) {
          await api(`/orcamentos/${novo.id}/despesa`, {method:"POST", body:JSON.stringify({categoria_id:parseInt(cat_id), centro_custo_id:parseInt(cc_id), valor_anual:parseFloat(val)})});
        }
      }
      // Ativar
      await api(`/orcamentos/${novo.id}/ativar`, {method:"PATCH"});
      setModalSetup(false);
      setAnoSel(formSetup.ano);
      carregar(formSetup.ano);
    } catch(e){ setErro(e.message); }
    finally { setSalvando(false); }
  };

  const resumoAno = resumo[0];
  const mesesUnicos = [...new Set(receitas.map(r=>r.mes))].sort();

  // Agrupa despesas por tipo para exibição
  const despPorTipo = despesas.reduce((acc, d) => {
    const key = d.categoria_tipo;
    if (!acc[key]) acc[key] = {orcado:0, realizado:0};
    acc[key].orcado    += Number(d.valor_orcado);
    acc[key].realizado += Number(d.valor_realizado);
    return acc;
  }, {});

  const Barra = ({pct, cor:c}) => (
    <div style={{height:6,background:"#F3F4F6",borderRadius:3,overflow:"hidden",marginTop:3}}>
      <div style={{height:"100%",width:`${Math.min(100,Number(pct||0))}%`,background:c,borderRadius:3,transition:"width 0.3s"}}/>
    </div>
  );

  return (
    <div style={{padding:"2rem",maxWidth:1100,margin:"0 auto"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"1.25rem"}}>
        <div>
          <h1 style={{fontSize:20,fontWeight:600,margin:0,color:"#111827"}}>Orçamento × Realizado</h1>
          <p style={{margin:"3px 0 0",fontSize:13,color:"#6B7280"}}>Metas anuais distribuídas mensalmente</p>
        </div>
        <div style={{display:"flex",gap:8,alignItems:"center"}}>
          <select value={anoSel} onChange={e=>setAnoSel(parseInt(e.target.value))} style={inputStyle}>
            {[...Array(4)].map((_,i)=>{const a=new Date().getFullYear()-1+i;return<option key={a} value={a}>{a}</option>;})}
          </select>
          <button onClick={()=>{setModalSetup(true);setStepSetup(1);}} style={btnPrimStyle}>+ Novo orçamento</button>
        </div>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={()=>setErro(null)} style={{background:"none",border:"none",cursor:"pointer"}}>✕</button></div>}

      {!orcAtivo && !loading && (
        <div style={{background:"#FEF3C7",border:"1px solid #FDE68A",borderRadius:10,padding:"16px 20px",marginBottom:16,fontSize:13,color:"#92400E"}}>
          ⚠ Nenhum orçamento ativo para {anoSel}. Clique em <strong>+ Novo orçamento</strong> para criar e definir as metas.
        </div>
      )}

      {/* Abas */}
      <div style={{display:"flex",borderBottom:"1px solid #E5E7EB",marginBottom:16}}>
        {[["painel","📊 Painel"],["receitas","📈 Receitas"],["despesas","📉 Despesas"]].map(([id,label])=>(
          <div key={id} onClick={()=>setAba(id)} style={{padding:"9px 18px",fontSize:13,cursor:"pointer",borderBottom:aba===id?"2px solid #185FA5":"2px solid transparent",color:aba===id?"#185FA5":"#6B7280",fontWeight:aba===id?500:400,marginBottom:"-1px"}}>{label}</div>
        ))}
      </div>

      {loading ? <div style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Carregando...</div> : (
        <>
          {/* PAINEL */}
          {aba==="painel" && resumoAno && (
            <div>
              {/* Cards */}
              <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12,marginBottom:20}}>
                {[
                  ["Receita orçada",   resumoAno.receita_orcada,   "#1E40AF","#DBEAFE", resumoAno.receita_realizada],
                  ["Despesa orçada",   resumoAno.despesa_orcada,   "#92400E","#FEF3C7", resumoAno.despesa_realizada],
                  ["Resultado orçado", resumoAno.resultado_orcado, cor(resumoAno.resultado_orcado), bgCor(resumoAno.resultado_orcado), resumoAno.resultado_realizado],
                ].map(([label,orcado,tc,bg,realizado])=>(
                  <div key={label} style={{background:bg,borderRadius:10,padding:"14px 16px"}}>
                    <div style={{fontSize:11,color:tc,fontWeight:500,marginBottom:6}}>{label} — {anoSel}</div>
                    <div style={{fontSize:18,fontWeight:600,fontFamily:"monospace",color:"#111827"}}>{fmtM(orcado)}</div>
                    <div style={{fontSize:12,color:tc,marginTop:4}}>
                      Realizado: <strong style={{fontFamily:"monospace"}}>{fmtM(realizado)}</strong>
                    </div>
                    <Barra pct={Number(orcado)>0?Number(realizado)/Number(orcado)*100:0} cor={tc}/>
                    <div style={{fontSize:11,color:tc,marginTop:3}}>
                      {Number(orcado)>0?fmtP(Number(realizado)/Number(orcado)*100):"—"} atingido
                    </div>
                  </div>
                ))}
              </div>

              {/* Tabela mensal resumida */}
              <div style={{background:"#fff",border:"1px solid #E5E7EB",borderRadius:10,overflow:"hidden"}}>
                <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
                  <thead>
                    <tr style={{background:"#F9FAFB",borderBottom:"1px solid #E5E7EB"}}>
                      <th style={{padding:"9px 14px",textAlign:"left",fontWeight:500,color:"#374151",fontSize:11}}>Mês</th>
                      <th style={{padding:"9px 14px",textAlign:"right",fontWeight:500,color:"#374151",fontSize:11}}>Rec. Orçada</th>
                      <th style={{padding:"9px 14px",textAlign:"right",fontWeight:500,color:"#374151",fontSize:11}}>Rec. Realizada</th>
                      <th style={{padding:"9px 14px",textAlign:"right",fontWeight:500,color:"#374151",fontSize:11}}>Desvio</th>
                      <th style={{padding:"9px 14px",textAlign:"left",fontWeight:500,color:"#374151",fontSize:11,minWidth:120}}>Atingimento</th>
                    </tr>
                  </thead>
                  <tbody>
                    {receitas.map((r,i)=>(
                      <tr key={r.mes} style={{borderBottom:"1px solid #F3F4F6",background:i%2===0?"#fff":"#FAFAFA"}}>
                        <td style={{padding:"9px 14px",fontWeight:500}}>{fmtMs(r.mes)}</td>
                        <td style={{padding:"9px 14px",textAlign:"right",fontFamily:"monospace"}}>{fmtM(r.valor_orcado)}</td>
                        <td style={{padding:"9px 14px",textAlign:"right",fontFamily:"monospace",fontWeight:500}}>{fmtM(r.valor_realizado)}</td>
                        <td style={{padding:"9px 14px",textAlign:"right",fontFamily:"monospace",color:cor(r.desvio)}}>{Number(r.desvio)>=0?"+":""}{fmtM(r.desvio)}</td>
                        <td style={{padding:"9px 14px"}}>
                          <div style={{display:"flex",alignItems:"center",gap:8}}>
                            <Barra pct={r.atingimento_pct} cor={Number(r.atingimento_pct)>=100?"#15803D":"#185FA5"}/>
                            <span style={{fontSize:11,color:"#6B7280",minWidth:38}}>{fmtP(r.atingimento_pct)}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* RECEITAS */}
          {aba==="receitas" && (
            <div style={{background:"#fff",border:"1px solid #E5E7EB",borderRadius:10,overflow:"auto"}}>
              <table style={{width:"100%",borderCollapse:"collapse",fontSize:13,minWidth:700}}>
                <thead>
                  <tr style={{background:"#F9FAFB",borderBottom:"1px solid #E5E7EB"}}>
                    <th style={{padding:"9px 14px",textAlign:"left",fontWeight:500,color:"#374151",fontSize:11}}>Mês</th>
                    <th style={{padding:"9px 14px",textAlign:"right",fontWeight:500,color:"#374151",fontSize:11}}>Orçado</th>
                    <th style={{padding:"9px 14px",textAlign:"right",fontWeight:500,color:"#374151",fontSize:11}}>Realizado</th>
                    <th style={{padding:"9px 14px",textAlign:"right",fontWeight:500,color:"#374151",fontSize:11}}>Desvio</th>
                    <th style={{padding:"9px 14px",textAlign:"right",fontWeight:500,color:"#374151",fontSize:11}}>%</th>
                  </tr>
                </thead>
                <tbody>
                  {receitas.length===0
                    ? <tr><td colSpan={5} style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Sem dados de receita para {anoSel}.</td></tr>
                    : receitas.map((r,i)=>(
                    <tr key={r.mes} style={{borderBottom:"1px solid #F3F4F6",background:i%2===0?"#fff":"#FAFAFA"}}>
                      <td style={{padding:"9px 14px",fontWeight:500}}>{fmtMs(r.mes)}</td>
                      <td style={{padding:"9px 14px",textAlign:"right",fontFamily:"monospace"}}>{fmtM(r.valor_orcado)}</td>
                      <td style={{padding:"9px 14px",textAlign:"right",fontFamily:"monospace",fontWeight:500}}>{fmtM(r.valor_realizado)}</td>
                      <td style={{padding:"9px 14px",textAlign:"right",fontFamily:"monospace",color:cor(r.desvio)}}>{Number(r.desvio)>=0?"+":""}{fmtM(r.desvio)}</td>
                      <td style={{padding:"9px 14px",textAlign:"right",color:Number(r.atingimento_pct)>=100?"#15803D":"#B91C1C",fontWeight:500}}>{fmtP(r.atingimento_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* DESPESAS */}
          {aba==="despesas" && (
            <div style={{display:"flex",flexDirection:"column",gap:10}}>
              {Object.keys(despPorTipo).length===0
                ? <div style={{padding:"3rem",textAlign:"center",color:"#9CA3AF"}}>Sem dados de despesa para {anoSel}.</div>
                : Object.entries(despPorTipo).map(([tipo,d])=>(
                <div key={tipo} style={{background:"#fff",border:"1px solid #E5E7EB",borderRadius:10,padding:"14px 16px"}}>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                    <div style={{fontWeight:500,fontSize:14,color:"#111827"}}>{tipo}</div>
                    <div style={{display:"flex",gap:16,fontSize:12}}>
                      <span style={{color:"#6B7280"}}>Orçado: <strong style={{fontFamily:"monospace",color:"#111827"}}>{fmtM(d.orcado)}</strong></span>
                      <span style={{color:"#6B7280"}}>Realizado: <strong style={{fontFamily:"monospace",color:cor(d.orcado-d.realizado)}}>{fmtM(d.realizado)}</strong></span>
                      <span style={{color:Number(d.realizado)>Number(d.orcado)?"#B91C1C":"#15803D",fontWeight:500}}>{Number(d.orcado)>0?fmtP(d.realizado/d.orcado*100):"—"}</span>
                    </div>
                  </div>
                  <Barra pct={Number(d.orcado)>0?d.realizado/d.orcado*100:0} cor={Number(d.realizado)>Number(d.orcado)?"#B91C1C":"#185FA5"}/>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Modal setup do orçamento */}
      {modalSetup && (
        <div style={ovStyle}>
          <div style={{...modalStyle,maxWidth:560}}>
            <h2 style={{fontSize:16,fontWeight:600,margin:"0 0 4px"}}>Criar orçamento</h2>
            <p style={{fontSize:12,color:"#9CA3AF",margin:"0 0 16px"}}>Passo {stepSetup} de 3</p>

            {/* Step 1: criar */}
            {stepSetup===1 && (
              <>
                <div style={{display:"grid",gridTemplateColumns:"1fr 2fr",gap:10,marginBottom:14}}>
                  <div><label style={labelStyle}>Ano *</label>
                    <input type="number" value={formSetup.ano} onChange={e=>setFormSetup(f=>({...f,ano:parseInt(e.target.value)}))} style={inputStyle}/>
                  </div>
                  <div><label style={labelStyle}>Descrição</label>
                    <input value={formSetup.descricao} onChange={e=>setFormSetup(f=>({...f,descricao:e.target.value}))} placeholder={`Orçamento ${formSetup.ano}`} style={inputStyle}/>
                  </div>
                </div>
                <div style={{display:"flex",justifyContent:"flex-end",gap:8}}>
                  <button onClick={()=>setModalSetup(false)} style={btnSecStyle}>Cancelar</button>
                  <button onClick={()=>setStepSetup(2)} style={btnPrimStyle}>Próximo →</button>
                </div>
              </>
            )}

            {/* Step 2: metas de receita */}
            {stepSetup===2 && (
              <>
                <p style={{fontSize:13,color:"#374151",marginBottom:12}}>Defina a <strong>meta anual de receita</strong> por modalidade. O sistema distribui em 12 meses iguais.</p>
                {["ASP","BSP","BPO"].map(mod=>(
                  <div key={mod} style={{marginBottom:10}}>
                    <label style={labelStyle}>Receita {mod} — Meta anual (R$)</label>
                    <input type="number" step="1000" value={metas[mod]} onChange={e=>setMetas(m=>({...m,[mod]:e.target.value}))} placeholder="0,00" style={inputStyle}/>
                    {metas[mod] && <div style={{fontSize:11,color:"#6B7280",marginTop:3}}>≈ {fmtM(parseFloat(metas[mod]||0)/12)}/mês</div>}
                  </div>
                ))}
                <div style={{display:"flex",justifyContent:"space-between",gap:8,marginTop:14}}>
                  <button onClick={()=>setStepSetup(1)} style={btnSecStyle}>← Voltar</button>
                  <button onClick={()=>setStepSetup(3)} style={btnPrimStyle}>Próximo →</button>
                </div>
              </>
            )}

            {/* Step 3: metas de despesa */}
            {stepSetup===3 && (
              <>
                <p style={{fontSize:13,color:"#374151",marginBottom:12}}>Defina a <strong>meta anual de despesa</strong> por categoria (opcional — preencha as principais).</p>
                <div style={{maxHeight:320,overflowY:"auto",display:"flex",flexDirection:"column",gap:8}}>
                  {categorias.filter(c=>["FOLHA","BENEFICIO","FORNECEDOR","IMPOSTO","ADMINISTRATIVA"].includes(c.tipo)).slice(0,10).map(cat=>(
                    <div key={cat.id} style={{display:"flex",alignItems:"center",gap:10}}>
                      <div style={{flex:1,fontSize:12,color:"#374151"}}>{cat.tipo} — {cat.nome}</div>
                      <input type="number" step="100" placeholder="Meta anual R$"
                        value={metasDesp[`${cat.id}_${centros[0]?.id||1}`]||""}
                        onChange={e=>setMetasDesp(m=>({...m,[`${cat.id}_${centros[0]?.id||1}`]:e.target.value}))}
                        style={{...inputStyle,width:140}}/>
                    </div>
                  ))}
                </div>
                <div style={{display:"flex",justifyContent:"space-between",gap:8,marginTop:14}}>
                  <button onClick={()=>setStepSetup(2)} style={btnSecStyle}>← Voltar</button>
                  <button onClick={handleCriarOrcamento} disabled={salvando} style={btnPrimStyle}>{salvando?"Criando...":"✓ Criar e ativar orçamento"}</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const inputStyle  = {padding:"7px 11px",border:"1px solid #D1D5DB",borderRadius:7,fontSize:13,background:"#fff",color:"#111827",width:"100%",boxSizing:"border-box",display:"block"};
const labelStyle  = {display:"block",fontSize:12,fontWeight:500,color:"#374151",marginBottom:4};
const btnPrimStyle= {padding:"9px 18px",background:"#185FA5",color:"#fff",border:"none",borderRadius:8,fontSize:13,fontWeight:500,cursor:"pointer"};
const btnSecStyle = {padding:"7px 14px",background:"#fff",color:"#374151",border:"1px solid #D1D5DB",borderRadius:8,fontSize:13,cursor:"pointer"};
const alertStyle  = {padding:"10px 14px",borderRadius:8,fontSize:13,marginBottom:12,background:"#FEE2E2",color:"#B91C1C",display:"flex",justifyContent:"space-between"};
const ovStyle     = {position:"fixed",inset:0,background:"rgba(0,0,0,0.45)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:50};
const modalStyle  = {background:"#fff",borderRadius:12,padding:"1.5rem",width:560,maxWidth:"90vw",maxHeight:"90vh",overflowY:"auto"};
