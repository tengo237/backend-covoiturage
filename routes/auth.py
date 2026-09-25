# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
from database import get_db
from models import User
from schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import os
import shutil

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ============================================
# CREATE ACCESS TOKEN
# ============================================

def create_access_token(email: str, expires_delta: timedelta = None) -> str:
    """Creer un JWT token"""
    to_encode = {"email": email}
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

# ============================================
# GET CURRENT USER
# ============================================

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Recuperer l'utilisateur courant a partir du token JWT"""
    
    try:
        if not authorization:
            print("[AUTH] Header Authorization manquant")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token manquant"
            )
        
        parts = authorization.split()
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            print(f"[AUTH] Format Authorization invalide: {authorization}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Format Authorization invalide"
            )
        
        token = parts[1]
        
        print(f"[AUTH] Token recu: {token[:50]}...")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        
        print(f"[AUTH] Email du token: {email}")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide - email manquant"
            )
        
        db_user = db.query(User).filter(User.email == email).first()
        
        if db_user is None:
            print(f"[AUTH] Utilisateur non trouve: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouve"
            )
        
        print(f"[AUTH] Utilisateur trouve: {db_user.email}")
        return db_user
        
    except JWTError as e:
        print(f"[AUTH] Erreur JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expire"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Erreur authentification: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# LOGIN
# ============================================

@router.post("/login", response_model=dict)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Se connecter"""
    
    try:
        print(f"[LOGIN] Tentative: {request.email}")
        
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            print(f"[LOGIN] Utilisateur non trouve: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        
        if user.password_hash != request.password:
            print(f"[LOGIN] Mot de passe incorrect pour {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        
        access_token = create_access_token(user.email)
        
        print(f"[LOGIN] OK: {user.email}")
        
        return {
            "status": "success",
            "message": "Connexion reussie",
            "token": access_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "photo_url": user.photo_url,
                "roles": user.roles,
                "current_role": user.current_role,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LOGIN] Erreur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la connexion"
        )

# ============================================
# SIGNUP
# ============================================

@router.post("/signup", response_model=dict)
async def signup(
    request: SignupRequest,
    db: Session = Depends(get_db)
):
    """Creer un compte"""
    
    try:
        print(f"[SIGNUP] Tentative: {request.email}")
        
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            print(f"[SIGNUP] Email deja utilise: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est deja utilise"
            )
        
        new_user = User(
            name=request.name,
            email=request.email,
            phone=request.phone,
            password_hash=request.password,
            roles=request.roles,
            current_role=request.roles,
            is_admin=False,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        access_token = create_access_token(new_user.email)
        
        print(f"[SIGNUP] OK: {new_user.email}")
        
        return {
            "status": "success",
            "message": "Compte cree avec succes",
            "token": access_token,
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "email": new_user.email,
                "phone": new_user.phone,
                "photo_url": new_user.photo_url,
                "roles": new_user.roles,
                "current_role": new_user.current_role,
                "is_admin": new_user.is_admin,
                "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
                "updated_at": new_user.updated_at.isoformat() if new_user.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SIGNUP] Erreur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la creation du compte"
        )

# ============================================
# GET ME
# ============================================

@router.get("/me", response_model=dict)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Recuperer les infos de l'utilisateur courant"""
    
    try:
        print(f"[GET_ME] Pour {current_user.email}")
        
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
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GET_ME] Erreur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# UPDATE PROFILE - SOLUTION 1 (FormData) ✅
# ============================================

@router.put("/profile", response_model=dict)
async def update_profile(
    name: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    photo: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mettre a jour le profil utilisateur (Solution 1 - FormData)
    Accepte TOUS les champs en FormData (texte + photo)
    """
    
    try:
        print(f"\n[PROFILE] Debut mise a jour pour {current_user.email}")
        print(f"[PROFILE] - Nom: {name}")
        print(f"[PROFILE] - Email: {email}")
        print(f"[PROFILE] - Telephone: {phone}")
        print(f"[PROFILE] - Photo: {photo.filename if photo else 'Aucune'}")
        
        # Verifier que l'email n'existe pas deja
        if email and email != current_user.email:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"[PROFILE] Email deja utilise: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cet email est deja utilise"
                )
        
        # Mettre a jour les champs texte
        if name:
            current_user.name = name
            print(f"[PROFILE] OK - Nom mis a jour: {name}")
        
        if phone:
            current_user.phone = phone
            print(f"[PROFILE] OK - Telephone mis a jour: {phone}")
        
        if email:
            current_user.email = email
            print(f"[PROFILE] OK - Email mis a jour: {email}")
        
        # UPLOADER LA PHOTO SI FOURNIE
        if photo:
            print(f"[PROFILE] Debut upload photo: {photo.filename}")
            
            os.makedirs("uploads/profiles", exist_ok=True)
            
            filename = f"{current_user.id}_profile_{photo.filename}"
            filepath = os.path.join("uploads/profiles", filename)
            
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            
            photo_url = f"/uploads/profiles/{filename}"
            current_user.photo_url = photo_url
            print(f"[PROFILE] OK - Photo uploadee: {photo_url}")
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        print(f"[PROFILE] OK - Profil mis a jour avec succes\n")
        
        return {
            "status": "success",
            "message": "Profil mis a jour avec succes",
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "phone": current_user.phone,
                "photo_url": current_user.photo_url,
                "roles": current_user.roles,
                "current_role": current_user.current_role,
                "is_admin": current_user.is_admin,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PROFILE] ERREUR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# VERIFY TOKEN
# ============================================

@router.post("/verify-token", response_model=dict)
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """Verifier si un token est valide"""
    
    try:
        print(f"[VERIFY] Token valide pour {current_user.email}")
        
        return {
            "status": "success",
            "message": "Token valide",
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "phone": current_user.phone,
                "photo_url": current_user.photo_url,
                "roles": current_user.roles,
                "current_role": current_user.current_role,
                "is_admin": current_user.is_admin,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VERIFY] Erreur: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )

# ============================================
# LOGOUT
# ============================================

@router.post("/logout", response_model=dict)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Se deconnecter"""
    
    print(f"[LOGOUT] {current_user.email}")
    
    return {
        "status": "success",
        "message": "Deconnexion reussie"
    }