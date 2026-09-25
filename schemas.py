# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ============================================
# AUTH
# ============================================

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str
    roles: str = "passenger"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    photo_url: Optional[str]
    roles: str
    current_role: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# VEHICLE
# ============================================

class VehicleCreate(BaseModel):
    brand: str
    model: str
    year: int
    color: str
    plate: str

class VehicleUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    plate: Optional[str] = None

class VehicleResponse(BaseModel):
    id: int
    driver_id: int
    brand: str
    model: str
    year: int
    color: str
    plate: str
    vehicle_photo_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# TRIP
# ============================================

class TripCreate(BaseModel):
    vehicle_id: int
    departure_location: str
    arrival_location: str
    departure_time: datetime
    arrival_time: Optional[datetime] = None
    available_seats: int
    price_per_seat: float
    description: Optional[str] = None

class TripResponse(BaseModel):
    id: int
    driver_id: int
    vehicle_id: int
    departure_location: str
    arrival_location: str
    departure_time: datetime
    arrival_time: Optional[datetime]
    available_seats: int
    price_per_seat: float
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TripUpdate(BaseModel):
    departure_location: Optional[str] = None
    arrival_location: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    available_seats: Optional[int] = None
    price_per_seat: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None

# ============================================
# RESERVATION
# ============================================

class ReservationCreate(BaseModel):
    trip_id: int
    seats_booked: int = 1

class ReservationResponse(BaseModel):
    id: int
    trip_id: int
    passenger_id: int
    seats_booked: int
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# TRACKING
# ============================================

class TripTrackingCreate(BaseModel):
    trip_id: int
    driver_latitude: float
    driver_longitude: float

class TripTrackingResponse(BaseModel):
    id: int
    trip_id: int
    driver_id: int
    latitude: float
    longitude: float
    speed: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# MESSAGE
# ============================================

class MessageCreate(BaseModel):
    conversation_id: int
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    is_read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# ALERT
# ============================================

class AlertCreate(BaseModel):
    trip_id: int
    alert_type: str
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class AlertResponse(BaseModel):
    id: int
    trip_id: int
    driver_id: int
    alert_type: str
    description: str
    latitude: Optional[float]
    longitude: Optional[float]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# REVIEW
# ============================================

class ReviewCreate(BaseModel):
    trip_id: int
    reviewed_user_id: int
    rating: int
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    trip_id: int
    reviewer_id: int
    reviewed_user_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
