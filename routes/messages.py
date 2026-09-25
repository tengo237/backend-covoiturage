# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Message, Conversation, User
from routes.auth import get_current_user

router = APIRouter(prefix="/api/messages", tags=["messages"])

# ============================================
# GET MY CONVERSATIONS - ✅ AVEC reservation_id
# ============================================

@router.get("/my-conversations", response_model=dict)
async def get_my_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer mes conversations"""
    try:
        print(f"\n🔵 Récupération conversations de {current_user.email}")
        
        # Chercher les conversations où l'utilisateur est impliqué
        conversations = db.query(Conversation).filter(
            (Conversation.user_1_id == current_user.id) | 
            (Conversation.user_2_id == current_user.id)
        ).all()
        
        print(f"🟢 {len(conversations)} conversations trouvées")
        
        # Formater avec infos utilisateur et dernier message
        result = []
        for conv in conversations:
            # Récupérer l'autre utilisateur
            other_user_id = conv.user_2_id if conv.user_1_id == current_user.id else conv.user_1_id
            other_user = db.query(User).filter(User.id == other_user_id).first()
            
            # Récupérer le dernier message
            last_message = db.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(Message.created_at.desc()).first()
            
            # Compter les messages non-lus
            unread_count = db.query(Message).filter(
                Message.conversation_id == conv.id,
                Message.sender_id != current_user.id,
                Message.is_read == False
            ).count()
            
            conv_obj = {
                "id": conv.id,
                "user_1_id": conv.user_1_id,
                "user_2_id": conv.user_2_id,
                "reservation_id": conv.reservation_id,  # ✅ NOUVEAU
                "user_1": {
                    "id": conv.user_1_id,
                    "name": db.query(User).filter(User.id == conv.user_1_id).first().name if conv.user_1_id else None,
                },
                "user_2": {
                    "id": conv.user_2_id,
                    "name": db.query(User).filter(User.id == conv.user_2_id).first().name if conv.user_2_id else None,
                },
                "last_message": {
                    "id": last_message.id,
                    "content": last_message.content,
                    "sender_id": last_message.sender_id,
                    "created_at": last_message.created_at.isoformat(),
                } if last_message else None,
                "unread_count": unread_count,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            }
            
            result.append(conv_obj)
        
        # Trier par dernier message (les plus récents en premier)
        result.sort(
            key=lambda x: x['last_message']['created_at'] if x['last_message'] else x['created_at'],
            reverse=True
        )
        
        print(f"📦 Réponse formatée: {len(result)} conversations\n")
        
        return {
            "status": "success",
            "conversations": result
        }
    except Exception as e:
        print(f"\n🔴 Erreur get conversations: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# GET CONVERSATION MESSAGES
# ============================================

@router.get("/conversation/{conversation_id}", response_model=dict)
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les messages d'une conversation"""
    try:
        print(f"🔵 Récupération messages conversation {conversation_id}")
        
        # Vérifier que l'utilisateur fait partie de la conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation non trouvée"
            )
        
        if conversation.user_1_id != current_user.id and conversation.user_2_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas accès à cette conversation"
            )
        
        # Récupérer les messages
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        # Marquer comme lus
        for msg in messages:
            if msg.sender_id != current_user.id and not msg.is_read:
                msg.is_read = True
        db.commit()
        
        print(f"🟢 {len(messages)} messages chargés")
        
        result = [
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "is_read": msg.is_read,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]
        
        print(f"📦 Messages: {len(result)}\n")
        
        return {
            "status": "success",
            "messages": result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n🔴 Erreur get messages: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# SEND MESSAGE
# ============================================

@router.post("", response_model=dict)
async def send_message(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Envoyer un message"""
    try:
        print(f"🔵 Envoi message par {current_user.email}")
        
        conversation_id = data.get("conversation_id")
        content = data.get("content")
        
        if not conversation_id or not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="conversation_id et content requis"
            )
        
        # Vérifier que l'utilisateur fait partie de la conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation non trouvée"
            )
        
        if conversation.user_1_id != current_user.id and conversation.user_2_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas accès à cette conversation"
            )
        
        # Créer le message
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            content=content.strip(),
            is_read=False,
            created_at=datetime.utcnow()
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        print(f"🟢 Message créé: {message.id}")
        
        return {
            "status": "success",
            "message": {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "sender_id": message.sender_id,
                "content": message.content,
                "is_read": message.is_read,
                "created_at": message.created_at.isoformat(),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n🔴 Erreur send message: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )

# ============================================
# MARK AS READ
# ============================================

@router.put("/message/{message_id}/read", response_model=dict)
async def mark_as_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marquer un message comme lu"""
    try:
        print(f"🔵 Marquer message {message_id} comme lu")
        
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message non trouvé"
            )
        
        message.is_read = True
        db.commit()
        db.refresh(message)
        
        print(f"🟢 Message marqué comme lu")
        
        return {
            "status": "success",
            "message": "Message marqué comme lu"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n🔴 Erreur mark read: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )