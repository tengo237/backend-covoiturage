"""
RIDE+ Backend - Driver Routes
Gestion des trajets et réservations du conducteur
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from database import get_db
from models import User, Trip, Reservation, Vehicle, TripTracking
from schemas import (
    TripResponse, 
    ReservationResponse, 
    DriverStatsResponse,
    MessageResponse
)
from auth import get_current_user

router = APIRouter(prefix="/api/driver", tags=["driver"])


# ============================================
# MES TRAJETS - GET /api/driver/my-trips
# ============================================

@router.get("/my-trips", response_model=List[TripResponse])
async def get_my_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère tous les trajets publiés par le conducteur actuel
    Statuts: PLANNED, IN_PROGRESS, COMPLETED, CANCELLED
    """
    trips = db.query(Trip).filter(
        Trip.driver_id == current_user.id
    ).order_by(Trip.departure_time.desc()).all()
    
    return trips


# ============================================
# DÉTAILS TRAJET + RÉSERVATIONS
# GET /api/driver/my-trips/{trip_id}/reservations
# ============================================

@router.get("/my-trips/{trip_id}/reservations", response_model=dict)
async def get_trip_reservations(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère toutes les réservations d'un trajet spécifique
    Vérification: le trajet appartient au conducteur
    """
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.driver_id == current_user.id
    ).first()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trajet non trouvé ou non autorisé"
        )
    
    # Récupérer les réservations du trajet
    reservations = db.query(Reservation).filter(
        Reservation.trip_id == trip_id
    ).all()
    
    # Formater les résultats avec infos passagers
    reservations_data = []
    for res in reservations:
        passenger = db.query(User).filter(User.id == res.passenger_id).first()
        reservations_data.append({
            "id": res.id,
            "reservation_id": res.id,
            "passenger_id": res.passenger_id,
            "passenger_name": passenger.full_name if passenger else "Unknown",
            "passenger_photo": passenger.profile_photo_url if passenger else None,
            "seats_booked": res.seats_booked,
            "total_price": res.total_price,
            "status": res.status,  # PENDING, CONFIRMED, PAID, IN_PROGRESS, COMPLETED, CANCELLED
            "created_at": res.created_at,
            "updated_at": res.updated_at
        })
    
    return {
        "trip": trip,
        "trip_id": trip.id,
        "departure_location": trip.departure_location,
        "arrival_location": trip.arrival_location,
        "departure_time": trip.departure_time,
        "total_seats": trip.total_seats,
        "available_seats": trip.available_seats,
        "price_per_seat": trip.price_per_seat,
        "reservations": reservations_data,
        "total_reservations": len(reservations_data)
    }


# ============================================
# ACCEPTER RÉSERVATION
# PUT /api/driver/reservations/{reservation_id}/accept
# ============================================

@router.put("/reservations/{reservation_id}/accept", response_model=dict)
async def accept_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accepte une réservation en attente
    Change le statut: PENDING → CONFIRMED
    """
    # Récupérer la réservation
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id
    ).first()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Réservation non trouvée"
        )
    
    # Vérifier que le trajet appartient au conducteur
    trip = db.query(Trip).filter(
        Trip.id == reservation.trip_id,
        Trip.driver_id == current_user.id
    ).first()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vous n'êtes pas autorisé à gérer cette réservation"
        )
    
    # Vérifier le statut actuel
    if reservation.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Réservation déjà {reservation.status}"
        )
    
    # Mettre à jour le statut
    reservation.status = "CONFIRMED"
    reservation.updated_at = datetime.utcnow()
    
    # Réduire les places disponibles
    trip.available_seats -= reservation.seats_booked
    
    db.commit()
    db.refresh(reservation)
    
    return {
        "success": True,
        "message": f"Réservation #{reservation_id} confirmée",
        "reservation_id": reservation.id,
        "status": reservation.status,
        "updated_at": reservation.updated_at
    }


# ============================================
# REJETER RÉSERVATION
# PUT /api/driver/reservations/{reservation_id}/reject
# ============================================

@router.put("/reservations/{reservation_id}/reject", response_model=dict)
async def reject_reservation(
    reservation_id: int,
    reason: str = "Conducteur a rejeté la réservation",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rejette une réservation
    Change le statut: PENDING → CANCELLED
    """
    # Récupérer la réservation
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id
    ).first()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Réservation non trouvée"
        )
    
    # Vérifier que le trajet appartient au conducteur
    trip = db.query(Trip).filter(
        Trip.id == reservation.trip_id,
        Trip.driver_id == current_user.id
    ).first()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vous n'êtes pas autorisé à gérer cette réservation"
        )
    
    # Vérifier le statut actuel
    if reservation.status not in ["PENDING", "CONFIRMED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de rejeter une réservation {reservation.status}"
        )
    
    # Mettre à jour le statut
    reservation.status = "CANCELLED"
    reservation.updated_at = datetime.utcnow()
    
    # Libérer les places
    trip.available_seats += reservation.seats_booked
    
    db.commit()
    db.refresh(reservation)
    
    return {
        "success": True,
        "message": f"Réservation #{reservation_id} rejetée",
        "reservation_id": reservation.id,
        "status": reservation.status,
        "reason": reason,
        "updated_at": reservation.updated_at
    }


# ============================================
# STATISTIQUES CONDUCTEUR
# GET /api/driver/statistics
# ============================================

@router.get("/statistics", response_model=dict)
async def get_driver_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les statistiques du conducteur
    """
    # Nombre de trajets
    total_trips = db.query(Trip).filter(
        Trip.driver_id == current_user.id
    ).count()
    
    completed_trips = db.query(Trip).filter(
        Trip.driver_id == current_user.id,
        Trip.status == "COMPLETED"
    ).count()
    
    active_trips = db.query(Trip).filter(
        Trip.driver_id == current_user.id,
        Trip.status.in_(["PLANNED", "IN_PROGRESS"])
    ).count()
    
    # Réservations
    total_reservations = db.query(Reservation).join(
        Trip, Reservation.trip_id == Trip.id
    ).filter(
        Trip.driver_id == current_user.id
    ).count()
    
    confirmed_reservations = db.query(Reservation).join(
        Trip, Reservation.trip_id == Trip.id
    ).filter(
        Trip.driver_id == current_user.id,
        Reservation.status == "CONFIRMED"
    ).count()
    
    # Revenus (à implémenter avec payments)
    total_revenue = db.query(Reservation).join(
        Trip, Reservation.trip_id == Trip.id
    ).filter(
        Trip.driver_id == current_user.id,
        Reservation.status.in_(["CONFIRMED", "PAID", "COMPLETED"])
    ).with_entities(
        db.func.sum(Reservation.total_price)
    ).scalar() or 0
    
    # Évaluations (à implémenter avec reviews)
    driver_user = db.query(User).filter(User.id == current_user.id).first()
    avg_rating = driver_user.average_rating if driver_user else 0
    
    return {
        "trips": {
            "total": total_trips,
            "completed": completed_trips,
            "active": active_trips
        },
        "reservations": {
            "total": total_reservations,
            "confirmed": confirmed_reservations
        },
        "revenue": {
            "total": total_revenue,
            "currency": "XAF"  # Francs CFA
        },
        "rating": {
            "average": avg_rating,
            "count": 0  # À implémenter
        }
    }


# ============================================
# ANNULER TRAJET
# PUT /api/driver/my-trips/{trip_id}/cancel
# ============================================

@router.put("/my-trips/{trip_id}/cancel", response_model=dict)
async def cancel_trip(
    trip_id: int,
    reason: str = "Annulation par le conducteur",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Annule un trajet
    Seuls les trajets PLANNED peuvent être annulés
    """
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.driver_id == current_user.id
    ).first()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trajet non trouvé"
        )
    
    if trip.status != "PLANNED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible d'annuler un trajet {trip.status}"
        )
    
    # Annuler le trajet
    trip.status = "CANCELLED"
    trip.updated_at = datetime.utcnow()
    
    # Annuler toutes les réservations
    reservations = db.query(Reservation).filter(
        Reservation.trip_id == trip_id
    ).all()
    
    for res in reservations:
        if res.status not in ["CANCELLED", "COMPLETED"]:
            res.status = "CANCELLED"
            res.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(trip)
    
    return {
        "success": True,
        "message": f"Trajet #{trip_id} annulé",
        "trip_id": trip.id,
        "status": trip.status,
        "reason": reason,
        "cancelled_reservations": len(reservations)
    }
