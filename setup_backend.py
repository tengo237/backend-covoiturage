# -*- coding: utf-8 -*-

# ========== routes/auth.py ==========
routes_auth_content = '''# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse
from auth import hash_password, verify_password, create_access_token
from datetime import timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Cet email est deja utilise")
    
    user = User(
        name=request.name,
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),
        roles="passenger",
        current_role="passenger",
        is_admin=False,
        is_active=True,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte desactive")
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.post("/admin-login", response_model=TokenResponse)
async def admin_login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acces administrateur requis")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte desactive")
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }
'''

# ========== routes/vehicles.py ==========
routes_vehicles_content = '''# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Vehicle
from schemas import VehicleCreate, VehicleResponse, VehicleUpdate
from auth import get_current_user

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

@router.post("", response_model=dict)
async def create_vehicle(
    vehicle: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing_vehicle = db.query(Vehicle).filter(Vehicle.plate == vehicle.plate).first()
    if existing_vehicle:
        raise HTTPException(status_code=409, detail="Plaque deja existante")
    
    db_vehicle = Vehicle(
        user_id=current_user.id,
        brand=vehicle.brand,
        model=vehicle.model,
        plate=vehicle.plate,
        color=vehicle.color,
        seats=vehicle.seats,
        is_active=True,
    )
    
    db.add(db_vehicle)
    
    if "driver" not in current_user.roles:
        if current_user.roles == "passenger":
            current_user.roles = "passenger,driver"
        current_user.current_role = "driver"
    
    db.commit()
    db.refresh(db_vehicle)
    db.refresh(current_user)
    
    return {
        "status": "success",
        "message": "Vehicule cree! Vous etes conducteur!",
        "vehicle": VehicleResponse.model_validate(db_vehicle),
        "user_roles": current_user.roles,
    }

@router.get("", response_model=dict)
async def get_my_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicles = db.query(Vehicle).filter(Vehicle.user_id == current_user.id).all()
    return {
        "status": "success",
        "count": len(vehicles),
        "vehicles": [VehicleResponse.model_validate(v) for v in vehicles]
    }

@router.get("/{vehicle_id}", response_model=dict)
async def get_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicule non trouve")
    
    if vehicle.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")
    
    return {
        "status": "success",
        "vehicle": VehicleResponse.model_validate(vehicle)
    }

@router.put("/{vehicle_id}", response_model=dict)
async def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicule non trouve")
    
    if vehicle.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")
    
    if vehicle_update.brand:
        vehicle.brand = vehicle_update.brand
    if vehicle_update.model:
        vehicle.model = vehicle_update.model
    if vehicle_update.color:
        vehicle.color = vehicle_update.color
    if vehicle_update.seats:
        vehicle.seats = vehicle_update.seats
    
    db.commit()
    db.refresh(vehicle)
    
    return {
        "status": "success",
        "message": "Vehicule modifie",
        "vehicle": VehicleResponse.model_validate(vehicle)
    }

@router.delete("/{vehicle_id}", response_model=dict)
async def delete_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicule non trouve")
    
    if vehicle.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")
    
    db.delete(vehicle)
    
    remaining = db.query(Vehicle).filter(Vehicle.user_id == current_user.id).count()
    
    if remaining == 0:
        current_user.roles = "passenger"
        current_user.current_role = "passenger"
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Vehicule supprime",
        "remaining_vehicles": remaining,
    }
'''

# Creer les fichiers
try:
    with open("routes/auth.py", "w", encoding="utf-8") as f:
        f.write(routes_auth_content)
    print("OK routes/auth.py")
except Exception as e:
    print(f"ERROR routes/auth.py: {e}")

try:
    with open("routes/vehicles.py", "w", encoding="utf-8") as f:
        f.write(routes_vehicles_content)
    print("OK routes/vehicles.py")
except Exception as e:
    print(f"ERROR routes/vehicles.py: {e}")

print("\nSetup OK!")