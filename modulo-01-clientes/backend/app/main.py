from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import clientes

app = FastAPI(
    title="Sistema de Gestão de Contratos e Faturamento",
    description="API para controle de clientes, contratos, produtos e faturamento com validação por IA.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # ajustar para produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clientes.router, prefix="/api/v1")


@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "ok", "modulo": "clientes", "versao": "1.0.0"}
