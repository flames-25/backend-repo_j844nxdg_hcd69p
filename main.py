import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson.objectid import ObjectId
from datetime import datetime

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities

def to_str_id(doc):
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert datetimes to isoformat
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d

# Schemas for requests
class CreateUser(BaseModel):
    username: str
    avatar_color: Optional[str] = "#6366F1"

class StartConversation(BaseModel):
    user_a: str
    user_b: str

class SendMessage(BaseModel):
    conversation_id: str
    sender_id: str
    text: str

@app.get("/")
def read_root():
    return {"message": "Chat API ready"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Users
@app.post("/users")
def create_user(payload: CreateUser):
    data = payload.model_dump()
    user_id = create_document("chatuser", data)
    doc = db["chatuser"].find_one({"_id": ObjectId(user_id)})
    return to_str_id(doc)

@app.get("/users")
def list_users():
    docs = get_documents("chatuser")
    return [to_str_id(d) for d in docs]

# Conversations
@app.post("/conversations")
def start_conversation(payload: StartConversation):
    a = payload.user_a
    b = payload.user_b
    if a == b:
        raise HTTPException(status_code=400, detail="Cannot start conversation with self")
    # check if exists
    existing = db["conversation"].find_one({"participant_ids": {"$all": [a, b]}})
    if existing:
        return to_str_id(existing)
    conv_id = create_document("conversation", {
        "participant_ids": [a, b],
        "last_message_preview": None,
    })
    doc = db["conversation"].find_one({"_id": ObjectId(conv_id)})
    return to_str_id(doc)

@app.get("/conversations/{user_id}")
def get_conversations(user_id: str):
    convs = db["conversation"].find({"participant_ids": user_id}).sort("updated_at", -1)
    return [to_str_id(c) for c in convs]

# Messages
@app.post("/messages")
def send_message(payload: SendMessage):
    # verify conversation and sender belongs
    conv = db["conversation"].find_one({"_id": ObjectId(payload.conversation_id)})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if payload.sender_id not in conv.get("participant_ids", []):
        raise HTTPException(status_code=403, detail="Sender not in conversation")

    msg_id = create_document("message", {
        "conversation_id": payload.conversation_id,
        "sender_id": payload.sender_id,
        "text": payload.text,
        "delivered": True,
        "read": False,
    })
    # update conversation preview and timestamp
    db["conversation"].update_one({"_id": conv["_id"]}, {"$set": {"last_message_preview": payload.text, "updated_at": datetime.utcnow()}})

    doc = db["message"].find_one({"_id": ObjectId(msg_id)})
    return to_str_id(doc)

@app.get("/messages/{conversation_id}")
def list_messages(conversation_id: str, limit: int = 50, before: Optional[str] = None):
    filt = {"conversation_id": conversation_id}
    if before:
        try:
            filt["_id"] = {"$lt": ObjectId(before)}
        except Exception:
            pass
    msgs = db["message"].find(filt).sort("_id", -1).limit(limit)
    arr = [to_str_id(m) for m in msgs]
    return list(reversed(arr))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
