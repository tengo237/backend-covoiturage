# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Trip, User, Vehicle
from schemas import TripCreate, TripResponse
from routes.auth import get_current_user
import json

router = APIRouter(prefix="/api/trips", tags=["trips"])

# ============================================
# CREATE TRIP - VERSION DEBUG
# ============================================

@router.post("", response_model=dict)
async def create_trip(
    trip: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer un trajet"""
    try:
        print("\n" + "="*60)
        print("[TRIPS] 🔵 CRÉATION TRAJET - DEBUG COMPLET")
        print("="*60)
        
        # 1️⃣ LOG UTILISATEUR
        print(f"[TRIPS] 👤 Utilisateur: {current_user.id} - {current_user.email}")
        print(f"[TRIPS] 👤 Roles: {current_user.roles}")
        
        # 2️⃣ LOG DONNÉES REÇUES
        print(f"\n[TRIPS] 📋 DONNÉES REÇUES:")
        print(f"[TRIPS]   - vehicle_id: {trip.vehicle_id} (type: {type(trip.vehicle_id)})")
        print(f"[TRIPS]   - departure_location: {trip.departure_location}")
        print(f"[TRIPS]   - arrival_location: {trip.arrival_location}")
        print(f"[TRIPS]   - departure_time: {trip.departure_time} (type: {type(trip.departure_time)})")
        print(f"[TRIPS]   - arrival_time: {trip.arrival_time} (type: {type(trip.arrival_time)})")
        print(f"[TRIPS]   - available_seats: {trip.available_seats} (type: {type(trip.available_seats)})")
        print(f"[TRIPS]   - price_per_seat: {trip.price_per_seat} (type: {type(trip.price_per_seat)})")
        print(f"[TRIPS]   - description: {trip.description}")
        
        # 3️⃣ VÉRIFICATION CONDUCTEUR
        print(f"\n[TRIPS] 🔐 Vérification rôle...")
        if 'driver' not in current_user.roles.lower():
            print(f"[TRIPS] ❌ ERREUR: Utilisateur n'est pas conducteur!")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous devez être conducteur pour créer un trajet"
            )
        print(f"[TRIPS] ✅ Utilisateur est conducteur")
        
        # 4️⃣ VÉRIFICATION VÉHICULE
        print(f"\n[TRIPS] 🚗 Vérification véhicule...")
        if trip.vehicle_id:
            vehicle = db.query(Vehicle).filter(
                Vehicle.id == trip.vehicle_id,
                Vehicle.user_id == current_user.id
            ).first()
            
            if not vehicle:
                print(f"[TRIPS] ❌ ERREUR: Véhicule {trip.vehicle_id} non trouvé ou n'appartient pas à l'utilisateur!")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Véhicule non trouvé"
                )
            print(f"[TRIPS] ✅ Véhicule trouvé: {vehicle.brand} {vehicle.model}")
        else:
            print(f"[TRIPS] ⚠️  Pas de véhicule spécifié")
        
        # 5️⃣ VALIDATION DATETIME
        print(f"\n[TRIPS] ⏰ Vérification datetime...")
        if not isinstance(trip.departure_time, datetime):
            print(f"[TRIPS] ❌ ERREUR: departure_time n'est pas un datetime valide!")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="departure_time doit être un datetime valide"
            )
        print(f"[TRIPS] ✅ departure_time valide: {trip.departure_time.isoformat()}")
        
        # 6️⃣ CRÉER LE TRAJET
        print(f"\n[TRIPS] 📝 Création du trajet en base...")
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
        
        print(f"[TRIPS]   - Objet Trip créé (avant commit)")
        
        # 7️⃣ COMMIT EN BASE
        print(f"[TRIPS] 💾 Commit en base de données...")
        db.add(new_trip)
        db.commit()
        db.refresh(new_trip)
        
        print(f"[TRIPS] ✅ SUCCÈS! Trajet créé avec ID: {new_trip.id}")
        
        # 8️⃣ VÉRIFICATION EN BASE
        print(f"\n[TRIPS] 🔍 Vérification en base de données...")
        trip_check = db.query(Trip).filter(Trip.id == new_trip.id).first()
        if trip_check:
            print(f"[TRIPS] ✅ Trajet {trip_check.id} confirmé en base!")
        else:
            print(f"[TRIPS] ❌ ERREUR: Trajet pas trouvé après insertion!")
        
        print("="*60 + "\n")
        
        return {
            "status": "success",
            "message": "Trajet créé avec succès",
            "trip": {
                "id": new_trip.id,
                "driver_id": new_trip.driver_id,
                "vehicle_id": new_trip.vehicle_id,
                "departure_location": new_trip.departure_location,
                "arrival_location": new_trip.arrival_location,
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
        print(f"[TRIPS] ❌ EXCEPTION: {type(e).__name__}: {str(e)}")
        print("="*60 + "\n")
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
        print(f"\n[TRIPS] GET /available pour {current_user.email}")
        
        trips = db.query(Trip).filter(
            Trip.status.in_(["active", "scheduled"])
        ).all()
        
        print(f"[TRIPS] ✓ {len(trips)} trajets trouvés en BD")
        
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
            
            trip_obj = {
                "id": trip.id,
                "driver_id": trip.driver_id,
                "vehicle_id": trip.vehicle_id,
                "departure_location": trip.departure_location,
                "arrival_location": trip.arrival_location,
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
        
        print(f"[TRIPS] ✓ Envoi de {len(result)} trajets au frontend\n")
        
        return {
            "status": "success",
            "trips": result
        }
    except Exception as e:
        print(f"[TRIPS] ✗ ERREUR: {e}\n")
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
        print(f"[TRIPS] GET /my-trips pour {current_user.email}")
        
        trips = db.query(Trip).filter(
            Trip.driver_id == current_user.id
        ).all()
        
        print(f"[TRIPS] {len(trips)} trajets trouvés pour driver_id={current_user.id}")
        
        result = []
        for trip in trips:
            vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first() if trip.vehicle_id else None
            
            trip_obj = {
                "id": trip.id,
                "driver_id": trip.driver_id,
                "vehicle_id": trip.vehicle_id,
                "departure_location": trip.departure_location,
                "arrival_location": trip.arrival_location,
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
        print(f"[TRIPS] ERREUR: {e}")
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
    """Récupérer un trajet"""
    try:
        print(f"[TRIPS] GET trajet {trip_id}")
        
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trajet non trouvé"
            )
        
        driver = db.query(User).filter(User.id == trip.driver_id).first()
        vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first() if trip.vehicle_id else None
        
        trip_obj = {
            "id": trip.id,
            "driver_id": trip.driver_id,
            "vehicle_id": trip.vehicle_id,
            "departure_location": trip.departure_location,
            "arrival_location": trip.arrival_location,
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
        
        return {
            "status": "success",
            "trip": trip_obj
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRIPS] ERREUR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )
