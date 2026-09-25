# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Reservation, Trip, User, Vehicle, Conversation
from routes.auth import get_current_user

router = APIRouter(prefix="/api/reservations", tags=["reservations"])

# ============================================
# CREATE RESERVATION
# ============================================

@router.post("", response_model=dict)
async def create_reservation(
    trip_id: int,
    seats_booked: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer une réservation"""
    try:
        print(f"\n[RESERVATIONS] Création réservation par {current_user.email}")
        print(f"[RESERVATIONS] - Trip ID: {trip_id}")
        print(f"[RESERVATIONS] - Seats: {seats_booked}")

        # Vérifier que le trajet existe
        trip = db.query(Trip).filter(Trip.id == trip_id).first()

        if not trip:
            print(f"[RESERVATIONS] Trajet non trouvé: {trip_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trajet non trouvé"
            )

        print(f"[RESERVATIONS] Trajet trouvé: {trip.departure_location} -> {trip.arrival_location}")

        # Vérifier qu'il y a assez de places
        if seats_booked > trip.available_seats:
            print(f"[RESERVATIONS] Pas assez de places: demandé {seats_booked}, disponible {trip.available_seats}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pas assez de places. Disponible: {trip.available_seats}"
            )

        # Vérifier que le passager n'a pas déjà une réservation
        existing_reservation = db.query(Reservation).filter(
            Reservation.trip_id == trip_id,
            Reservation.passenger_id == current_user.id,
            Reservation.status != "cancelled"
        ).first()

        if existing_reservation:
            print(f"[RESERVATIONS] Passager a déjà une réservation sur ce trajet!")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous avez déjà une réservation sur ce trajet"
            )

        print(f"[RESERVATIONS] Pas de doublon détecté")

        # Créer la réservation
        total_price = seats_booked * trip.price_per_seat

        new_reservation = Reservation(
            trip_id=trip_id,
            passenger_id=current_user.id,
            seats_booked=seats_booked,
            total_price=total_price,
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_reservation)

        # Réduire les places disponibles
        trip.available_seats -= seats_booked

        print(f"[RESERVATIONS] Réservation créée: ID {new_reservation.id}")
        print(f"[RESERVATIONS] Places réduites: {trip.available_seats} restantes")

        db.commit()
        db.refresh(new_reservation)

        # Créer/récupérer la conversation
        print(f"[RESERVATIONS] Création conversation entre {current_user.id} et {trip.driver_id}")

        existing_conversation = db.query(Conversation).filter(
            ((Conversation.user_1_id == current_user.id) & (Conversation.user_2_id == trip.driver_id)) |
            ((Conversation.user_1_id == trip.driver_id) & (Conversation.user_2_id == current_user.id))
        ).first()

        if existing_conversation:
            print(f"[RESERVATIONS] Conversation existe déjà: {existing_conversation.id}")
            new_reservation.conversation_id = existing_conversation.id
        else:
            print(f"[RESERVATIONS] Création nouvelle conversation")
            conversation = Conversation(
                user_1_id=current_user.id,
                user_2_id=trip.driver_id,
                reservation_id=new_reservation.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(conversation)
            db.commit()
            db.refresh(conversation)

            print(f"[RESERVATIONS] Conversation créée: {conversation.id}")
            new_reservation.conversation_id = conversation.id
            db.commit()

        print(f"[RESERVATIONS] Réservation finalisée\n")

        return {
            "status": "success",
            "message": "Réservation créée avec succès",
            "reservation": {
                "id": new_reservation.id,
                "trip_id": new_reservation.trip_id,
                "passenger_id": new_reservation.passenger_id,
                "seats_booked": new_reservation.seats_booked,
                "total_price": new_reservation.total_price,
                "status": new_reservation.status,
                "conversation_id": new_reservation.conversation_id,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[RESERVATIONS] ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET MY RESERVATIONS (PASSAGER)
# ============================================

@router.get("/my-reservations", response_model=dict)
async def get_my_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer mes réservations (passager)"""
    try:
        print(f"\n[RESERVATIONS] GET /my-reservations pour {current_user.email}")

        reservations = db.query(Reservation).filter(
            Reservation.passenger_id == current_user.id,
            Reservation.status != "cancelled"
        ).all()

        print(f"[RESERVATIONS] {len(reservations)} réservations trouvées")

        result = []
        for res in reservations:
            trip = db.query(Trip).filter(Trip.id == res.trip_id).first()

            if not trip:
                continue

            driver = db.query(User).filter(User.id == trip.driver_id).first()
            vehicle = None

            if trip.vehicle_id:
                vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()

            reservation_obj = {
                "id": res.id,
                "trip_id": res.trip_id,
                "passenger_id": res.passenger_id,
                "seats_booked": res.seats_booked,
                "total_price": res.total_price,
                "status": res.status,
                "conversation_id": res.conversation_id,
                "created_at": res.created_at.isoformat() if res.created_at else None,
                "trip": {
                    "id": trip.id,
                    "departure_location": trip.departure_location,
                    "arrival_location": trip.arrival_location,
                    "departure_time": trip.departure_time.isoformat() if trip.departure_time else None,
                    "price_per_seat": trip.price_per_seat,
                    "driver": {
                        "id": driver.id,
                        "name": driver.name,
                        "email": driver.email,
                        "phone": driver.phone,
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
            }
            result.append(reservation_obj)

        print(f"[RESERVATIONS] Réponse: {len(result)} réservations\n")

        return {
            "status": "success",
            "reservations": result
        }
    except Exception as e:
        print(f"[RESERVATIONS] ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET RECEIVED RESERVATIONS (CONDUCTEUR) ✅
# ============================================

@router.get("/received", response_model=dict)
async def get_received_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les réservations reçues sur mes trajets (conducteur)"""
    try:
        print(f"\n[RESERVATIONS] GET /received pour {current_user.email}")

        # Récupérer tous les trajets du conducteur
        my_trips = db.query(Trip).filter(
            Trip.driver_id == current_user.id
        ).all()

        print(f"[RESERVATIONS] {len(my_trips)} trajets trouvés pour le conducteur")

        # Récupérer toutes les réservations sur ces trajets
        trip_ids = [trip.id for trip in my_trips]
        reservations = []

        if trip_ids:
            reservations = db.query(Reservation).filter(
                Reservation.trip_id.in_(trip_ids)
            ).all()

        print(f"[RESERVATIONS] {len(reservations)} réservations trouvées")

        result = []
        for res in reservations:
            trip = db.query(Trip).filter(Trip.id == res.trip_id).first()
            passenger = db.query(User).filter(User.id == res.passenger_id).first()

            result.append({
                "id": res.id,
                "trip_id": res.trip_id,
                "passenger_id": res.passenger_id,
                "seats_booked": res.seats_booked,
                "total_price": res.total_price,
                "status": res.status,
                "created_at": res.created_at.isoformat() if res.created_at else None,
                "passenger": {
                    "id": passenger.id,
                    "name": passenger.name,
                    "email": passenger.email,
                    "phone": passenger.phone,
                } if passenger else None,
                "trip": {
                    "id": trip.id,
                    "departure_location": trip.departure_location,
                    "arrival_location": trip.arrival_location,
                    "departure_time": trip.departure_time.isoformat() if trip.departure_time else None,
                    "price_per_seat": trip.price_per_seat,
                } if trip else None
            })

        print(f"[RESERVATIONS] {len(result)} réservations formatées\n")

        return {
            "status": "success",
            "reservations": result
        }
    except Exception as e:
        print(f"[RESERVATIONS] ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# UPDATE RESERVATION STATUS (CONDUCTEUR) ✅
# ============================================

@router.put("/{reservation_id}", response_model=dict)
async def update_reservation_status(
    reservation_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour le statut d'une réservation (accepted/declined)"""
    try:
        print(f"\n[RESERVATIONS] PUT {reservation_id} pour {current_user.email}")

        new_status = data.get("status")

        if new_status not in ["accepted", "declined"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le statut doit être 'accepted' ou 'declined'"
            )

        # Récupérer la réservation
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Réservation non trouvée"
            )

        # Vérifier que c'est le conducteur du trajet
        trip = db.query(Trip).filter(Trip.id == reservation.trip_id).first()

        if not trip or trip.driver_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas le conducteur de ce trajet"
            )

        # Mettre à jour le statut
        print(f"[RESERVATIONS] Changement statut: {reservation.status} → {new_status}")

        reservation.status = new_status
        reservation.updated_at = datetime.utcnow()

        # Si refusée, restaurer les places
        if new_status == "declined":
            trip.available_seats += reservation.seats_booked
            print(f"[RESERVATIONS] Places restaurées: {trip.available_seats}")

        db.commit()
        db.refresh(reservation)

        print(f"[RESERVATIONS] Réservation mise à jour\n")

        return {
            "status": "success",
            "message": f"Réservation {new_status}",
            "reservation": {
                "id": reservation.id,
                "status": reservation.status,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[RESERVATIONS] ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# CANCEL RESERVATION (PASSAGER)
# ============================================

@router.put("/{reservation_id}/cancel", response_model=dict)
async def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Annuler une réservation (passager)"""
    try:
        print(f"\n[RESERVATIONS] Annuler réservation {reservation_id} par {current_user.email}")

        reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()

        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Réservation non trouvée"
            )

        # Vérifier que c'est le passager
        if reservation.passenger_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul le passager peut annuler sa réservation"
            )

        # Charger le trip et restaurer les places
        trip = db.query(Trip).filter(Trip.id == reservation.trip_id).first()

        if trip:
            trip.available_seats += reservation.seats_booked
            print(f"[RESERVATIONS] Places restaurées: {trip.available_seats}")

        # Mettre à jour le statut
        reservation.status = "cancelled"
        reservation.updated_at = datetime.utcnow()

        db.commit()

        print(f"[RESERVATIONS] Réservation annulée\n")

        return {
            "status": "success",
            "message": "Réservation annulée",
            "reservation": {
                "id": reservation.id,
                "status": reservation.status,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[RESERVATIONS] ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )
