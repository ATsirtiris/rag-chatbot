# app/users.py

from fastapi import APIRouter, HTTPException, Depends

from pydantic import BaseModel

import hashlib

from .auth import create_token

from .memory import redis



router = APIRouter(prefix="/auth", tags=["auth"])



class User(BaseModel):

    username: str

    password: str



def hash_password(pw: str):

    return hashlib.sha256(pw.encode()).hexdigest()



@router.post("/signup")

async def signup(user: User):

    key = f"user:{user.username}"

    exists = await redis.exists(key)

    if exists:

        raise HTTPException(status_code=400, detail="User already exists")

    await redis.hset(key, mapping={"password": hash_password(user.password)})

    # Automatically log in the user after signup
    token = create_token(user.username)
    return {"access_token": token, "token_type": "bearer", "message": "User created"}



@router.post("/login")

async def login(user: User):

    key = f"user:{user.username}"

    data = await redis.hgetall(key)

    if not data or data.get("password") != hash_password(user.password):

        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.username)

    return {"access_token": token, "token_type": "bearer"}

