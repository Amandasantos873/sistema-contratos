"""
Sistema de Gestão de Contratos e Faturamento
Ponto de entrada principal da API — FastAPI

Módulos registrados:
  01 — Clientes
  02 — Contratos + Go-live por item
  03 — Produtos e Serviços
  04 — Reajustes e Aditivos
  05 — Faturamento
  06 — Validação por IA
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.config import settings

# Routers de cada módulo
from app.routers.auth        import router as router_auth
from app.routers.clientes    import router as router_clientes
from app.routers.contratos   import router as router_contratos
from app.routers.goLive_item import router as router_golive
from app.routers.produtos    import router as router_produtos
from app.routers.reajustes   import router as router_reajustes
from app.routers.faturamento import router as router_faturamento
from app.routers.validacao   import router as router_validacao

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Instância principal
# ------------------------------------------------------------------
app = FastAPI(
    title       = "Sistema de Gestão de Contratos e Faturamento",
    description = """
API REST para controle de clientes, contratos, produtos, reajustes,
faturamento e validação automática por IA.

## Módulos
- **Clientes** — cadastro, endereços e contatos
- **Contratos** — ASP, BSP e BPO com controle de go-live por item
- **Produtos** — catálogo, pacotes mínimos e movimentações
- **Reajustes** — INPC, IPCA, IGPM e dissídio com fluxo de aprovação
- **Faturamento** — apuração em lote, volumetria e integração K2
- **Validação IA** — 12 regras determinísticas + Claude API
    """,
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)


# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------
origens_permitidas = [
    "http://localhost:3000",    # Next.js dev
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]
if settings.ENVIRONMENT == "production":
    # Em produção, adicionar o domínio real
    origens_permitidas += settings.ALLOWED_ORIGINS.split(",") if hasattr(settings, "ALLOWED_ORIGINS") else []

app.add_middleware(
    CORSMiddleware,
    allow_origins     = origens_permitidas,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ------------------------------------------------------------------
# Middleware: log de requisições + tempo de resposta
# ------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    response.headers["X-Response-Time"] = f"{duration}ms"
    return response


# ------------------------------------------------------------------
# Tratamento global de erros
# ------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente."}
    )


# ------------------------------------------------------------------
# Registro dos routers
# Prefixo padrão: /api/v1
# ------------------------------------------------------------------
PREFIX = "/api/v1"

app.include_router(router_auth,        prefix=PREFIX)
app.include_router(router_clientes,    prefix=PREFIX)
app.include_router(router_contratos,   prefix=PREFIX)
app.include_router(router_golive,      prefix=PREFIX)
app.include_router(router_produtos,    prefix=PREFIX)
app.include_router(router_reajustes,   prefix=PREFIX)
app.include_router(router_faturamento, prefix=PREFIX)
app.include_router(router_validacao,   prefix=PREFIX)


# ------------------------------------------------------------------
# Endpoints de sistema
# ------------------------------------------------------------------

@app.get("/", tags=["Sistema"], summary="Redireciona para a documentação")
async def root():
    return {
        "sistema": "Gestão de Contratos e Faturamento",
        "versao":  "1.0.0",
        "docs":    "/docs",
        "status":  "online",
    }


@app.get("/health", tags=["Sistema"], summary="Health check — verifica se a API está no ar")
async def health():
    return {
        "status":      "ok",
        "environment": settings.ENVIRONMENT,
        "versao":      "1.0.0",
    }


@app.get("/api/v1/info", tags=["Sistema"], summary="Lista todos os endpoints registrados")
async def info():
    rotas = [
        {"path": route.path, "methods": list(route.methods), "name": route.name}
        for route in app.routes
        if hasattr(route, "methods")
    ]
    return {"total_endpoints": len(rotas), "endpoints": rotas}
