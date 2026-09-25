# routes/eye_detection.py - Détection d'yeux avec MediaPipe (SANS OpenCV)
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import mediapipe as mp
import numpy as np
from PIL import Image
import io

router = APIRouter(prefix="/api/eye-detection", tags=["eye-detection"])

# Initialiser MediaPipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def calculate_eye_aspect_ratio(eye_landmarks):
    """
    Calculer le Eye Aspect Ratio (EAR)
    EAR < 0.15 = yeux fermés
    EAR > 0.25 = yeux ouverts
    """
    vertical1 = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
    vertical2 = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
    horizontal = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
    
    ear = (vertical1 + vertical2) / (2.0 * horizontal)
    return ear

@router.post("/analyze")
async def analyze_frame(file: UploadFile = File(...)):
    """
    Analyser une frame pour détecter si les yeux sont ouverts ou fermés
    
    Retourne:
    {
        "face_detected": bool,
        "eyes_closed": bool,
        "left_eye_ratio": float,
        "right_eye_ratio": float,
        "yawning": bool,
        "confidence": float
    }
    """
    try:
        # Lire l'image
        contents = await file.read()
        image_data = Image.open(io.BytesIO(contents)).convert('RGB')
        frame = np.array(image_data)
        
        # Détecter les landmarks du visage
        results = face_mesh.process(frame)
        
        if not results.multi_face_landmarks:
            return JSONResponse({
                "face_detected": False,
                "eyes_closed": False,
                "message": "No face detected"
            })
        
        # Récupérer les landmarks du premier visage
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Landmarks des yeux (FaceMesh a 468 points)
        # Oeil gauche
        left_eye_indices = [362, 385, 387, 263, 373, 380]
        left_eye_landmarks = [[landmarks[i].x, landmarks[i].y] for i in left_eye_indices]
        left_ear = calculate_eye_aspect_ratio(left_eye_landmarks)
        
        # Oeil droit
        right_eye_indices = [33, 160, 158, 133, 153, 144]
        right_eye_landmarks = [[landmarks[i].x, landmarks[i].y] for i in right_eye_indices]
        right_ear = calculate_eye_aspect_ratio(right_eye_landmarks)
        
        # Moyenne des deux yeux
        avg_ear = (left_ear + right_ear) / 2.0
        
        # Déterminer si yeux fermés
        eyes_closed = avg_ear < 0.2  # Seuil de 0.2
        
        # Détection du bâillement (distance bouche)
        mouth_top = landmarks[13]
        mouth_bottom = landmarks[14]
        mouth_distance = np.sqrt(
            (mouth_top.x - mouth_bottom.x)**2 + 
            (mouth_top.y - mouth_bottom.y)**2
        )
        yawning = mouth_distance > 0.05
        
        print(f"[EYE_DETECTION] Face detected!")
        print(f"[EYE_DETECTION] Left EAR: {left_ear:.3f}, Right EAR: {right_ear:.3f}")
        print(f"[EYE_DETECTION] Eyes closed: {eyes_closed}")
        print(f"[EYE_DETECTION] Yawning: {yawning}")
        
        return JSONResponse({
            "face_detected": True,
            "eyes_closed": eyes_closed,
            "left_eye_ratio": float(left_ear),
            "right_eye_ratio": float(right_ear),
            "avg_eye_ratio": float(avg_ear),
            "yawning": yawning,
            "confidence": 0.95
        })
        
    except Exception as e:
        print(f"[ERROR] Eye detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    """Vérifier que le service fonctionne"""
    return {"status": "OK", "service": "eye_detection"}