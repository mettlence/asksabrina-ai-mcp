from datetime import datetime, timedelta
from src.db.mongo import ai_insight
from typing import Dict, List, Any

def get_customer_segments(period_days=30):
    """Segment customers by value and behavior"""
    since = datetime.utcnow() - timedelta(days=period_days)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$group": {
            "_id": "$customer_id",
            "total_orders": {"$sum": 1},
            "total_spent": {"$sum": "$total_price"},
            "avg_order_value": {"$avg": "$total_price"},
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
        {"$sort": {"total_spent": -1}}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_customer_lifetime_value(customer_id=None, top_n=20):
    """Get CLV for specific customer or top N customers"""
    match_stage = {"customer_id": {"$ne": None}}
    if customer_id:
        match_stage["customer_id"] = customer_id
    
    pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$customer_id",
            "total_orders": {"$sum": 1},
            "total_revenue": {"$sum": "$total_price"},
            "avg_order_value": {"$avg": "$total_price"},
            "first_order": {"$min": "$created_at"},
            "last_order": {"$max": "$created_at"}
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": top_n if not customer_id else 1}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_repeat_customers(period_days=30):
    """Identify loyal vs one-time customers"""
    since = datetime.utcnow() - timedelta(days=period_days)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}, "customer_id": {"$ne": None}}},
        {"$group": {
            "_id": "$customer_id",
            "order_count": {"$sum": 1}
        }},
        {"$group": {
            "_id": {"$cond": [{"$gt": ["$order_count", 1]}, "repeat", "one_time"]},
            "customer_count": {"$sum": 1},
            "customers": {"$push": "$_id"}
        }}
    ]
    results = list(ai_insight.aggregate(pipeline))
    
    summary = {"repeat": 0, "one_time": 0, "repeat_rate": 0}
    for r in results:
        summary[r["_id"]] = r["customer_count"]
    
    total = summary["repeat"] + summary["one_time"]
    if total > 0:
        summary["repeat_rate"] = round((summary["repeat"] / total) * 100, 2)
    
    return summary


def get_payment_time_analysis(period_days=30):
    """Analyze time between order creation and payment"""
    since = datetime.utcnow() - timedelta(days=period_days)
    pipeline = [
        {"$match": {
            "created_at": {"$gte": since},
            "payment_status": 1,
            "payment_date": {"$exists": True}
        }},
        {"$addFields": {
            "payment_duration_hours": {
                "$divide": [
                    {"$subtract": ["$payment_date", "$created_at"]},
                    3600000  # Convert milliseconds to hours
                ]
            }
        }},
        {"$group": {
            "_id": None,
            "avg_payment_time_hours": {"$avg": "$payment_duration_hours"},
            "min_payment_time_hours": {"$min": "$payment_duration_hours"},
            "max_payment_time_hours": {"$max": "$payment_duration_hours"},
            "total_paid_orders": {"$sum": 1},
            "durations": {"$push": "$payment_duration_hours"}
        }}
    ]
    results = list(ai_insight.aggregate(pipeline))
    
    if not results:
        return {"message": "No paid orders found in this period"}
    
    data = results[0]
    durations = sorted(data.get("durations", []))
    
    # Calculate median
    median = 0
    if durations:
        mid = len(durations) // 2
        median = durations[mid] if len(durations) % 2 != 0 else (durations[mid-1] + durations[mid]) / 2
    
    return {
        "avg_payment_time_hours": round(data.get("avg_payment_time_hours", 0), 2),
        "median_payment_time_hours": round(median, 2),
        "min_payment_time_hours": round(data.get("min_payment_time_hours", 0), 2),
        "max_payment_time_hours": round(data.get("max_payment_time_hours", 0), 2),
        "total_paid_orders": data.get("total_paid_orders", 0)
    }


def get_fast_vs_slow_payers(period_days=30, threshold_hours=24):
    """Segment customers by payment speed"""
    since = datetime.utcnow() - timedelta(days=period_days)
    pipeline = [
        {"$match": {
            "created_at": {"$gte": since},
            "payment_status": 1,
            "payment_date": {"$exists": True}
        }},
        {"$addFields": {
            "payment_duration_hours": {
                "$divide": [
                    {"$subtract": ["$payment_date", "$created_at"]},
                    3600000
                ]
            }
        }},
        {"$group": {
            "_id": {
                "$cond": [
                    {"$lte": ["$payment_duration_hours", threshold_hours]},
                    "fast_payers",
                    "slow_payers"
                ]
            },
            "count": {"$sum": 1},
            "avg_payment_time": {"$avg": "$payment_duration_hours"},
            "total_revenue": {"$sum": "$total_price"}
        }}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_abandoned_carts(hours_threshold=48):
    """Find unpaid orders older than threshold (potential abandoned carts)"""
    cutoff = datetime.utcnow() - timedelta(hours=hours_threshold)
    pipeline = [
        {"$match": {
            "payment_status": 0,
            "created_at": {"$lte": cutoff}
        }},
        {"$group": {
            "_id": "$customer_id",
            "abandoned_orders": {"$sum": 1},
            "total_abandoned_value": {"$sum": "$total_price"},
            "topics": {"$addToSet": "$topics"},
            "emotions": {"$addToSet": "$emotional_tone"},
            "last_abandoned": {"$max": "$created_at"}
        }},
        {"$sort": {"total_abandoned_value": -1}},
        {"$limit": 50}
    ]
    return list(ai_insight.aggregate(pipeline))