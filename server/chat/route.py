from fastapi import APIRouter, HTTPException, Depends, Body
from auth.route import authenticate
from chat.chat_query import answer_query
from pydantic import BaseModel
from typing import List, Optional
import datetime
from config.db import (
    chat_history_collection
)
from bson.objectid import ObjectId


router=APIRouter()

@router.post("/chat")
async def chat(user=Depends(authenticate),query:str=Body(...,embed=True)):
    if user["role"] != "Student":
        raise HTTPException(
            status_code=403,
            details="Only student can ask questions"
        )
    
    response=await answer_query(
        query,user["role"],user["grade"],
    )

    chat_history_collection.insert_one({
        "user_id":user["user_id"],
        "timestamp":datetime.datetime.utcnow(),
        "query":query,
        "response":response["answer"],
        "sources":response["sources"],
    })

    return response