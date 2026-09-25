# routes/admin.py - Routes d'administration
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db
from models import User, Trip, Alert, Reservation
from schemas import UserResponse
from datetime import datetime, timedelta
from pydantic import BaseModel

class ToggleUserRequest(BaseModel):
    is_active: bool

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ============================================
# GET /api/admin/stats - Statistiques
# ============================================
@router.get("/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """Retourne les stats du dashboard admin"""
    try:
        print("[ADMIN STATS] Début")
        
        users_count = db.query(func.count(User.id)).scalar()
        trips_count = db.query(func.count(Trip.id)).scalar()
        alerts_count = db.query(func.count(Alert.id)).scalar()
        pending_count = db.query(func.count(Reservation.id)).filter(
            Reservation.status == 'pending'
        ).scalar()
        
        users_yesterday = db.query(func.count(User.id)).filter(
            User.created_at >= datetime.now() - timedelta(days=1)
        ).scalar()
        
        trips_yesterday = db.query(func.count(Trip.id)).filter(
            Trip.created_at >= datetime.now() - timedelta(days=1)
        ).scalar()
        
        print(f"[ADMIN STATS] ✅ Users={users_count}, Trips={trips_count}, Alerts={alerts_count}")
        
        return {
            "status": "success",
            "data": {
                "users": {"count": users_count, "change": f"+{users_yesterday}"},
                "trips": {"count": trips_count, "change": f"+{trips_yesterday}"},
                "alerts": {"count": alerts_count, "change": "+0"},
                "pending": {"count": pending_count, "change": "+0"},
            }
        }
    except Exception as e:
        print(f"[ADMIN STATS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# GET /api/admin/activities - Activités récentes
# ============================================
@router.get("/activities")
async def get_admin_activities(db: Session = Depends(get_db)):
    """Retourne les activités récentes"""
    try:
        print("[ADMIN ACTIVITIES] Début")
        activities = []
        
        new_users = db.query(User).filter(
            User.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        for user in new_users[:3]:
            activities.append({
                "id": user.id,
                "title": f"Nouvel utilisateur: {user.name}",
                "time": "Il y a quelques heures",
                "icon": "person-add-outline",
            })
        
        new_trips = db.query(Trip).filter(
            Trip.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        for trip in new_trips[:2]:
            activities.append({
                "id": trip.id,
                "title": "Nouveau trajet créé",
                "time": "Il y a quelques heures",
                "icon": "add-circle-outline",
            })
        
        recent_alerts = db.query(Alert).filter(
            Alert.created_at >= datetime.now() - timedelta(hours=24)
        ).limit(1).all()
        
        for alert in recent_alerts:
            activities.append({
                "id": alert.id,
                "title": "Signalement reçu",
                "time": "Il y a quelques heures",
                "icon": "alert-circle-outline",
            })
        
        print(f"[ADMIN ACTIVITIES] ✅ {len(activities)} activités")
        return {"status": "success", "data": activities}
    except Exception as e:
        print(f"[ADMIN ACTIVITIES] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# GET /api/admin/signalements - Tous les signalements
# ============================================
@router.get("/signalements")
async def get_signalements(status: str = None, db: Session = Depends(get_db)):
    """Retourne les signalements/alertes"""
    try:
        print(f"[ADMIN SIGNALEMENTS] Récupération avec status={status}...")
        
        query = db.query(Alert)
        
        if status:
            query = query.filter(Alert.status == status)
        
        alerts = query.order_by(Alert.created_at.desc()).all()
        
        print(f"[ADMIN SIGNALEMENTS] {len(alerts)} alertes trouvées")
        
        result = []
        for alert in alerts:
            trip = db.query(Trip).filter(Trip.id == alert.trip_id).first()
            driver = db.query(User).filter(User.id == alert.driver_id).first()
            
            result.append({
                "id": alert.id,
                "trip_id": alert.trip_id,
                "reservation_id": alert.reservation_id,
                "driver_id": alert.driver_id,
                "passenger_id": alert.passenger_id,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "status": alert.status,
                "latitude": alert.passenger_latitude,
                "longitude": alert.passenger_longitude,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "trip": {
                    "departure_location": trip.departure_location if trip else None,
                    "arrival_location": trip.arrival_location if trip else None,
                    "departure_time": trip.departure_time.isoformat() if trip and trip.departure_time else None,
                } if trip else None,
                "driver": {
                    "id": driver.id,
                    "name": driver.name,
                    "email": driver.email,
                    "photo_url": driver.photo_url,
                } if driver else None,
            })
        
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"[ADMIN SIGNALEMENTS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PATCH /api/admin/signalements/{id}/status
# ============================================
@router.patch("/signalements/{alert_id}/status")
async def update_signalement_status(alert_id: int, new_status: str, db: Session = Depends(get_db)):
    """Met à jour le statut d'un signalement"""
    try:
        print(f"[ADMIN SIGNALEMENTS] Mise à jour {alert_id} → {new_status}...")
        
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Signalement introuvable")
        
        valid_statuses = ['open', 'investigating', 'resolved', 'closed']
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Statut invalide")
        
        alert.status = new_status
        alert.updated_at = datetime.utcnow()
        db.commit()
        
        print(f"[ADMIN SIGNALEMENTS] ✅ Signalement {alert_id} → {new_status}")
        
        return {
            "status": "success",
            "message": f"Signalement mis à jour",
            "data": {"id": alert.id, "status": alert.status}
        }
    except Exception as e:
        db.rollback()
        print(f"[ADMIN SIGNALEMENTS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# GET /api/admin/users - Tous les utilisateurs
# ============================================
@router.get("/users")
async def get_users(db: Session = Depends(get_db)):
    """Retourne tous les utilisateurs"""
    try:
        print("[ADMIN USERS] Récupération utilisateurs...")
        
        users = db.query(User).all()
        
        print(f"[ADMIN USERS] {len(users)} utilisateurs trouvés")
        
        result = []
        for user in users:
            result.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "photo_url": user.photo_url,
                "roles": user.roles,
                "current_role": user.current_role,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            })
        
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"[ADMIN USERS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PATCH /api/admin/users/{id}/active
# ============================================
@router.patch("/users/{user_id}/active")
async def toggle_user_active(user_id: int, request: ToggleUserRequest, db: Session = Depends(get_db)):
    """Active/Désactive un utilisateur"""
    try:
        is_active = request.is_active
        print(f"[ADMIN USERS] Toggle {user_id} → {is_active}")
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        
        user.is_active = is_active
        db.commit()
        
        print(f"[ADMIN USERS] ✅ Utilisateur {user_id} updated")
        
        return {
            "status": "success",
            "message": f"Utilisateur {'activé' if is_active else 'désactivé'}",
            "data": {"id": user.id, "is_active": user.is_active}
        }
    except Exception as e:
        db.rollback()
        print(f"[ADMIN USERS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# GET /api/admin/driver-requests
# ============================================
@router.get("/driver-requests")
async def get_driver_requests(db: Session = Depends(get_db)):
    """Retourne les demandes d'inscription conducteur en attente"""
    try:
        print("[ADMIN DRIVERS] Récupération demandes en attente...")
        
        pending_drivers = db.query(User).filter(
            User.roles.like('%driver%'),
            User.is_active == False
        ).all()
        
        print(f"[ADMIN DRIVERS] {len(pending_drivers)} demandes trouvées")
        
        result = []
        for driver in pending_drivers:
            result.append({
                "id": driver.id,
                "name": driver.name,
                "email": driver.email,
                "phone": driver.phone,
                "photo_url": driver.photo_url,
                "roles": driver.roles,
                "current_role": driver.current_role,
                "created_at": driver.created_at.isoformat() if driver.created_at else None,
                "is_active": driver.is_active,
            })
        
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"[ADMIN DRIVERS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PATCH /api/admin/drivers/{id}/approve
# ============================================
@router.patch("/drivers/{driver_id}/approve")
async def approve_driver(driver_id: int, db: Session = Depends(get_db)):
    """Approuve une demande d'inscription conducteur"""
    try:
        print(f"[ADMIN DRIVERS] Approbation {driver_id}...")
        
        driver = db.query(User).filter(User.id == driver_id).first()
        
        if not driver:
            raise HTTPException(status_code=404, detail="Conducteur introuvable")
        
        if "driver" not in (driver.roles or ""):
            raise HTTPException(status_code=400, detail="Non conducteur")
        
        driver.is_active = True
        db.commit()
        
        print(f"[ADMIN DRIVERS] ✅ Conducteur {driver_id} approuvé")
        
        return {
            "status": "success",
            "message": "Conducteur approuvé",
            "data": {"id": driver.id, "name": driver.name, "is_active": driver.is_active}
        }
    except Exception as e:
        db.rollback()
        print(f"[ADMIN DRIVERS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PATCH /api/admin/drivers/{id}/reject
# ============================================
@router.patch("/drivers/{driver_id}/reject")
async def reject_driver(driver_id: int, reason: str = "", db: Session = Depends(get_db)):
    """Refuse une demande d'inscription conducteur"""
    try:
        print(f"[ADMIN DRIVERS] Refus {driver_id}...")
        
        driver = db.query(User).filter(User.id == driver_id).first()
        
        if not driver:
            raise HTTPException(status_code=404, detail="Conducteur introuvable")
        
        if "driver" not in (driver.roles or ""):
            raise HTTPException(status_code=400, detail="Non conducteur")
        
        driver.is_active = False
        driver.roles = driver.roles.replace("driver,", "").replace(",driver", "").replace("driver", "")
        db.commit()
        
        print(f"[ADMIN DRIVERS] ✅ Conducteur {driver_id} refusé")
        
        return {
            "status": "success",
            "message": "Demande refusée",
            "data": {"id": driver.id, "name": driver.name, "is_active": driver.is_active}
        }
    except Exception as e:
        db.rollback()
        print(f"[ADMIN DRIVERS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# GET /api/admin/driver-applications - Dossiers en attente
# ============================================
@router.get("/driver-applications")
async def get_driver_applications(db: Session = Depends(get_db)):
    """Retourne les réservations en attente"""
    try:
        print("[ADMIN APPS] Récupération dossiers...")
        
        applications = db.query(Reservation).filter(
            Reservation.status == 'pending'
        ).all()
        
        print(f"[ADMIN APPS] {len(applications)} dossiers trouvés")
        
        result = []
        for app in applications:
            result.append({
                "id": app.id,
                "passenger_id": app.passenger_id,
                "trip_id": app.trip_id,
                "seats_booked": app.seats_booked,
                "total_price": app.total_price,
                "status": app.status,
                "created_at": app.created_at.isoformat() if app.created_at else None,
            })
        
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"[ADMIN APPS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PATCH /api/admin/applications/{id}/status
# ============================================
@router.patch("/applications/{app_id}/status")
async def update_application_status(app_id: int, new_status: str, db: Session = Depends(get_db)):
    """Met à jour le statut d'une réservation"""
    try:
        print(f"[ADMIN APPS] Mise à jour {app_id} → {new_status}")
        
        if new_status not in ["approved", "rejected", "pending"]:
            raise HTTPException(status_code=400, detail="Statut invalide")
        
        reservation = db.query(Reservation).filter(Reservation.id == app_id).first()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Dossier introuvable")
        
        reservation.status = new_status
        db.commit()
        
        print(f"[ADMIN APPS] ✅ Dossier {app_id} updated")
        
        return {
            "status": "success",
            "message": f"Dossier {new_status}",
            "data": {"id": reservation.id, "status": reservation.status}
        }
    except Exception as e:
        db.rollback()
        print(f"[ADMIN APPS] ❌ ERREUR: {e}")
        raise HTTPException(status_code=500, detail=str(e))