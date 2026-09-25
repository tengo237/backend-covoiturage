# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Alert, Reservation, Trip, User
from schemas import AlertCreate, AlertResponse
from auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# ============================================
# ENVOYER UNE ALERTE SOS
# ============================================

@router.post("", response_model=dict)
async def send_alert(
    request: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Envoyer une alerte SOS"""
    
    try:
        # Vérifier que la réservation existe
        reservation = db.query(Reservation).filter(
            Reservation.id == request.reservation_id
        ).first()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Réservation non trouvée")
        
        # Vérifier que c'est le passager qui envoie l'alerte
        if reservation.passenger_id != current_user.id:
            raise HTTPException(status_code=403, detail="Non autorisé")
        
        # Vérifier que le trajet existe
        trip = db.query(Trip).filter(Trip.id == request.trip_id).first()
        if not trip:
            raise HTTPException(status_code=404, detail="Trajet non trouvé")
        
        # Créer l'alerte
        alert = Alert(
            trip_id=request.trip_id,
            reservation_id=request.reservation_id,
            passenger_id=current_user.id,
            driver_id=trip.driver_id,
            alert_type=request.alert_type,
            message=request.message,
            passenger_latitude=request.passenger_latitude,
            passenger_longitude=request.passenger_longitude,
            status="pending"
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        print(f"🚨 ALERTE SOS! Passager {current_user.name} (ID: {current_user.id})")
        print(f"   Position: {request.passenger_latitude}, {request.passenger_longitude}")
        print(f"   Trajet: {trip.id} | Conducteur: {trip.driver_id}")
        
        return {
            "status": "success",
            "message": "Alerte envoyée aux administrateurs",
            "alert": AlertResponse.model_validate(alert)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 Erreur création alerte: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# GET ALERTS (Admin uniquement)
# ============================================

@router.get("", response_model=dict)
async def get_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les alertes (Admin uniquement)"""
    
    try:
        # Vérifier que c'est un admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Accès administrateur requis")
        
        alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
        
        return {
            "status": "success",
            "alerts": [AlertResponse.model_validate(alert) for alert in alerts]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 Erreur récupérer alertes: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# ACKNOWLEDGE ALERT (Admin - reconnaître alerte)
# ============================================

@router.put("/{alert_id}/acknowledge", response_model=dict)
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reconnaître une alerte (Admin)"""
    
    try:
        # Vérifier que c'est un admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Accès administrateur requis")
        
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alerte non trouvée")
        
        alert.status = "acknowledged"
        alert.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
        
        print(f"✅ Alerte {alert_id} reconnue par admin {current_user.name}")
        
        return {
            "status": "success",
            "message": "Alerte reconnue",
            "alert": AlertResponse.model_validate(alert)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 Erreur acknowledge alerte: {e}")
        raise HTTPException(status_code=400, detail=str(e))