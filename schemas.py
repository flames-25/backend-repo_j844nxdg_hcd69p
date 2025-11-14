"""
Database Schemas for 1:1 Chat App

Each Pydantic model represents a collection in MongoDB. The collection name is the
lowercased class name (handled by the Flames platform conventions).
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class ChatUser(BaseModel):
    """
    Users in the chat app
    Collection: "chatuser"
    """
    username: str = Field(..., min_length=2, max_length=24, description="Public username")
    avatar_color: str = Field("#6366F1", description="Hex color for avatar background")

class Conversation(BaseModel):
    """
    A 1:1 conversation between two users
    Collection: "conversation"
    """
    participant_ids: List[str] = Field(..., min_items=2, max_items=2, description="Two user IDs")
    last_message_preview: Optional[str] = Field(None, description="Preview of last message")

class Message(BaseModel):
    """
    Message within a conversation
    Collection: "message"
    """
    conversation_id: str = Field(..., description="Conversation ID")
    sender_id: str = Field(..., description="Sender user ID")
    text: str = Field(..., min_length=1, max_length=4000, description="Message text")
    delivered: bool = Field(False, description="Delivered flag")
    read: bool = Field(False, description="Read flag")
