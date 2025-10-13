from datetime import datetime, timedelta
from src.db.mongo import ai_insight
from collections import Counter

def get_trending_topics(period_days=7, limit=10):
    """Get trending topics in specified period"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$unwind": "$topics"},
        {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_topic_revenue_correlation(period_days=30):
    """Show which topics generate most revenue"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1  # Only paid orders
        }},
        {"$unwind": "$topics"},
        {"$group": {
            "_id": "$topics",
            "total_revenue": {"$sum": "$total_price"},
            "order_count": {"$sum": 1},
            "avg_order_value": {"$avg": "$total_price"}
        }},
        {"$sort": {"total_revenue": -1}}
    ]
    return list(ai_insight.aggregate(pipeline))

def get_topics_by_emotion(emotion_filter=None, period_days=30):
    """Get topics filtered by specific emotion and their revenue"""
    since = datetime.utcnow() - timedelta(days=period_days)
    
    match_stage = {
        "created_at": {"$gte": since},
        "payment_status": 1
    }
    
    # Add emotion filter if provided
    if emotion_filter:
        if isinstance(emotion_filter, list):
            match_stage["emotional_tone"] = {"$in": emotion_filter}
        else:
            match_stage["emotional_tone"] = emotion_filter
    
    pipeline = [
        {"$match": match_stage},
        {"$unwind": "$topics"},
        {"$group": {
            "_id": "$topics",
            "total_revenue": {"$sum": "$total_price"},
            "order_count": {"$sum": 1},
            "avg_order_value": {"$avg": "$total_price"},
            "emotions": {"$addToSet": "$emotional_tone"}
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": 20}
    ]
    
    return list(ai_insight.aggregate(pipeline))

def get_question_patterns(period_days=30):
    """Analyze common question themes"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    docs = ai_insight.find(
        {"reference_date": {"$gte": since}},
        {"questions": 1, "topics": 1}
    )
    
    all_topics = []
    question_count = 0
    
    for doc in docs:
        questions = doc.get("questions", [])
        question_count += len(questions)
        all_topics.extend(doc.get("topics", []))
    
    topic_freq = Counter(all_topics)
    
    return {
        "total_questions": question_count,
        "unique_topics": len(topic_freq),
        "top_topics": topic_freq.most_common(10)
    }