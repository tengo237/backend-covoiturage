# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import User
from routes.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["users"])

# ============================================
# SCHEMAS
# ============================================

class UpdatePaymentMethodRequest(BaseModel):
    payment_method: str  # "orange_money" ou "mtn_momo"
    phone_number: str


# ============================================
# GET CURRENT USER
# ============================================

@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Récupérer les infos de l'utilisateur connecté"""
    try:
        return {
            "status": "success",
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "phone": current_user.phone,
                "photo_url": current_user.photo_url,
                "roles": current_user.roles,
                "current_role": current_user.current_role,
                "is_admin": current_user.is_admin,
                "payment_method": current_user.payment_method,
                "payment_phone_number": current_user.payment_phone_number,
                "payment_operator": current_user.payment_operator,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# UPDATE PAYMENT METHOD
# ============================================

@router.put("/update-payment-method", response_model=dict)
async def update_payment_method(
    request: UpdatePaymentMethodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ Mettre à jour le mode de paiement de l'utilisateur
    """
    try:
        print(f"\n[USERS] 🔵 Mise à jour mode paiement pour {current_user.email}")
        
        # Valider la méthode
        if request.payment_method not in ["orange_money", "mtn_momo"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Méthode invalide"
            )
        
        # Valider le numéro
        clean_phone = request.phone_number.replace("+", "").replace(" ", "").replace("-", "")
        if clean_phone.startswith("237"):
            clean_phone = clean_phone[3:]
        
        if len(clean_phone) < 9:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Numéro invalide"
            )
        
        # Déterminer l'opérateur
        prefix = int(clean_phone[:3])
        
        if request.payment_method == "orange_money":
            if not (650 <= prefix <= 659 or 680 <= prefix <= 689 or 690 <= prefix <= 699):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ce numéro n'est pas un numéro Orange Money"
                )
            operator = "orange"
        else:  # mtn_momo
            if not (670 <= prefix <= 679 or 680 <= prefix <= 689 or 690 <= prefix <= 699):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ce numéro n'est pas un numéro MTN Mobile Money"
                )
            operator = "mtn"
        
        # Formater le numéro
        formatted_phone = "+237" + clean_phone
        
        # Mettre à jour l'utilisateur
        current_user.payment_method = request.payment_method
        current_user.payment_phone_number = formatted_phone
        current_user.payment_operator = operator
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        print(f"[USERS] ✅ Mode paiement mis à jour")
        print(f"[USERS] 💳 Méthode: {request.payment_method}")
        print(f"[USERS] 📞 Numéro: {formatted_phone}")
        print(f"[USERS] 🏢 Opérateur: {operator}\n")
        
        return {
            "status": "success",
            "message": "Mode de paiement mis à jour",
            "user": {
                "payment_method": current_user.payment_method,
                "payment_phone_number": current_user.payment_phone_number,
                "payment_operator": current_user.payment_operator,
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS] ❌ ERREUR: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )
