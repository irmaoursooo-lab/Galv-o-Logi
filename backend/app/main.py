import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .api.routes import router as routes_router
from .api.docks import router as docks_router
from .api.sync import router as sync_router
from .api.trucks import router as trucks_router
from .models.entities import create_destination, list_all_destinations, add_slow_report

def seed_initial_data():
    init_db()
    existing = list_all_destinations()
    if not existing:
        # Doca 1: Doca Crônica (Mercado Central, muitas reclamações em horários distintos)
        d1 = create_destination(
            name="Mercado Central Doca Sul",
            address="Av. das Amoras, 420 - Box 14",
            latitude=-23.5489,
            longitude=-46.6388
        )
        add_slow_report(d1["id"], "motorista-joao", "08:30", 90, "Fila de conferentes travada desde cedo")
        add_slow_report(d1["id"], "motorista-pedro", "15:00", 75, "Falta de empilhadeiras constante")

        # Doca 2: Doca Lenta por Horário (CD Anhanguera, lenta entre 11h e 13h)
        d2 = create_destination(
            name="Centro de Distribuição Anhanguera",
            address="Rodovia Anhanguera, KM 18",
            latitude=-23.4920,
            longitude=-46.7350
        )
        add_slow_report(d2["id"], "motorista-carlos", "11:45", 60, "Pausa de almoço dos conferentes")
        add_slow_report(d2["id"], "motorista-marcos", "12:30", 50, "Troca de turno das 12h")

        # Doca 3: Doca Rápida Normal
        create_destination(
            name="Galpão Logístico Mooca",
            address="Rua dos Trilhos, 1200",
            latitude=-23.5550,
            longitude=-46.6020
        )

        # Doca 4: Hipermercado Tamboré
        create_destination(
            name="Hipermercado Tamboré Docas 1-4",
            address="Alameda Araguaia, 800",
            latitude=-23.5010,
            longitude=-46.8520
        )

# Inicializa schema SQLite imediatamente ao carregar o módulo
init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_initial_data()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Plataforma de Roteirização Colaborativa Inteligente com Sistema Multi-Agente e Arquitetura Offline-First",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas de API
app.include_router(routes_router, prefix="/api/v1")
app.include_router(docks_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
app.include_router(trucks_router, prefix="/api/v1")

# Servir arquivos estáticos do Cockpit Web / PWA
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Galvão Logi API rodando com sucesso. Acesse /docs para explorar o Swagger."}
