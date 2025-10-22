from datetime import datetime, timedelta
from src.db.mongo import ai_insight
from src.utils.date import get_utc_date_range_for_local_period

def get_sentiment_distribution(period_days=30):
    """Overall sentiment breakdown"""
    since = get_utc_date_range_for_local_period(period_days)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$group": {
            "_id": "$sentiment.label",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$sentiment.score"}
        }},
        {"$sort": {"count": -1}}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_sentiment_by_product(period_days=30):
    """Sentiment analysis per product"""
    since = get_utc_date_range_for_local_period(period_days)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$group": {
            "_id": {
                "product_id": "$product_id",
                "sentiment": "$sentiment.label"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.product_id": 1, "count": -1}}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_keyword_frequency(period_days=30, limit=20):
    """Most mentioned keywords"""
    since = get_utc_date_range_for_local_period(period_days)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$unwind": "$keywords"},
        {"$group": {"_id": "$keywords", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    return list(ai_insight.aggregate(pipeline))