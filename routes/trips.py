# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Trip, User, Vehicle
from schemas import TripCreate, TripResponse
from routes.auth import get_current_user

router = APIRouter(prefix="/api/trips", tags=["trips"])

# ✅ COORDONNÉES PRINCIPALES CAMEROUN (pour géocodage simple)
CAMEROON_COORDS = {
    "yaoundé": {"lat": 3.8667, "lng": 11.5167},
    "douala": {"lat": 4.0511, "lng": 9.7679},
    "bafoussam": {"lat": 5.7679, "lng": 10.4167},
    "kribi": {"lat": 2.9333, "lng": 9.9167},
    "buea": {"lat": 4.1628, "lng": 9.2410},
    "bamenda": {"lat": 5.9631, "lng": 10.1591},
    "garoua": {"lat": 9.3077, "lng": 13.3948},
    "maroua": {"lat": 10.5916, "lng": 14.3055},
}

def get_coordinates(location: str):
    """Retourner les coordonnées pour une ville"""
    location_lower = location.lower().strip()
    if location_lower in CAMEROON_COORDS:
        return CAMEROON_COORDS[location_lower]
    # Par défaut: Yaoundé
    return {"lat": 3.8667, "lng": 11.5167}

# ============================================
# CREATE TRIP
# ============================================

@router.post("", response_model=dict)
async def create_trip(
    trip: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer un trajet"""
    try:
        print(f"\n[TRIPS] 🔵 Création trajet par {current_user.email}")
        
        if 'driver' not in current_user.roles.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous devez être conducteur pour créer un trajet"
            )
        
        if trip.vehicle_id:
            vehicle = db.query(Vehicle).filter(
                Vehicle.id == trip.vehicle_id,
                Vehicle.user_id == current_user.id
            ).first()
            
            if not vehicle:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Véhicule non trouvé"
                )
        
        new_trip = Trip(
            driver_id=current_user.id,
            vehicle_id=trip.vehicle_id,
            departure_location=trip.departure_location,
            arrival_location=trip.arrival_location,
            departure_time=trip.departure_time,
            arrival_time=trip.arrival_time,
            available_seats=trip.available_seats,
            price_per_seat=trip.price_per_seat,
            description=trip.description,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_trip)
        db.commit()
        db.refresh(new_trip)
        
        print(f"[TRIPS] ✅ Trajet créé: ID {new_trip.id}\n")
        
        # ✅ AJOUTER COORDONNÉES
        departure_coords = get_coordinates(trip.departure_location)
        arrival_coords = get_coordinates(trip.arrival_location)
        
        return {
            "status": "success",
            "message": "Trajet créé avec succès",
            "trip": {
                "id": new_trip.id,
                "driver_id": new_trip.driver_id,
                "vehicle_id": new_trip.vehicle_id,
                "departure_location": new_trip.departure_location,
                "departure_latitude": departure_coords["lat"],  # ✅ NOUVEAU
                "departure_longitude": departure_coords["lng"],  # ✅ NOUVEAU
                "arrival_location": new_trip.arrival_location,
                "arrival_latitude": arrival_coords["lat"],  # ✅ NOUVEAU
                "arrival_longitude": arrival_coords["lng"],  # ✅ NOUVEAU
                "departure_time": new_trip.departure_time.isoformat() if new_trip.departure_time else None,
                "arrival_time": new_trip.arrival_time.isoformat() if new_trip.arrival_time else None,
                "available_seats": new_trip.available_seats,
                "price_per_seat": new_trip.price_per_seat,
                "status": new_trip.status,
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRIPS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET AVAILABLE TRIPS
# ============================================

@router.get("/available", response_model=dict)
async def get_available_trips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les trajets disponibles"""
    try:
        print(f"\n[TRIPS] 🔵 GET /available pour {current_user.email}")
        
        trips = db.query(Trip).filter(
            Trip.status.in_(["active", "scheduled"])
        ).all()
        
        print(f"[TRIPS] ✅ {len(trips)} trajets trouvés")
        
        result = []
        for trip in trips:
            driver = db.query(User).filter(User.id == trip.driver_id).first()
            vehicle = None
            vehicle_obj = None
            if trip.vehicle_id:
                vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()
                if vehicle:
                    vehicle_obj = {
                        "id": vehicle.id,
                        "brand": vehicle.brand,
                        "model": vehicle.model,
                        "plate": vehicle.plate,
                        "color": vehicle.color,
                        "photo_url": vehicle.vehicle_photo_url,
                    }
            
            # ✅ AJOUTER COORDONNÉES
            departure_coords = get_coordinates(trip.departure_location)
            arrival_coords = get_coordinates(trip.arrival_location)
            
            trip_obj = {
                "id": trip.id,
                "driver_id": trip.driver_id,
                "vehicle_id": trip.vehicle_id,
                "departure_location": trip.departure_location,
                "departure_latitude": departure_coords["lat"],  # ✅ NOUVEAU
                "departure_longitude": departure_coords["lng"],  # ✅ NOUVEAU
                "arrival_location": trip.arrival_location,
                "arrival_latitude": arrival_coords["lat"],  # ✅ NOUVEAU
                "arrival_longitude": arrival_coords["lng"],  # ✅ NOUVEAU
                "departure_time": trip.departure_time.isoformat() if trip.departure_time else None,
                "arrival_time": trip.arrival_time.isoformat() if trip.arrival_time else None,
                "available_seats": trip.available_seats,
                "price_per_seat": trip.price_per_seat,
                "description": trip.description,
                "status": trip.status,
                "created_at": trip.created_at.isoformat() if trip.created_at else None,
                "updated_at": trip.updated_at.isoformat() if trip.updated_at else None,
                "driver": {
                    "id": driver.id,
                    "name": driver.name,
                    "email": driver.email,
                    "phone": driver.phone,
                    "photo_url": driver.photo_url,
                } if driver else None,
                "vehicle": vehicle_obj
            }
            result.append(trip_obj)
        
        print(f"[TRIPS] Retour de {len(result)} trajets au frontend\n")
        
        return {
            "status": "success",
            "trips": result
        }
    except Exception as e:
        print(f"[TRIPS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET MY TRIPS
# ============================================

@router.get("/my-trips", response_model=dict)
async def get_my_trips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer mes trajets"""
    try:
        print(f"\n[TRIPS] GET /my-trips pour {current_user.email}")
        
        trips = db.query(Trip).filter(
            Trip.driver_id == current_user.id
        ).all()
        
        print(f"[TRIPS] ✅ {len(trips)} trajets trouvés\n")
        
        result = []
        for trip in trips:
            vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first() if trip.vehicle_id else None
            
            # ✅ AJOUTER COORDONNÉES
            departure_coords = get_coordinates(trip.departure_location)
            arrival_coords = get_coordinates(trip.arrival_location)
            
            trip_obj = {
                "id": trip.id,
                "driver_id": trip.driver_id,
                "vehicle_id": trip.vehicle_id,
                "departure_location": trip.departure_location,
                "departure_latitude": departure_coords["lat"],  # ✅ NOUVEAU
                "departure_longitude": departure_coords["lng"],  # ✅ NOUVEAU
                "arrival_location": trip.arrival_location,
                "arrival_latitude": arrival_coords["lat"],  # ✅ NOUVEAU
                "arrival_longitude": arrival_coords["lng"],  # ✅ NOUVEAU
                "departure_time": trip.departure_time.isoformat() if trip.departure_time else None,
                "arrival_time": trip.arrival_time.isoformat() if trip.arrival_time else None,
                "available_seats": trip.available_seats,
                "price_per_seat": trip.price_per_seat,
                "description": trip.description,
                "status": trip.status,
                "created_at": trip.created_at.isoformat() if trip.created_at else None,
                "updated_at": trip.updated_at.isoformat() if trip.updated_at else None,
                "vehicle": {
                    "id": vehicle.id,
                    "brand": vehicle.brand,
                    "model": vehicle.model,
                    "plate": vehicle.plate,
                    "color": vehicle.color,
                    "photo_url": vehicle.vehicle_photo_url,
                } if vehicle else None
            }
            result.append(trip_obj)
        
        return {
            "status": "success",
            "trips": result
        }
    except Exception as e:
        print(f"[TRIPS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET TRIP BY ID
# ============================================

@router.get("/{trip_id}", response_model=dict)
async def get_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer un trajet par ID"""
    try:
        print(f"\n[TRIPS] GET trajet ID {trip_id}")
        
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trajet non trouvé"
            )
        
        driver = db.query(User).filter(User.id == trip.driver_id).first()
        vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first() if trip.vehicle_id else None
        
        # ✅ AJOUTER COORDONNÉES
        departure_coords = get_coordinates(trip.departure_location)
        arrival_coords = get_coordinates(trip.arrival_location)
        
        trip_obj = {
            "id": trip.id,
            "driver_id": trip.driver_id,
            "vehicle_id": trip.vehicle_id,
            "departure_location": trip.departure_location,
            "departure_latitude": departure_coords["lat"],  # ✅ NOUVEAU
            "departure_longitude": departure_coords["lng"],  # ✅ NOUVEAU
            "arrival_location": trip.arrival_location,
            "arrival_latitude": arrival_coords["lat"],  # ✅ NOUVEAU
            "arrival_longitude": arrival_coords["lng"],  # ✅ NOUVEAU
            "departure_time": trip.departure_time.isoformat() if trip.departure_time else None,
            "arrival_time": trip.arrival_time.isoformat() if trip.arrival_time else None,
            "available_seats": trip.available_seats,
            "price_per_seat": trip.price_per_seat,
            "description": trip.description,
            "status": trip.status,
            "created_at": trip.created_at.isoformat() if trip.created_at else None,
            "updated_at": trip.updated_at.isoformat() if trip.updated_at else None,
            "driver": {
                "id": driver.id,
                "name": driver.name,
                "email": driver.email,
                "phone": driver.phone,
                "photo_url": driver.photo_url,
            } if driver else None,
            "vehicle": {
                "id": vehicle.id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "plate": vehicle.plate,
                "color": vehicle.color,
                "photo_url": vehicle.vehicle_photo_url,
            } if vehicle else None
        }
        
        print(f"[TRIPS] ✅ Trajet trouvé\n")
        
        return {
            "status": "success",
            "trip": trip_obj
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRIPS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )
