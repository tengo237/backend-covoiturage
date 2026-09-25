# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Tracking, Trip, User
from schemas import TripTrackingCreate, TripTrackingResponse
from routes.auth import get_current_user

router = APIRouter(prefix="/api/tracking", tags=["tracking"])

# ============================================
# CREATE TRACKING
# ============================================

@router.post("", response_model=TripTrackingResponse)
async def create_tracking(
    tracking: TripTrackingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enregistrer la position du conducteur"""
    try:
        print(f"🔵 Tracking créé pour le trajet {tracking.trip_id}")
        
        # Vérifier que c'est le conducteur du trajet
        trip = db.query(Trip).filter(Trip.id == tracking.trip_id).first()
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trajet non trouvé"
            )
        
        if trip.driver_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas le conducteur de ce trajet"
            )
        
        # Créer le tracking
        db_tracking = Tracking(
            trip_id=tracking.trip_id,
            driver_id=current_user.id,
            latitude=tracking.driver_latitude,
            longitude=tracking.driver_longitude,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_tracking)
        db.commit()
        db.refresh(db_tracking)
        
        print(f"🟢 Tracking enregistré: ({tracking.driver_latitude}, {tracking.driver_longitude})")
        
        return db_tracking
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 Erreur create tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement du tracking"
        )

# ============================================
# GET TRIP TRACKING
# ============================================

@router.get("/trip/{trip_id}", response_model=list[TripTrackingResponse])
async def get_trip_tracking(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer le tracking d'un trajet"""
    try:
        print(f"🔵 Récupération tracking du trajet {trip_id}")
        
        # Vérifier que le trajet existe
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trajet non trouvé"
            )
        
        # Récupérer le tracking
        trackings = db.query(Tracking).filter(
            Tracking.trip_id == trip_id
        ).order_by(Tracking.created_at.desc()).all()
        
        print(f"🟢 {len(trackings)} enregistrements de tracking trouvés")
        
        return trackings
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 Erreur get trip tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du tracking"
        )

# ============================================
# GET LATEST TRACKING
# ============================================

@router.get("/trip/{trip_id}/latest", response_model=dict)
async def get_latest_tracking(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer la dernière position du conducteur"""
    try:
        print(f"🔵 Récupération dernière position du trajet {trip_id}")
        
        # Vérifier que le trajet existe
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trajet non trouvé"
            )
        
        # Récupérer le dernier tracking
        tracking = db.query(Tracking).filter(
            Tracking.trip_id == trip_id
        ).order_by(Tracking.created_at.desc()).first()
        
        if not tracking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pas de tracking disponible"
            )
        
        print(f"🟢 Dernière position: ({tracking.latitude}, {tracking.longitude})")
        
        return {
            "id": tracking.id,
            "trip_id": tracking.trip_id,
            "driver_id": tracking.driver_id,
            "latitude": tracking.latitude,
            "longitude": tracking.longitude,
            "speed": tracking.speed,
            "created_at": tracking.created_at,
            "updated_at": tracking.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 Erreur get latest tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du tracking"
        )
