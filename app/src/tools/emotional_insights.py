from datetime import datetime, timedelta
from src.db.mongo import ai_insight
from collections import Counter

def get_emotion_distribution(period_days=30):
    """Get breakdown of customer emotions"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$unwind": "$emotional_tone"},
        {"$group": {"_id": "$emotional_tone", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_emotion_conversion_rate(period_days=30):
    """Correlate emotions with payment completion"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$unwind": "$emotional_tone"},
        {"$group": {
            "_id": "$emotional_tone",
            "total_orders": {"$sum": 1},
            "completed_orders": {
                "$sum": {"$cond": [{"$eq": ["$payment_status", 1]}, 1, 0]}
            }
        }},
        {"$addFields": {
            "conversion_rate": {
                "$multiply": [
                    {"$divide": ["$completed_orders", "$total_orders"]},
                    100
                ]
            }
        }},
        {"$sort": {"conversion_rate": -1}}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_high_risk_customers(threshold_emotions=None):
    """Flag customers with negative emotional patterns"""
    if threshold_emotions is None:
        threshold_emotions = ["anxious", "stressed", "depressed", "hopeless", "distressed"]
    
    pipeline = [
        {"$match": {"customer_id": {"$ne": None}}},
        {"$unwind": "$emotional_tone"},
        {"$match": {"emotional_tone": {"$in": threshold_emotions}}},
        {"$group": {
            "_id": "$customer_id",
            "negative_emotion_count": {"$sum": 1},
            "emotions": {"$addToSet": "$emotional_tone"},
            "last_order": {"$max": "$created_at"}
        }},
        {"$sort": {"negative_emotion_count": -1}},
        {"$limit": 50}
    ]
    return list(ai_insight.aggregate(pipeline))