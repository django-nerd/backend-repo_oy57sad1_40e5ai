from __future__ import annotations
import os
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic_settings import BaseSettings
from datetime import datetime

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "imperial_essence")

settings = Settings()

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.DATABASE_URL)
        _db = _client[settings.DATABASE_NAME]
    return _db

async def create_document(collection_name: str, data: dict[str, Any]) -> dict[str, Any]:
    db = await get_db()
    now = datetime.utcnow()
    data_with_meta = {**data, "created_at": now, "updated_at": now}
    result = await db[collection_name].insert_one(data_with_meta)
    inserted = await db[collection_name].find_one({"_id": result.inserted_id})
    if inserted and "_id" in inserted:
        inserted["id"] = str(inserted.pop("_id"))
    return inserted or {}

async def get_documents(collection_name: str, filter_dict: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = db[collection_name].find(filter_dict or {}).limit(limit)
    docs = []
    async for d in cursor:
        d["id"] = str(d.pop("_id"))
        docs.append(d)
    return docs
