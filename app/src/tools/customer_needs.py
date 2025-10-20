from datetime import datetime, timedelta
from src.db.mongo import ai_insight
from src.utils.date import get_utc_date_range_for_local_period

def get_customer_needs_distribution(period_days=30):
    """Identify what customers are looking for"""
    since = get_utc_date_range_for_local_period(period_days)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$unwind": "$possible_needs"},
        {"$group": {
            "_id": "$possible_needs",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_unmet_needs_analysis(period_days=30):
    """Find gaps in service based on needs vs completion"""
    since = get_utc_date_range_for_local_period(period_days)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$unwind": "$possible_needs"},
        {"$group": {
            "_id": "$possible_needs",
            "total_requests": {"$sum": 1},
            "completed": {
                "$sum": {"$cond": [{"$eq": ["$payment_status", 1]}, 1, 0]}
            }
        }},
        {"$addFields": {
            "fulfillment_rate": {
                "$multiply": [
                    {"$divide": ["$completed", "$total_requests"]},
                    100
                ]
            }
        }},
        {"$sort": {"fulfillment_rate": 1}}
    ]
    return list(ai_insight.aggregate(pipeline))