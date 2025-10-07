from pymongo import MongoClient
from src.config import settings

client = MongoClient(settings.MONGO_URI)
db = client["asksabrina"]
ai_insight = db["ai_insight"]
