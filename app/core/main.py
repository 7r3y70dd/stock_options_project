import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.dashboard import router as dashboard_router
from app.core.config import settings
from app.core.database import init_db

# Initialize database
init_db()

# Setup templates and static files
template_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates')
static_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static')

templates = Jinja2Templates(directory=template_dir)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown

app = FastAPI(title="Options Tracker", lifespan=lifespan)

# Mount static files
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(dashboard_router, prefix="/api/api", tags=["dashboard"])

# HTML Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/opportunities", response_class=HTMLResponse)
async def opportunities(request: Request):
    return templates.TemplateResponse("opportunities.html", {"request": request})

@app.get("/opportunities/{signal_id}", response_class=HTMLResponse)
async def opportunity_detail(request: Request, signal_id: int):
    return templates.TemplateResponse("opportunity_detail.html", {"request": request, "signal_id": signal_id})

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    return templates.TemplateResponse("portfolio.html", {"request": request})

@app.get("/trades", response_class=HTMLResponse)
async def trades(request: Request):
    return templates.TemplateResponse("trades.html", {"request": request})

@app.get("/watchlist", response_class=HTMLResponse)
async def watchlist(request: Request):
    return templates.TemplateResponse("watchlist.html", {"request": request})

@app.get("/risk-settings", response_class=HTMLResponse)
async def risk_settings(request: Request):
    return templates.TemplateResponse("risk_settings.html", {"request": request})

@app.get("/news", response_class=HTMLResponse)
async def news(request: Request):
    return templates.TemplateResponse("news.html", {"request": request})

@app.get("/status", response_class=HTMLResponse)
async def status(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
