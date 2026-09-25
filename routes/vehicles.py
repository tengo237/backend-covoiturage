# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Vehicle, User
from routes.auth import get_current_user
import os
import shutil

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

# ============================================
# CREATE VEHICLE - AVEC UPLOAD PHOTO ✅
# ============================================

@router.post("", response_model=dict)
async def create_vehicle(
    brand: str = Form(...),
    model: str = Form(...),
    plate: str = Form(...),
    color: str = Form(None),
    photo: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creer un vehicule avec photo"""
    
    try:
        print(f"\n[VEHICLE] Debut creation pour {current_user.email}")
        print(f"[VEHICLE] - Brand: {brand}")
        print(f"[VEHICLE] - Model: {model}")
        print(f"[VEHICLE] - Plate: {plate}")
        print(f"[VEHICLE] - Color: {color}")
        print(f"[VEHICLE] - Photo: {photo.filename if photo else 'Aucune'}")
        
        # Verifier que la plaque n'existe pas deja
        existing = db.query(Vehicle).filter(Vehicle.plate == plate).first()
        if existing:
            print(f"[VEHICLE] Plaque deja utilisee: {plate}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cette plaque d'immatriculation est deja utilisee"
            )
        
        # Creer le vehicule
        new_vehicle = Vehicle(
            user_id=current_user.id,
            brand=brand,
            model=model,
            plate=plate,
            color=color,
            vehicle_photo_url=None,  # Sera rempli si photo
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # ✅ UPLOADER LA PHOTO SI FOURNIE
        if photo:
            print(f"[VEHICLE] Debut upload photo: {photo.filename}")
            
            os.makedirs("uploads/vehicles", exist_ok=True)
            
            # Creer le nom du fichier
            filename = f"{current_user.id}_vehicle_{photo.filename}"
            filepath = os.path.join("uploads/vehicles", filename)
            
            # Sauvegarder le fichier
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            
            photo_url = f"/uploads/vehicles/{filename}"
            new_vehicle.vehicle_photo_url = photo_url
            print(f"[VEHICLE] OK - Photo uploadee: {photo_url}")
        
        db.add(new_vehicle)
        db.commit()
        db.refresh(new_vehicle)
        
        print(f"[VEHICLE] OK - Vehicule cree: {new_vehicle.id}\n")
        
        return {
            "status": "success",
            "message": "Vehicule cree avec succes",
            "vehicle": {
                "id": new_vehicle.id,
                "brand": new_vehicle.brand,
                "model": new_vehicle.model,
                "plate": new_vehicle.plate,
                "color": new_vehicle.color,
                "photo_url": new_vehicle.vehicle_photo_url,
                "created_at": new_vehicle.created_at.isoformat() if new_vehicle.created_at else None,
                "updated_at": new_vehicle.updated_at.isoformat() if new_vehicle.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VEHICLE] ERREUR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET MY VEHICLE
# ============================================

@router.get("/my-vehicle", response_model=dict)
async def get_my_vehicle(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recuperer mon vehicule"""
    
    try:
        print(f"[VEHICLE] GET my-vehicle pour {current_user.email}")
        
        vehicle = db.query(Vehicle).filter(
            Vehicle.user_id == current_user.id
        ).first()
        
        if not vehicle:
            print(f"[VEHICLE] Aucun vehicule trouve pour {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun vehicule trouve"
            )
        
        print(f"[VEHICLE] OK - Vehicule trouve: {vehicle.id}")
        print(f"[VEHICLE] Photo URL: {vehicle.vehicle_photo_url}")
        
        return {
            "status": "success",
            "vehicle": {
                "id": vehicle.id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "plate": vehicle.plate,
                "color": vehicle.color,
                "photo_url": vehicle.vehicle_photo_url,  # ✅ IMPORTANT
                "created_at": vehicle.created_at.isoformat() if vehicle.created_at else None,
                "updated_at": vehicle.updated_at.isoformat() if vehicle.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VEHICLE] ERREUR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET ALL VEHICLES
# ============================================

@router.get("", response_model=dict)
async def get_all_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recuperer tous les vehicules"""
    
    try:
        print(f"[VEHICLE] GET all vehicles pour {current_user.email}")
        
        vehicles = db.query(Vehicle).all()
        
        print(f"[VEHICLE] {len(vehicles)} vehicules trouves")
        
        result = []
        for vehicle in vehicles:
            result.append({
                "id": vehicle.id,
                "user_id": vehicle.user_id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "plate": vehicle.plate,
                "color": vehicle.color,
                "photo_url": vehicle.vehicle_photo_url,
                "created_at": vehicle.created_at.isoformat() if vehicle.created_at else None,
                "updated_at": vehicle.updated_at.isoformat() if vehicle.updated_at else None,
            })
        
        return {
            "status": "success",
            "vehicles": result
        }
    except Exception as e:
        print(f"[VEHICLE] ERREUR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# UPDATE VEHICLE
# ============================================

@router.put("/{vehicle_id}", response_model=dict)
async def update_vehicle(
    vehicle_id: int,
    brand: str = Form(None),
    model: str = Form(None),
    plate: str = Form(None),
    color: str = Form(None),
    photo: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mettre a jour un vehicule"""
    
    try:
        print(f"[VEHICLE] UPDATE {vehicle_id} pour {current_user.email}")
        
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == vehicle_id,
            Vehicle.user_id == current_user.id
        ).first()
        
        if not vehicle:
            print(f"[VEHICLE] Vehicule non trouve ou acces refuse: {vehicle_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicule non trouve"
            )
        
        # Mettre a jour les champs
        if brand:
            vehicle.brand = brand
            print(f"[VEHICLE] Brand mis a jour: {brand}")
        
        if model:
            vehicle.model = model
            print(f"[VEHICLE] Model mis a jour: {model}")
        
        if plate:
            vehicle.plate = plate
            print(f"[VEHICLE] Plate mis a jour: {plate}")
        
        if color:
            vehicle.color = color
            print(f"[VEHICLE] Color mis a jour: {color}")
        
        # Uploader la photo si presente
        if photo:
            print(f"[VEHICLE] Upload nouvelle photo: {photo.filename}")
            
            os.makedirs("uploads/vehicles", exist_ok=True)
            
            filename = f"{current_user.id}_vehicle_{photo.filename}"
            filepath = os.path.join("uploads/vehicles", filename)
            
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            
            photo_url = f"/uploads/vehicles/{filename}"
            vehicle.vehicle_photo_url = photo_url
            print(f"[VEHICLE] Photo mise a jour: {photo_url}")
        
        vehicle.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(vehicle)
        
        print(f"[VEHICLE] OK - Vehicule mis a jour\n")
        
        return {
            "status": "success",
            "message": "Vehicule mis a jour avec succes",
            "vehicle": {
                "id": vehicle.id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "plate": vehicle.plate,
                "color": vehicle.color,
                "photo_url": vehicle.vehicle_photo_url,
                "created_at": vehicle.created_at.isoformat() if vehicle.created_at else None,
                "updated_at": vehicle.updated_at.isoformat() if vehicle.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VEHICLE] ERREUR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# DELETE VEHICLE
# ============================================

@router.delete("/{vehicle_id}", response_model=dict)
async def delete_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un vehicule"""
    
    try:
        print(f"[VEHICLE] DELETE {vehicle_id} pour {current_user.email}")
        
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == vehicle_id,
            Vehicle.user_id == current_user.id
        ).first()
        
        if not vehicle:
            print(f"[VEHICLE] Vehicule non trouve ou acces refuse: {vehicle_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicule non trouve"
            )
        
        # Supprimer le fichier photo si existe
        if vehicle.vehicle_photo_url:
            filepath = vehicle.vehicle_photo_url.replace("/uploads/vehicles/", "uploads/vehicles/")
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"[VEHICLE] Photo supprimee: {filepath}")
            except:
                pass
        
        db.delete(vehicle)
        db.commit()
        
        print(f"[VEHICLE] OK - Vehicule supprime\n")
        
        return {
            "status": "success",
            "message": "Vehicule supprime avec succes"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VEHICLE] ERREUR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )