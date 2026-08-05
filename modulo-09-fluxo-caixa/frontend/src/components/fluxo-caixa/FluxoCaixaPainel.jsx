// src/components/fluxo-caixa/FluxoCaixaPainel.jsx
"use client";
import { useState, useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const api  = (path) => fetch(`${BASE}${path}`).then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || "Erro"); }));

const fmtMoeda = v => Number(v||0).toLocaleString("pt-BR", { style:"currency", currency:"BRL" });
const fmtMes   = d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR", { month:"short", year:"numeric" }).replace(".","") : "—";
const fmtData  = d => d ? new Date(d+"T00:00:00").toLocaleDateString("pt-BR") : "—";
const pct      = (a, b) => b ? Math.round((Number(a)/Number(b))*100) : 0;

const cor = (v) => Number(v) >= 0 ? "#15803D" : "#B91C1C";

export default function FluxoCaixaPainel() {
  const [mensal,   setMensal]   = useState([]);
  const [resumo,   setResumo]   = useState(null);
  const [diario,   setDiario]   = useState([]);
  const [mesSel,   setMesSel]   = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [loadDia,  setLoadDia]  = useState(false);
  const [erro,     setErro]     = useState(null);
  const [aba,      setAba]      = useState("mensal"); // mensal | diario

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api("/fluxo-caixa/mensal?meses_atras=5&meses_frente=3"),
      api("/fluxo-caixa/resumo"),
    ])
    .then(([m, r]) => { setMensal(m); setResumo(r); })
    .catch(e => setErro(e.message))
    .finally(() => setLoading(false));
  }, []);

  const verDia = async (mes) => {
    setMesSel(mes);
    setAba("diario");
    setLoadDia(true);
    try { setDiario(await api(`/fluxo-caixa/diario?mes=${mes}`)); }
    catch(e){ setErro(e.message); }
    finally { setLoadDia(false); }
  };

  // Barra de progresso
  const Barra = ({ valor, max, cor: c }) => (
    <div style={{ height:6, background:"#F3F4F6", borderRadius:3, overflow:"hidden", marginTop:4 }}>
      <div style={{ height:"100%", width:`${Math.min(100, pct(valor, max))}%`, background:c, borderRadius:3, transition:"width 0.3s" }}/>
    </div>
  );

  const maxEntrada = Math.max(...mensal.map(m => Math.max(Number(m.entradas_realizadas), Number(m.entradas_projetadas))), 1);
  const maxSaida   = Math.max(...mensal.map(m => Math.max(Number(m.saidas_realizadas),   Number(m.saidas_projetadas))),   1);

  return (
    <div style={{ padding:"2rem", maxWidth:1100, margin:"0 auto" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1.25rem" }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:600, margin:0, color:"#111827" }}>Fluxo de Caixa</h1>
          <p style={{ margin:"3px 0 0", fontSize:13, color:"#6B7280" }}>Projetado × Realizado</p>
        </div>
      </div>

      {erro && <div style={alertStyle}>{erro}<button onClick={()=>setErro(null)} style={{background:"none",border:"none",cursor:"pointer"}}>✕</button></div>}

      {/* Cards de resumo do mês atual */}
      {resumo && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10, marginBottom:20 }}>
          {[
            ["Entradas realizadas", resumo.entradas_realizadas, "#15803D", "#DCFCE7"],
            ["Entradas projetadas", resumo.entradas_projetadas, "#1E40AF", "#DBEAFE"],
            ["Saídas realizadas",   resumo.saidas_realizadas,   "#B91C1C", "#FEE2E2"],
            ["Saldo projetado",     resumo.saldo_projetado,     cor(resumo.saldo_projetado), Number(resumo.saldo_projetado)>=0?"#DCFCE7":"#FEE2E2"],
          ].map(([label, valor, textC, bgC]) => (
            <div key={label} style={{ background:bgC, borderRadius:10, padding:"12px 14px" }}>
              <div style={{ fontSize:11, color:textC, fontWeight:500, marginBottom:4 }}>{label}</div>
              <div style={{ fontSize:18, fontWeight:600, color:"#111827", fontFamily:"monospace" }}>{fmtMoeda(valor)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Abas */}
      <div style={{ display:"flex", borderBottom:"1px solid #E5E7EB", marginBottom:16 }}>
        {[["mensal","📅 Visão mensal"],["diario",`📋 Detalhe${mesSel?" — "+fmtMes(mesSel):""}`]].map(([id,label])=>(
          <div key={id} onClick={()=>setAba(id)} style={{ padding:"9px 18px", fontSize:13, cursor:"pointer", borderBottom: aba===id?"2px solid #185FA5":"2px solid transparent", color:aba===id?"#185FA5":"#6B7280", fontWeight:aba===id?500:400, marginBottom:"-1px" }}>{label}</div>
        ))}
      </div>

      {/* VISÃO MENSAL */}
      {aba==="mensal" && (
        loading ? <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Carregando...</div> :
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {/* Legenda */}
          <div style={{ display:"flex", gap:16, fontSize:12, color:"#6B7280", marginBottom:4 }}>
            {[["#15803D","Realizado"],["#93C5FD","Projetado"],["#D1D5DB","Barra de progresso"]].map(([c,l])=>(
              <span key={l} style={{ display:"flex", alignItems:"center", gap:4 }}>
                <span style={{ width:12, height:12, borderRadius:2, background:c, display:"inline-block" }}/>
                {l}
              </span>
            ))}
          </div>

          {mensal.map((m, i) => {
            const isMesAtual = new Date(m.mes+"T00:00:00").getMonth() === new Date().getMonth() && new Date(m.mes+"T00:00:00").getFullYear() === new Date().getFullYear();
            const isFuturo   = new Date(m.mes+"T00:00:00") > new Date();
            return (
              <div key={m.mes}
                onClick={() => verDia(m.mes)}
                style={{ background: isMesAtual?"#EFF6FF":"#fff", border: isMesAtual?"1px solid #BFDBFE":"1px solid #E5E7EB", borderRadius:10, padding:"14px 16px", cursor:"pointer", transition:"box-shadow 0.1s" }}
                onMouseEnter={e=>e.currentTarget.style.boxShadow="0 2px 8px rgba(0,0,0,0.08)"}
                onMouseLeave={e=>e.currentTarget.style.boxShadow="none"}
              >
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
                  <div style={{ minWidth:90, fontSize:13, fontWeight:600, color:"#111827" }}>
                    {fmtMes(m.mes).toUpperCase()}
                    {isMesAtual && <span style={{ marginLeft:6, fontSize:10, background:"#185FA5", color:"#fff", padding:"1px 6px", borderRadius:10 }}>atual</span>}
                    {isFuturo   && <span style={{ marginLeft:6, fontSize:10, background:"#F3F4F6", color:"#9CA3AF", padding:"1px 6px", borderRadius:10 }}>futuro</span>}
                  </div>
                  <div style={{ flex:1, display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr 1fr", gap:8, fontSize:12 }}>
                    {[
                      ["Entradas real.", m.entradas_realizadas, "#15803D"],
                      ["Entradas proj.", m.entradas_projetadas, "#1E40AF"],
                      ["Saídas real.",   m.saidas_realizadas,   "#B91C1C"],
                      ["Saídas proj.",   m.saidas_projetadas,   "#9A3412"],
                      ["Saldo",          m.saldo_realizado,     cor(m.saldo_realizado)],
                    ].map(([label, val, c]) => (
                      <div key={label}>
                        <div style={{ color:"#9CA3AF", fontSize:11 }}>{label}</div>
                        <div style={{ fontFamily:"monospace", fontWeight:500, color:c, fontSize:12 }}>{fmtMoeda(val)}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize:11, color:"#9CA3AF", minWidth:60, textAlign:"right" }}>
                    Ver detalhe →
                  </div>
                </div>

                {/* Barras visuais */}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
                  <div>
                    <div style={{ fontSize:11, color:"#6B7280", marginBottom:2 }}>Entradas: {pct(m.entradas_realizadas, m.entradas_projetadas||m.entradas_realizadas)}% realizado</div>
                    <Barra valor={m.entradas_realizadas} max={maxEntrada} cor="#15803D"/>
                    <Barra valor={m.entradas_projetadas} max={maxEntrada} cor="#93C5FD"/>
                  </div>
                  <div>
                    <div style={{ fontSize:11, color:"#6B7280", marginBottom:2 }}>Saídas: {pct(m.saidas_realizadas, m.saidas_projetadas||m.saidas_realizadas)}% realizado</div>
                    <Barra valor={m.saidas_realizadas} max={maxSaida} cor="#B91C1C"/>
                    <Barra valor={m.saidas_projetadas} max={maxSaida} cor="#FCA5A5"/>
                  </div>
                </div>

                {/* Desvios */}
                {(Number(m.desvio_entradas) !== 0 || Number(m.desvio_saidas) !== 0) && (
                  <div style={{ display:"flex", gap:16, marginTop:8, fontSize:11 }}>
                    {Number(m.desvio_entradas) !== 0 && (
                      <span style={{ color: Number(m.desvio_entradas)>=0?"#15803D":"#B91C1C" }}>
                        Desvio entradas: {Number(m.desvio_entradas)>=0?"+":""}{fmtMoeda(m.desvio_entradas)}
                      </span>
                    )}
                    {Number(m.desvio_saidas) !== 0 && (
                      <span style={{ color: Number(m.desvio_saidas)<=0?"#15803D":"#B91C1C" }}>
                        Desvio saídas: {Number(m.desvio_saidas)>=0?"+":""}{fmtMoeda(m.desvio_saidas)}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* DETALHE DIÁRIO */}
      {aba==="diario" && (
        loadDia ? <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Carregando detalhes...</div> :
        diario.length===0 ? <div style={{ padding:"3rem", textAlign:"center", color:"#9CA3AF" }}>Nenhum lançamento para este mês.</div> :
        <div>
          {/* Totais do mês */}
          {(() => {
            const ent = diario.filter(d=>d.sentido==="ENTRADA").reduce((s,d)=>s+Number(d.valor),0);
            const sai = diario.filter(d=>d.sentido==="SAIDA").reduce((s,d)=>s+Number(d.valor),0);
            return (
              <div style={{ display:"flex", gap:10, marginBottom:16 }}>
                {[["Total entradas",fmtMoeda(ent),"#DCFCE7","#15803D"],["Total saídas",fmtMoeda(sai),"#FEE2E2","#B91C1C"],["Saldo do mês",fmtMoeda(ent-sai),ent-sai>=0?"#DCFCE7":"#FEE2E2",cor(ent-sai)]].map(([l,v,bg,tc])=>(
                  <div key={l} style={{ flex:1, background:bg, borderRadius:10, padding:"12px 14px" }}>
                    <div style={{ fontSize:11, color:tc, marginBottom:3 }}>{l}</div>
                    <div style={{ fontSize:16, fontWeight:600, fontFamily:"monospace", color:"#111827" }}>{v}</div>
                  </div>
                ))}
              </div>
            );
          })()}

          <div style={{ background:"#fff", border:"1px solid #E5E7EB", borderRadius:10, overflow:"hidden" }}>
            <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
              <thead>
                <tr style={{ background:"#F9FAFB", borderBottom:"1px solid #E5E7EB" }}>
                  {["Data","Descrição","Categoria","Tipo","Origem","Valor"].map(h=>(
                    <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontWeight:500, color:"#374151", fontSize:11 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {diario.map((d,i)=>(
                  <tr key={i} style={{ borderBottom:"1px solid #F3F4F6", background:i%2===0?"#fff":"#FAFAFA" }}>
                    <td style={{ padding:"9px 12px", color:"#6B7280" }}>{fmtData(d.data)}</td>
                    <td style={{ padding:"9px 12px", color:"#111827", maxWidth:200, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{d.descricao}</td>
                    <td style={{ padding:"9px 12px", fontSize:11, color:"#6B7280" }}>{d.categoria}</td>
                    <td style={{ padding:"9px 12px" }}>
                      <span style={{ padding:"2px 8px", borderRadius:20, fontSize:11, fontWeight:500,
                        background: d.natureza==="REALIZADO"?"#DCFCE7":"#EFF6FF",
                        color:      d.natureza==="REALIZADO"?"#15803D":"#1E40AF" }}>
                        {d.natureza}
                      </span>
                    </td>
                    <td style={{ padding:"9px 12px", fontFamily:"monospace", fontSize:11, color:"#9CA3AF" }}>{d.origem_numero}</td>
                    <td style={{ padding:"9px 12px", fontFamily:"monospace", fontWeight:600,
                      color: d.sentido==="ENTRADA"?"#15803D":"#B91C1C", textAlign:"right" }}>
                      {d.sentido==="ENTRADA"?"+":"-"}{fmtMoeda(d.valor)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

const alertStyle = { padding:"10px 14px", borderRadius:8, fontSize:13, marginBottom:12, background:"#FEE2E2", color:"#B91C1C", display:"flex", justifyContent:"space-between" };
