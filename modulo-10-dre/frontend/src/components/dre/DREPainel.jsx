// src/components/dre/DREPainel.jsx
"use client";
import { useState, useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path) => fetch(`${BASE}${path}`).then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtM  = v => Number(v||0).toLocaleString("pt-BR", { style:"currency", currency:"BRL" });
const fmtP  = v => `${Number(v||0).toFixed(1)}%`;
const fmtMs = d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR",{month:"short",year:"numeric"}).replace(".","") : "—";
const cor   = v => Number(v) >= 0 ? "#15803D" : "#B91C1C";
const bgCor = v => Number(v) >= 0 ? "#DCFCE7" : "#FEE2E2";

const LINHAS_DRE = [
  { key:"receita_bruta",           label:"(+) Receita Bruta",                    nivel:0, destaque:true,  cor:"#111827" },
  { key:"receita_asp",             label:"    ASP",                               nivel:1, destaque:false, cor:"#374151" },
  { key:"receita_bsp",             label:"    BSP",                               nivel:1, destaque:false, cor:"#374151" },
  { key:"receita_bpo",             label:"    BPO",                               nivel:1, destaque:false, cor:"#374151" },
  { key:"deducoes_impostos",       label:"(-) Impostos sobre serviços",           nivel:0, destaque:false, cor:"#B91C1C", negativo:true },
  { key:"receita_liquida",         label:"(=) Receita Líquida",                   nivel:0, destaque:true,  cor:"#1E40AF", borda:true },
  { key:"custo_folha",             label:"(-) Folha de Pagamento",                nivel:1, destaque:false, cor:"#374151", negativo:true },
  { key:"custo_beneficios",        label:"(-) Benefícios",                        nivel:1, destaque:false, cor:"#374151", negativo:true },
  { key:"custo_fornecedores",      label:"(-) Fornecedores",                      nivel:1, destaque:false, cor:"#374151", negativo:true },
  { key:"total_custos",            label:"(-) Total Custos Operacionais",         nivel:0, destaque:false, cor:"#B91C1C", negativo:true },
  { key:"lucro_bruto",             label:"(=) Lucro Bruto",                       nivel:0, destaque:true,  cor:"#1E40AF", borda:true },
  { key:"desp_administrativa",     label:"(-) Despesas Administrativas",          nivel:1, destaque:false, cor:"#374151", negativo:true },
  { key:"desp_comissoes",          label:"(-) Comissões",                         nivel:1, destaque:false, cor:"#374151", negativo:true },
  { key:"desp_outros",             label:"(-) Outras Despesas",                   nivel:1, destaque:false, cor:"#374151", negativo:true },
  { key:"total_desp_operacionais", label:"(-) Total Desp. Operacionais",          nivel:0, destaque:false, cor:"#B91C1C", negativo:true },
  { key:"ebitda",                  label:"(=) EBITDA",                            nivel:0, destaque:true,  cor:null,      borda:true, dinamico:true },
  { key:"margem_ebitda_pct",       label:"    Margem EBITDA",                     nivel:1, destaque:false, cor:"#6B7280", percentual:true },
  { key:"resultado_liquido",       label:"(=) Resultado Líquido",                 nivel:0, destaque:true,  cor:null,      borda:true, dinamico:true },
  { key:"margem_liquida_pct",      label:"    Margem Líquida",                    nivel:1, destaque:false, cor:"#6B7280", percentual:true },
];

export default function DREPainel() {
  const [mensal,   setMensal]   = useState([]);
  const [acum,     setAcum]     = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [erro,     setErro]     = useState(null);
  const [ano,      setAno]      = useState(new Date().getFullYear());
  const [aba,      setAba]      = useState("completo"); // completo | acumulado | comparativo
  const [comparat, setComparat] = useState(null);

  const carregar = async (a) => {
    setLoading(true);
    try {
      const [m, ac, comp] = await Promise.all([
        api(`/dre/mensal?ano=${a}`),
        api(`/dre/acumulado?ano=${a}`),
        api(`/dre/comparativo/${a}`),
      ]);
      setMensal(m);
      setAcum(ac[0] || null);
      setComparat(comp);
    } catch(e){ setErro(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { carregar(ano); }, [ano]);

  const anos = Array.from({length:4}, (_,i) => new Date().getFullYear() - i);

  // Valor formatado por tipo de linha
  const fmtValor = (linha, val) => {
    if (linha.percentual) return <span style={{color:"#6B7280"}}>{fmtP(val)}</span>;
    if (linha.dinamico)   return <span style={{color:cor(val),fontWeight:600}}>{fmtM(val)}</span>;
    if (linha.negativo)   return <span style={{color:"#B91C1C"}}>{Number(val)>0?`(${fmtM(val)})`:fmtM(val)}</span>;
    return <span style={{color:linha.cor||"#111827"}}>{fmtM(val)}</span>;
  };

  return (
    <div style={{ padding:"2rem", maxWidth:1200, margin:"0 auto" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1.25rem" }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0, color:"#111827" }}>DRE Gerencial</h1>
          <p style={{ margin:"3px 0 0", fontSize:13, color:"#6B7280" }}>Demonstrativo de Resultado</p>
        </div>
        <div style={{ display:"flex", gap:8, alignItems:"center" }}>
          <select value={ano} onChange={e=>setAno(parseInt(e.target.value))} style={inputStyle}>
            {anos.map(a=><option key={a} value={a}>{a}</option>)}
          </select>
        </div>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={()=>setErro(null)} style={{background:"none",border:"none",cursor:"pointer"}}>✕</button></div>}

      {/* Cards resumo do ano */}
      {acum && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10, marginBottom:20 }}>
          {[
            ["Receita Bruta",   acum.receita_bruta,    "#1E40AF","#DBEAFE"],
            ["Receita Líquida", acum.receita_liquida,  "#185FA5","#EFF6FF"],
            ["EBITDA",          acum.ebitda,            cor(acum.ebitda), bgCor(acum.ebitda)],
            ["Margem EBITDA",   null,                   cor(acum.ebitda), bgCor(acum.ebitda)],
          ].map(([label, valor, tc, bg], i) => (
            <div key={label} style={{ background:bg, borderRadius:10, padding:"12px 14px" }}>
              <div style={{ fontSize:11, color:tc, fontWeight:500, marginBottom:4 }}>{label} — {ano}</div>
              <div style={{ fontSize:18, fontWeight:600, color:"#111827", fontFamily:"monospace" }}>
                {i===3 ? fmtP(acum.margem_ebitda_pct) : fmtM(valor)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Abas */}
      <div style={{ display:"flex", borderBottom:"1px solid #E5E7EB", marginBottom:16 }}>
        {[["completo","DRE Completo"],["acumulado","Acumulado do Ano"],["comparativo","Comparativo YoY"]].map(([id,label])=>(
          <div key={id} onClick={()=>setAba(id)} style={{ padding:"9px 18px", fontSize:13, cursor:"pointer", borderBottom:aba===id?"2px solid #185FA5":"2px solid transparent", color:aba===id?"#185FA5":"#6B7280", fontWeight:aba===id?500:400, marginBottom:"-1px" }}>{label}</div>
        ))}
      </div>

      {loading ? <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Carregando...</div> : (

        <>
          {/* DRE COMPLETO */}
          {aba==="completo" && mensal.length > 0 && (
            <div style={{ overflowX:"auto" }}>
              <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12, minWidth:900 }}>
                <thead>
                  <tr style={{ background:"#F9FAFB", borderBottom:"2px solid #E5E7EB" }}>
                    <th style={{ padding:"10px 14px", textAlign:"left", fontWeight:500, color:"#374151", minWidth:240 }}>Linha</th>
                    {mensal.map(m=>(
                      <th key={m.mes} style={{ padding:"10px 10px", textAlign:"right", fontWeight:500, color:"#374151", whiteSpace:"nowrap" }}>
                        {fmtMs(m.mes)}
                      </th>
                    ))}
                    {acum && <th style={{ padding:"10px 10px", textAlign:"right", fontWeight:600, color:"#185FA5", background:"#EFF6FF", whiteSpace:"nowrap" }}>Acum. {ano}</th>}
                  </tr>
                </thead>
                <tbody>
                  {LINHAS_DRE.map((linha, idx) => (
                    <tr key={linha.key} style={{
                      borderBottom: linha.borda ? "2px solid #E5E7EB" : "1px solid #F3F4F6",
                      background:   linha.destaque ? "#FAFAFA" : "#fff",
                    }}>
                      <td style={{ padding:"8px 14px", fontWeight:linha.destaque?600:400, color:linha.cor||"#374151", paddingLeft: linha.nivel===1?"28px":"14px" }}>
                        {linha.label}
                      </td>
                      {mensal.map(m=>(
                        <td key={m.mes} style={{ padding:"8px 10px", textAlign:"right", fontFamily:"monospace" }}>
                          {fmtValor(linha, m[linha.key])}
                        </td>
                      ))}
                      {acum && (
                        <td style={{ padding:"8px 10px", textAlign:"right", fontFamily:"monospace", background:"#EFF6FF" }}>
                          {fmtValor(linha, acum[linha.key])}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ACUMULADO */}
          {aba==="acumulado" && acum && (
            <div style={{ maxWidth:600 }}>
              <div style={{ background:"#fff", border:"1px solid #E5E7EB", borderRadius:10, overflow:"hidden" }}>
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                  <thead>
                    <tr style={{ background:"#F9FAFB", borderBottom:"2px solid #E5E7EB" }}>
                      <th style={{ padding:"10px 14px", textAlign:"left", fontWeight:500, color:"#374151" }}>Linha</th>
                      <th style={{ padding:"10px 14px", textAlign:"right", fontWeight:500, color:"#185FA5" }}>Acumulado {ano}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {LINHAS_DRE.filter(l=>l.nivel===0).map(linha=>(
                      <tr key={linha.key} style={{ borderBottom:linha.borda?"2px solid #E5E7EB":"1px solid #F3F4F6", background:linha.destaque?"#FAFAFA":"#fff" }}>
                        <td style={{ padding:"10px 14px", fontWeight:linha.destaque?600:400, color:linha.cor||"#374151" }}>{linha.label}</td>
                        <td style={{ padding:"10px 14px", textAlign:"right", fontFamily:"monospace" }}>{fmtValor(linha, acum[linha.key])}</td>
                      </tr>
                    ))}
                    <tr style={{ background:"#EFF6FF", borderTop:"2px solid #BFDBFE" }}>
                      <td style={{ padding:"10px 14px", fontWeight:600, color:"#185FA5" }}>Margem EBITDA</td>
                      <td style={{ padding:"10px 14px", textAlign:"right", fontFamily:"monospace", fontWeight:600, color:cor(acum.ebitda) }}>{fmtP(acum.margem_ebitda_pct)}</td>
                    </tr>
                    <tr style={{ background:"#EFF6FF" }}>
                      <td style={{ padding:"10px 14px", fontWeight:600, color:"#185FA5" }}>Margem Líquida</td>
                      <td style={{ padding:"10px 14px", textAlign:"right", fontFamily:"monospace", fontWeight:600, color:cor(acum.resultado_liquido) }}>{fmtP(acum.margem_liquida_pct)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* COMPARATIVO YoY */}
          {aba==="comparativo" && comparat && (
            <div style={{ background:"#fff", border:"1px solid #E5E7EB", borderRadius:10, overflow:"hidden" }}>
              <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                <thead>
                  <tr style={{ background:"#F9FAFB", borderBottom:"2px solid #E5E7EB" }}>
                    {["Mês","Receita atual","Receita ant.","Variação","EBITDA atual","EBITDA ant.","Margem atual","Margem ant."].map(h=>(
                      <th key={h} style={{ padding:"9px 12px", textAlign:"right", fontWeight:500, color:"#374151", fontSize:11, whiteSpace:"nowrap", ":first-child":{textAlign:"left"} }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {comparat.comparativo.map((c,i)=>(
                    <tr key={i} style={{ borderBottom:"1px solid #F3F4F6", background:i%2===0?"#fff":"#FAFAFA" }}>
                      <td style={{ padding:"9px 12px", fontWeight:500 }}>{fmtMs(c.mes)}</td>
                      <td style={{ padding:"9px 12px", textAlign:"right", fontFamily:"monospace" }}>{fmtM(c.receita_atual)}</td>
                      <td style={{ padding:"9px 12px", textAlign:"right", fontFamily:"monospace", color:"#9CA3AF" }}>{fmtM(c.receita_anterior)}</td>
                      <td style={{ padding:"9px 12px", textAlign:"right", fontFamily:"monospace", fontWeight:600, color:Number(c.variacao_receita_pct||0)>=0?"#15803D":"#B91C1C" }}>
                        {c.variacao_receita_pct!=null ? `${Number(c.variacao_receita_pct)>=0?"+":""}${fmtP(c.variacao_receita_pct)}` : "—"}
                      </td>
                      <td style={{ padding:"9px 12px", textAlign:"right", fontFamily:"monospace", color:cor(c.ebitda_atual) }}>{fmtM(c.ebitda_atual)}</td>
                      <td style={{ padding:"9px 12px", textAlign:"right", fontFamily:"monospace", color:"#9CA3AF" }}>{fmtM(c.ebitda_anterior)}</td>
                      <td style={{ padding:"9px 12px", textAlign:"right", fontFamily:"monospace", color:cor(c.margem_atual) }}>{fmtP(c.margem_atual)}</td>
                      <td style={{ padding:"9px 12px", textAlign:"right", fontFamily:"monospace", color:"#9CA3AF" }}>{fmtP(c.margem_anterior)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {mensal.length===0 && aba==="completo" && (
            <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Nenhum dado para {ano}.</div>
          )}
        </>
      )}
    </div>
  );
}

const inputStyle = { padding:"7px 11px", border:"1px solid #D1D5DB", borderRadius:7, fontSize:13, background:"#fff", color:"#111827" };
const alertStyle = { padding:"10px 14px", borderRadius:8, fontSize:13, marginBottom:12, background:"#FEE2E2", color:"#B91C1C", display:"flex", justifyContent:"space-between" };
