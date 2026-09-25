from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from config import APP_NAME, APP_VERSION, DEBUG, CORS_ORIGINS
from database import engine, Base
from routes.auth import router as auth_router
from routes.vehicles import router as vehicles_router
from routes.trips import router as trips_router
from routes.reservations import router as reservations_router
from routes.tracking import router as tracking_router
from routes.alerts import router as alerts_router
from routes.messages import router as messages_router
from routes.reviews import router as reviews_router
from routes.admin import router as admin_router  # ✅ NOUVEAU - Dashboard admin
# from routes.eye_detection import router as eye_detection_router  # ✅ DÉSACTIVÉ - Problème mediapipe
import os

# ============================================
# CREATE TABLES
# ============================================

Base.metadata.create_all(bind=engine)

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="API pour l'application RIDE+ (Covoiturage)",
    debug=DEBUG,
)

# ============================================
# CREATE UPLOADS DIRECTORY
# ============================================

os.makedirs("uploads/vehicles", exist_ok=True)
os.makedirs("uploads/profiles", exist_ok=True)

# ============================================
# SERVE STATIC FILES (PHOTOS)
# ============================================

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ============================================
# CORS MIDDLEWARE
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ROUTES
# ============================================

app.include_router(auth_router)
app.include_router(vehicles_router)
app.include_router(trips_router)
app.include_router(reservations_router)
app.include_router(tracking_router)
app.include_router(alerts_router)
app.include_router(messages_router)
app.include_router(reviews_router)
app.include_router(admin_router)  # ✅ NOUVEAU - Dashboard admin
# app.include_router(eye_detection_router)  # ✅ DÉSACTIVÉ - Problème mediapipe

# ============================================
# ROOT ENDPOINT
# ============================================

@app.get("/")
async def root():
    """Racine de l'API"""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }

@app.get("/health")
async def health_check():
    """Vérifier la santé de l'API"""
    return {
        "status": "healthy",
        "version": APP_VERSION,
    }

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Gérer les exceptions génériques"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc) if DEBUG else "Une erreur est survenue",
        }
    )

# ============================================
# STARTUP/SHUTDOWN
# ============================================

@app.on_event("startup")
async def startup():
    """Au démarrage"""
    print(f"🚀 {APP_NAME} v{APP_VERSION} démarré!")
    print(f"📚 Docs disponibles à http://localhost:8000/docs")
    print(f"📁 Dossier uploads créé: uploads/vehicles")
    print(f"📁 Dossier uploads créé: uploads/profiles")
    print(f"🗺️ Tracking module chargé")
    print(f"🚨 Alerts module chargé")
    print(f"💬 Messages module chargé")
    print(f"⭐ Reviews module chargé")
    print(f"📊 Admin Dashboard module chargé")  # ✅ NOUVEAU
    # print(f"👁️ Eye Detection module chargé")  # ✅ DÉSACTIVÉ - Problème mediapipe

@app.on_event("shutdown")
async def shutdown():
    """À l'arrêt"""
    print(f"🛑 {APP_NAME} arrêté!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
    )
