from datetime import datetime, timedelta
from src.db.mongo import ai_insight

def get_payment_success_rate(period_days=30):
    """Calculate payment completion rates"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"reference_date": {"$gte": since}}},
        {"$group": {
            "_id": "$payment_status",
            "count": {"$sum": 1},
            "total_value": {"$sum": "$total_price"}
        }}
    ]
    results = list(ai_insight.aggregate(pipeline))
    
    summary = {
        "paid": {"count": 0, "revenue": 0},
        "unpaid": {"count": 0, "lost_revenue": 0},
        "success_rate": 0
    }
    
    total_orders = 0
    for r in results:
        total_orders += r["count"]
        if r["_id"] == 1:  # Paid
            summary["paid"]["count"] = r["count"]
            summary["paid"]["revenue"] = r["total_value"]
        else:  # Unpaid (0 or None)
            summary["unpaid"]["count"] = r["count"]
            summary["unpaid"]["lost_revenue"] = r["total_value"]
    
    if total_orders > 0:
        summary["success_rate"] = round(
            (summary["paid"]["count"] / total_orders) * 100, 2
        )
    
    return summary


def get_revenue_trends(period_days=30, group_by="day"):
    """Revenue trends over time"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    date_format = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%U",
        "month": "%Y-%m"
    }.get(group_by, "%Y-%m-%d")
    
    pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1  # Only paid orders
        }},
        {"$group": {
            "_id": {"$dateToString": {"format": date_format, "date": "$reference_date"}},
            "revenue": {"$sum": "$total_price"},
            "orders": {"$sum": 1},
            "avg_order_value": {"$avg": "$total_price"}
        }},
        {"$sort": {"_id": 1}}
    ]
    return list(ai_insight.aggregate(pipeline))


def get_product_performance(period_days=30):
    """Best performing products"""
    since = (datetime.now() - timedelta(days=period_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1  # Only paid orders
        }},
        {"$group": {
            "_id": "$product_id",
            "total_revenue": {"$sum": "$total_price"},
            "order_count": {"$sum": 1},
            "avg_price": {"$avg": "$total_price"}
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": 10}
    ]
    return list(ai_insight.aggregate(pipeline))