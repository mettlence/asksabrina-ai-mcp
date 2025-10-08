from pymongo import MongoClient
from src.config import settings
import certifi

client = MongoClient(settings.MONGODB_URI, tlsCAFile=certifi.where())
db = client["development"]
ai_insight = db["ai_insight"]

# Test connection
try:
    client.admin.command('ping')
    print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
except Exception as e:
    print(f"MongoDB connection failed: {e}")