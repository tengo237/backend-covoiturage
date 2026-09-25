# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Review, Reservation, User, Trip
from routes.auth import get_current_user

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

# ============================================
# PYDANTIC MODELS
# ============================================

class CreateReviewRequest(BaseModel):
    """Modèle pour créer un avis"""
    reservation_id: int
    driver_id: int
    rating: int
    comment: str = "Pas de commentaire"

    class Config:
        schema_extra = {
            "example": {
                "reservation_id": 5,
                "driver_id": 7,
                "rating": 5,
                "comment": "Bon conducteur, très rapide!"
            }
        }

# ============================================
# CREATE REVIEW (PASSAGER)
# ============================================

@router.post("", response_model=dict)
async def create_review(
    review_data: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer un avis (passager sur conducteur)"""
    try:
        print(f"\n[REVIEWS] Création avis par {current_user.email}")
        print(f"[REVIEWS] Données reçues: {review_data.dict()}")

        # Valider le rating
        if review_data.rating < 1 or review_data.rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le rating doit être entre 1 et 5"
            )

        # Vérifier que la réservation existe
        reservation = db.query(Reservation).filter(
            Reservation.id == review_data.reservation_id
        ).first()

        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Réservation non trouvée"
            )

        # Vérifier que c'est le passager de la réservation
        if reservation.passenger_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas le passager de cette réservation"
            )

        # Vérifier qu'il n'y a pas déjà un avis
        existing_review = db.query(Review).filter(
            Review.reservation_id == review_data.reservation_id,
            Review.passenger_id == current_user.id
        ).first()

        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous avez déjà laissé un avis pour cette réservation"
            )

        # Créer l'avis
        new_review = Review(
            reservation_id=review_data.reservation_id,
            driver_id=review_data.driver_id,
            passenger_id=current_user.id,
            rating=review_data.rating,
            comment=review_data.comment,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        print(f"[REVIEWS] ✅ Avis créé avec succès: ID={new_review.id}, Rating={new_review.rating}⭐\n")

        return {
            "status": "success",
            "message": "Avis créé avec succès",
            "review": {
                "id": new_review.id,
                "reservation_id": new_review.reservation_id,
                "driver_id": new_review.driver_id,
                "passenger_id": new_review.passenger_id,
                "rating": new_review.rating,
                "comment": new_review.comment,
                "created_at": new_review.created_at.isoformat() if new_review.created_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REVIEWS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET DRIVER REVIEWS (CONDUCTEUR)
# ============================================

@router.get("/driver/{driver_id}", response_model=dict)
async def get_driver_reviews(
    driver_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les avis reçus par un conducteur"""
    try:
        print(f"\n[REVIEWS] GET avis pour conducteur {driver_id}")

        reviews = db.query(Review).filter(
            Review.driver_id == driver_id
        ).all()

        print(f"[REVIEWS] {len(reviews)} avis trouvés")

        result = []
        for review in reviews:
            passenger = db.query(User).filter(User.id == review.passenger_id).first()

            result.append({
                "id": review.id,
                "reservation_id": review.reservation_id,
                "driver_id": review.driver_id,
                "passenger_id": review.passenger_id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "passenger": {
                    "id": passenger.id,
                    "name": passenger.name,
                    "email": passenger.email,
                    "photo_url": passenger.photo_url,
                } if passenger else None
            })

        # Calculer la moyenne
        if reviews:
            average_rating = sum([r.rating for r in reviews]) / len(reviews)
        else:
            average_rating = 0

        print(f"[REVIEWS] Note moyenne: {average_rating}\n")

        return {
            "status": "success",
            "reviews": result,
            "stats": {
                "total_reviews": len(reviews),
                "average_rating": round(average_rating, 1),
            }
        }
    except Exception as e:
        print(f"[REVIEWS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET MY DRIVER REVIEWS (MOI EN TANT QUE CONDUCTEUR)
# ============================================

@router.get("/my-reviews", response_model=dict)
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer MES avis (en tant que conducteur)"""
    try:
        print(f"\n[REVIEWS] GET mes avis pour {current_user.email}")

        reviews = db.query(Review).filter(
            Review.driver_id == current_user.id
        ).all()

        print(f"[REVIEWS] {len(reviews)} avis trouvés")

        result = []
        for review in reviews:
            passenger = db.query(User).filter(User.id == review.passenger_id).first()

            result.append({
                "id": review.id,
                "reservation_id": review.reservation_id,
                "driver_id": review.driver_id,
                "passenger_id": review.passenger_id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "passenger": {
                    "id": passenger.id,
                    "name": passenger.name,
                    "email": passenger.email,
                    "photo_url": passenger.photo_url,
                } if passenger else None
            })

        # Calculer statistiques
        if reviews:
            average_rating = sum([r.rating for r in reviews]) / len(reviews)
            ratings_count = {
                5: len([r for r in reviews if r.rating == 5]),
                4: len([r for r in reviews if r.rating == 4]),
                3: len([r for r in reviews if r.rating == 3]),
                2: len([r for r in reviews if r.rating == 2]),
                1: len([r for r in reviews if r.rating == 1]),
            }
        else:
            average_rating = 0
            ratings_count = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}

        print(f"[REVIEWS] Note moyenne: {average_rating}\n")

        return {
            "status": "success",
            "reviews": result,
            "stats": {
                "total_reviews": len(reviews),
                "average_rating": round(average_rating, 1),
                "ratings_count": ratings_count,
            }
        }
    except Exception as e:
        print(f"[REVIEWS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET RESERVATIONS WITHOUT REVIEW (PASSAGER)
# ============================================

@router.get("/pending-reviews", response_model=dict)
async def get_pending_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les réservations sans avis (passager)"""
    try:
        print(f"\n[REVIEWS] GET réservations sans avis pour {current_user.email}")

        # Récupérer les réservations acceptées du passager
        reservations = db.query(Reservation).filter(
            Reservation.passenger_id == current_user.id,
            Reservation.status == "accepted"
        ).all()

        print(f"[REVIEWS] {len(reservations)} réservations acceptées trouvées")

        # Filtrer celles sans avis
        result = []
        for res in reservations:
            review = db.query(Review).filter(
                Review.reservation_id == res.id,
                Review.passenger_id == current_user.id
            ).first()

            if not review:  # Pas d'avis encore
                trip = db.query(Trip).filter(Trip.id == res.trip_id).first()
                driver = db.query(User).filter(User.id == trip.driver_id).first() if trip else None

                result.append({
                    "id": res.id,
                    "trip_id": res.trip_id,
                    "seats_booked": res.seats_booked,
                    "total_price": res.total_price,
                    "trip": {
                        "departure_location": trip.departure_location,
                        "arrival_location": trip.arrival_location,
                        "departure_time": trip.departure_time.isoformat() if trip else None,
                    } if trip else None,
                    "driver": {
                        "id": driver.id,
                        "name": driver.name,
                        "email": driver.email,
                    } if driver else None
                })

        print(f"[REVIEWS] {len(result)} réservations sans avis\n")

        return {
            "status": "success",
            "reservations": result
        }
    except Exception as e:
        print(f"[REVIEWS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )
