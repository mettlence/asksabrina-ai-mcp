import requests
from pymongo import MongoClient
from datetime import datetime
import time
from config import settings
import logging
import certifi

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
client = MongoClient(settings.MONGODB_URI, tlsCAFile=certifi.where())
db = client[settings.MONGODB_DB_NAME]
orders = db["orders"]
ai_insight = db["ai_insight"]

# ClickBank API setup
CLICKBANK_API_URL = "https://api.clickbank.com/rest/1.3/orders"
CLICKBANK_API_KEY = "API-LLCNNI7GUQ4Y14VWWI5KVH4AJUQOFEK56MW1"

def get_clickbank_data(clickbank_order_id):
    """Fetch country, amount and accountAmount from ClickBank API"""
    try:
        response = requests.get(
            f"{CLICKBANK_API_URL}/{clickbank_order_id}",
            headers={
                "Authorization": CLICKBANK_API_KEY,
                "Accept": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            order_data = data.get("orderData")
            
            if isinstance(order_data, dict):
                return {
                    "country": order_data.get("country"),
                    "amount": order_data.get("amount"),
                    "accountAmount": order_data.get("accountAmount")
                }
            elif isinstance(order_data, list) and len(order_data) > 0:
                return {
                    "country": order_data[0].get("country"),
                    "amount": order_data[0].get("amount"),
                    "accountAmount": order_data[0].get("accountAmount")
                }
        else:
            logger.warning(f"API Error {clickbank_order_id}: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Exception {clickbank_order_id}: {e}")
        return None

def backfill_clickbank_data():
    """Backfill clickbank data (country and prices) to ai_insight - only for missing data"""
    
    # Find paid orders
    paid_orders = list(orders.find({"paymentStatus": 1}))
    logger.info(f"📊 Found {len(paid_orders)} paid orders")
    
    updated = 0
    failed = 0
    skipped = 0
    
    for order in paid_orders:
        order_id = order.get("_id")
        clickbank_order_id = order.get("orderIdClickBank")
        
        if not clickbank_order_id:
            skipped += 1
            continue
        
        # Check if ai_insight already has complete clickbank data
        existing_insight = ai_insight.find_one(
            {"source_id": str(order_id)},
            {
                "customer_info.country": 1,
                "clickbank_order_id": 1,
                "clickbank_amount": 1,
                "clickbank_account_amount": 1
            }
        )
        
        if not existing_insight:
            logger.warning(f"No ai_insight found for order {order_id}")
            skipped += 1
            continue
        
        # Check if all clickbank data already exists
        has_country = existing_insight.get("customer_info", {}).get("country")
        has_order_id = existing_insight.get("clickbank_order_id")
        has_amount = existing_insight.get("clickbank_amount")
        has_account_amount = existing_insight.get("clickbank_account_amount")
        
        if has_country and has_order_id and has_amount and has_account_amount:
            skipped += 1
            continue
        
        # Fetch from ClickBank API
        cb_data = get_clickbank_data(clickbank_order_id)
        
        if not cb_data:
            failed += 1
            continue
        
        # Prepare update - only set fields that are missing
        update_fields = {
            "clickbank_order_id": clickbank_order_id,
        }
        
        if not has_country and cb_data.get("country"):
            update_fields["customer_info.country"] = cb_data["country"]
        
        if not has_amount and cb_data.get("amount"):
            update_fields["clickbank_amount"] = float(cb_data["amount"])
        
        if not has_account_amount and cb_data.get("accountAmount"):
            update_fields["clickbank_account_amount"] = float(cb_data["accountAmount"])
        
        # Remove old field name if exists
        unset_fields = {}
        if existing_insight.get("clickbankOrderId"):
            unset_fields["clickbankOrderId"] = ""
        
        update_query = {"$set": update_fields}
        if unset_fields:
            update_query["$unset"] = unset_fields
        
        result = ai_insight.update_one(
            {"_id": existing_insight["_id"]},
            update_query
        )
        
        if result.modified_count > 0:
            updated += 1
            logger.info(f"✅ Updated {order_id}: {cb_data.get('country', 'N/A')}, ${cb_data.get('amount', 'N/A')} (account: ${cb_data.get('accountAmount', 'N/A')})")
        
        time.sleep(0.5)
    
    logger.info(f"\n🎉 Complete! Updated: {updated}, Failed: {failed}, Skipped: {skipped} (already complete)")

if __name__ == "__main__":
    logger.info("🚀 Starting clickbank data backfill...")
    backfill_clickbank_data()