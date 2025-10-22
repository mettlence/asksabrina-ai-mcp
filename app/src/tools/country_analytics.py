from datetime import datetime, timedelta
from src.db.mongo import ai_insight
from src.config import settings
from src.utils.date import get_utc_date_range_for_local_period, get_local_date_projection

def get_revenue_by_country(period_days=30, limit=20):
    """
    Analyze revenue breakdown by customer country.
    Shows which countries generate the most revenue.
    """
    since = get_utc_date_range_for_local_period(period_days)
    
    pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1,
            "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
        }},
        {"$group": {
            "_id": "$customer_info.country",
            "total_revenue": {"$sum": "$clickbank_amount"},
            "total_orders": {"$sum": 1},
            "avg_order_value": {"$avg": "$clickbank_amount"},
            "unique_customers": {"$addToSet": "$customer_id"}
        }},
        {"$addFields": {
            "customer_count": {"$size": "$unique_customers"}
        }},
        {"$project": {
            "country": "$_id",
            "total_revenue": 1,
            "total_orders": 1,
            "avg_order_value": {"$round": ["$avg_order_value", 2]},
            "customer_count": 1,
            "_id": 0
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": limit}
    ]
    
    results = list(ai_insight.aggregate(pipeline))
    
    # Calculate totals and percentages
    total_revenue = sum(r["total_revenue"] for r in results)
    total_orders = sum(r["total_orders"] for r in results)
    
    for r in results:
        r["revenue_percentage"] = round((r["total_revenue"] / total_revenue * 100), 2) if total_revenue > 0 else 0
        r["order_percentage"] = round((r["total_orders"] / total_orders * 100), 2) if total_orders > 0 else 0
    
    return {
        "countries": results,
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "countries_count": len(results),
        "period_days": period_days
    }


def get_top_countries_by_sales(period_days=30, limit=10):
    """
    Rank countries by number of sales/orders.
    Shows which countries have the most customers.
    """
    since = get_utc_date_range_for_local_period(period_days)
    
    pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1,
            "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
        }},
        {"$group": {
            "_id": "$customer_info.country",
            "total_sales": {"$sum": 1},
            "total_revenue": {"$sum": "$clickbank_amount"},
            "unique_customers": {"$addToSet": "$customer_id"}
        }},
        {"$addFields": {
            "customer_count": {"$size": "$unique_customers"}
        }},
        {"$project": {
            "country": "$_id",
            "total_sales": 1,
            "total_revenue": {"$round": ["$total_revenue", 2]},
            "customer_count": 1,
            "avg_orders_per_customer": {
                "$round": [{"$divide": ["$total_sales", "$customer_count"]}, 2]
            },
            "_id": 0
        }},
        {"$sort": {"total_sales": -1}},
        {"$limit": limit}
    ]
    
    return list(ai_insight.aggregate(pipeline))


def get_country_performance_comparison(period_days=30):
    """
    Compare country performance metrics.
    Shows countries with best conversion rates and AOV.
    """
    since = get_utc_date_range_for_local_period(period_days)
    
    pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
        }},
        {"$group": {
            "_id": {
                "country": "$customer_info.country",
                "payment_status": "$payment_status"
            },
            "count": {"$sum": 1},
            "revenue": {"$sum": "$clickbank_amount"}
        }},
        {"$group": {
            "_id": "$_id.country",
            "total_orders": {"$sum": "$count"},
            "paid_orders": {
                "$sum": {
                    "$cond": [{"$eq": ["$_id.payment_status", 1]}, "$count", 0]
                }
            },
            "total_revenue": {
                "$sum": {
                    "$cond": [{"$eq": ["$_id.payment_status", 1]}, "$revenue", 0]
                }
            }
        }},
        {"$addFields": {
            "conversion_rate": {
                "$round": [
                    {"$multiply": [
                        {"$divide": ["$paid_orders", "$total_orders"]},
                        100
                    ]},
                    2
                ]
            },
            "avg_order_value": {
                "$round": [
                    {"$cond": [
                        {"$gt": ["$paid_orders", 0]},
                        {"$divide": ["$total_revenue", "$paid_orders"]},
                        0
                    ]},
                    2
                ]
            }
        }},
        {"$project": {
            "country": "$_id",
            "total_orders": 1,
            "paid_orders": 1,
            "conversion_rate": 1,
            "total_revenue": {"$round": ["$total_revenue", 2]},
            "avg_order_value": 1,
            "_id": 0
        }},
        {"$sort": {"conversion_rate": -1}}
    ]
    
    return list(ai_insight.aggregate(pipeline))


def get_country_growth_trends(period_days=30, comparison_days=30):
    """
    Compare country performance current period vs previous period.
    Shows which countries are growing or declining.
    """
    current_start = get_utc_date_range_for_local_period(period_days)
    previous_start = get_utc_date_range_for_local_period(period_days + comparison_days)
    previous_end = current_start
    
    # Current period
    current_pipeline = [
        {"$match": {
            "reference_date": {"$gte": current_start},
            "payment_status": 1,
            "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
        }},
        {"$group": {
            "_id": "$customer_info.country",
            "current_revenue": {"$sum": "$clickbank_amount"},
            "current_orders": {"$sum": 1}
        }}
    ]
    
    # Previous period
    previous_pipeline = [
        {"$match": {
            "reference_date": {"$gte": previous_start, "$lt": previous_end},
            "payment_status": 1,
            "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
        }},
        {"$group": {
            "_id": "$customer_info.country",
            "previous_revenue": {"$sum": "$clickbank_amount"},
            "previous_orders": {"$sum": 1}
        }}
    ]
    
    current_data = {r["_id"]: r for r in ai_insight.aggregate(current_pipeline)}
    previous_data = {r["_id"]: r for r in ai_insight.aggregate(previous_pipeline)}
    
    # Combine and calculate growth
    all_countries = set(current_data.keys()) | set(previous_data.keys())
    results = []
    
    for country in all_countries:
        current = current_data.get(country, {"current_revenue": 0, "current_orders": 0})
        previous = previous_data.get(country, {"previous_revenue": 0, "previous_orders": 0})
        
        revenue_growth = 0
        if previous.get("previous_revenue", 0) > 0:
            revenue_growth = round(
                ((current.get("current_revenue", 0) - previous["previous_revenue"]) / 
                 previous["previous_revenue"]) * 100,
                2
            )
        elif current.get("current_revenue", 0) > 0:
            revenue_growth = 100  # New country
        
        order_growth = 0
        if previous.get("previous_orders", 0) > 0:
            order_growth = round(
                ((current.get("current_orders", 0) - previous["previous_orders"]) / 
                 previous["previous_orders"]) * 100,
                2
            )
        elif current.get("current_orders", 0) > 0:
            order_growth = 100
        
        results.append({
            "country": country,
            "current_revenue": round(current.get("current_revenue", 0), 2),
            "previous_revenue": round(previous.get("previous_revenue", 0), 2),
            "revenue_growth_percent": revenue_growth,
            "current_orders": current.get("current_orders", 0),
            "previous_orders": previous.get("previous_orders", 0),
            "order_growth_percent": order_growth
        })
    
    # Sort by current revenue
    results.sort(key=lambda x: x["current_revenue"], reverse=True)
    
    return {
        "comparison": results,
        "current_period_days": period_days,
        "previous_period_days": comparison_days
    }


def get_country_revenue_over_time(country_code=None, period_days=30, group_by="day"):
    """
    Track revenue trends for specific country or all countries over time.
    """
    since = get_utc_date_range_for_local_period(period_days)
    
    date_format = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%U",
        "month": "%Y-%m"
    }.get(group_by, "%Y-%m-%d")
    
    match_stage = {
        "reference_date": {"$gte": since},
        "payment_status": 1,
        "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
    }
    
    # Filter by specific country if provided
    if country_code:
        match_stage["customer_info.country"] = country_code
    
    pipeline = [
        {"$match": match_stage},
        get_local_date_projection("reference_date"),
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": date_format, "date": "$local_date"}},
                "country": "$customer_info.country"
            },
            "revenue": {"$sum": "$clickbank_amount"},
            "orders": {"$sum": 1}
        }},
        {"$project": {
            "date": "$_id.date",
            "country": "$_id.country",
            "revenue": {"$round": ["$revenue", 2]},
            "orders": 1,
            "_id": 0
        }},
        {"$sort": {"date": 1, "revenue": -1}}
    ]
    
    return list(ai_insight.aggregate(pipeline))


def get_country_customer_lifetime_value(period_days=365, limit=20):
    """
    Calculate average customer lifetime value by country.
    Shows which countries have the most valuable customers.
    """
    since = get_utc_date_range_for_local_period(period_days)
    
    pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1,
            "customer_id": {"$ne": None},
            "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
        }},
        {"$group": {
            "_id": {
                "country": "$customer_info.country",
                "customer_id": "$customer_id"
            },
            "customer_lifetime_revenue": {"$sum": "$clickbank_amount"},
            "customer_orders": {"$sum": 1}
        }},
        {"$group": {
            "_id": "$_id.country",
            "total_customers": {"$sum": 1},
            "avg_customer_ltv": {"$avg": "$customer_lifetime_revenue"},
            "avg_orders_per_customer": {"$avg": "$customer_orders"},
            "total_revenue": {"$sum": "$customer_lifetime_revenue"}
        }},
        {"$project": {
            "country": "$_id",
            "total_customers": 1,
            "avg_customer_ltv": {"$round": ["$avg_customer_ltv", 2]},
            "avg_orders_per_customer": {"$round": ["$avg_orders_per_customer", 2]},
            "total_revenue": {"$round": ["$total_revenue", 2]},
            "_id": 0
        }},
        {"$sort": {"avg_customer_ltv": -1}},
        {"$limit": limit}
    ]
    
    return list(ai_insight.aggregate(pipeline))


def get_country_distribution_summary(period_days=30):
    """
    Overall summary of geographic distribution.
    Dashboard overview of all country metrics.
    """
    since = get_utc_date_range_for_local_period(period_days)
    
    # Total metrics
    total_pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1
        }},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$clickbank_amount"},
            "total_orders": {"$sum": 1}
        }}
    ]
    
    total_data = list(ai_insight.aggregate(total_pipeline))
    total_revenue = total_data[0]["total_revenue"] if total_data else 0
    total_orders = total_data[0]["total_orders"] if total_data else 0
    
    # Country metrics
    country_pipeline = [
        {"$match": {
            "reference_date": {"$gte": since},
            "payment_status": 1,
            "customer_info.country": {"$exists": True, "$ne": None, "$ne": ""}
        }},
        {"$group": {
            "_id": "$customer_info.country",
            "revenue": {"$sum": "$clickbank_amount"},
            "orders": {"$sum": 1}
        }},
        {"$sort": {"revenue": -1}}
    ]
    
    country_data = list(ai_insight.aggregate(country_pipeline))
    
    # Top 5 countries
    top_countries = []
    for c in country_data[:5]:
        top_countries.append({
            "country": c["_id"],
            "revenue": round(c["revenue"], 2),
            "orders": c["orders"],
            "revenue_percentage": round((c["revenue"] / total_revenue * 100), 2) if total_revenue > 0 else 0
        })
    
    # Countries count
    total_countries = len(country_data)
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_countries": total_countries,
        "top_5_countries": top_countries,
        "top_5_revenue_percentage": sum(c["revenue_percentage"] for c in top_countries),
        "period_days": period_days
    }