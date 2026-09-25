# -*- coding: utf-8 -*-
from jose import JWTError, jwt
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from fastapi import HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from database import get_db

# ============================================
# UTILITAIRES JWT
# ============================================

def create_access_token(email: str, expires_delta: timedelta = None) -> str:
    """Créer un JWT token"""
    to_encode = {"email": email}
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Vérifier et décoder un JWT token"""
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_email_from_token(token: str) -> str:
    """Extraire l'email du token"""
    payload = verify_token(token)
    if payload:
        return payload.get("email")
    return None

def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Récupérer l'utilisateur courant à partir du header Authorization"""
    from models import User
    
    print(f"🔵 get_current_user called")
    print(f"   authorization header: {authorization[:30] if authorization else 'NONE'}...")
    
    if not authorization:
        print(f"🔴 Pas d'authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant"
        )
    
    # Extraire le token de "Bearer TOKEN"
    parts = authorization.split()
    
    if len(parts) != 2 or parts[0] != "Bearer":
        print(f"🔴 Format invalid: {parts}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Format de token invalide"
        )
    
    token = parts[1]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        
        if email is None:
            print(f"🔴 Email manquant dans token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
    except JWTError as e:
        print(f"🔴 Erreur JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré"
        )
    
    db_user = db.query(User).filter(User.email == email).first()
    
    if db_user is None:
        print(f"🔴 Utilisateur non trouvé: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé"
        )
    
    print(f"🟢 get_current_user OK: {email}")
    return db_user

def get_admin_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Récupérer l'utilisateur admin"""
    user = get_current_user(authorization, db)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )
    
    return user
