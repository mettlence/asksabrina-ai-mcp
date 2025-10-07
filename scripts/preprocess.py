import os
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import MongoClient
from openai import OpenAI
from dotenv import load_dotenv
import json

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

DB_NAME = "asksabrina"
ORDERS_COLLECTION = "orders"
CUSTOMERS_COLLECTION = "customers"
TARGET_COLLECTION = "ai_insight"

LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "720"))

# -----------------------------
# MongoDB setup
# -----------------------------
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[DB_NAME]
orders_col = db[ORDERS_COLLECTION]
customers_col = db[CUSTOMERS_COLLECTION]
ai_insight = db[TARGET_COLLECTION]

# -----------------------------
# OpenAI client
# -----------------------------
openai = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------
# Get unprocessed orders
# -----------------------------
def get_unprocessed_orders():
    since = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
    processed_ids = (
        ai_insight.distinct("source_id") if TARGET_COLLECTION in db.list_collection_names() else []
    )
    cursor = orders_col.find({
        "createdAt": {"$gte": since},
        "_id": {"$nin": [ObjectId(x) for x in processed_ids]}
    })
    return cursor


# -----------------------------
# Process single order
# -----------------------------
def process_order(order):
    order_id = order.get("_id")
    customer_id = order.get("customerId")
    payment_status = order.get("paymentStatus", 0)

    # Fetch customer details
    customer = customers_col.find_one({"_id": customer_id}) if customer_id else None

    # Combine customer metadata
    customer_info = {
        "fullName": customer.get("fullName") if customer else None,
        "firstName": customer.get("firstName") if customer else None,
        "lastName": customer.get("lastName") if customer else None,
        "email": customer.get("email") if customer else None,
        "gender": customer.get("gender") if customer else None,
        "age": customer.get("age") if customer else None,
        "horoscope": customer.get("horoscope") if customer else None,
        "birthday": customer.get("birthday") if customer else None,
        "martialStatus": customer.get("martialStatus") if customer else None,
        "country": customer.get("country") if customer else None,
        "city": customer.get("city") if customer else None,
    }

    # Prepare question text
    questions = order.get("question", [])
    raw_text = " ".join(questions).strip()

    if not raw_text:
        print(f"Skipping order {order_id} — no question content.")
        return

    print(f"Processing order {order_id} (paymentStatus={payment_status})...")

    # 1. Generate embedding
    embedding_response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=raw_text
    )
    embedding = embedding_response.data[0].embedding

    # 2. AI insight generation
    insight_prompt = f"""
    Analyze the following tarot-related customer question and return structured marketing and product insights.

    Customer details:
    {customer_info}

    Questions:
    {raw_text}

    Respond in JSON with the following fields:
    - keywords: list of key terms from the question
    - topics: list of topics with {{name, confidence}}
    - sentiment: {{label: positive|neutral|negative, score: 0-1}}
    - emotional_tone: list of emotions with scores
    - insight_tags: suggested tags for marketing or segmentation
    - possible_needs: list of inferred customer needs or desires
    """

    completion = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise NLP analyst for customer insights."},
            {"role": "user", "content": insight_prompt}
        ],
        response_format={"type": "json_object"}
    )

    # Parse JSON response content manually
    raw_content = completion.choices[0].message.content
    try:
        insights = json.loads(raw_content)
    except json.JSONDecodeError:
        print("Warning: Could not parse JSON, storing raw string instead.")
        insights = {}


    # Build enriched record
    enriched_doc = {
        "source_id": str(order_id),
        "customer_id": str(customer_id) if customer_id else None,
        "order_id": order.get("orderId"),
        "created_at": order.get("createdAt"),
        "payment_status": payment_status,
        "product_id": str(order.get("productId")),
        "total_price": order.get("totalPrice"),
        "questions": questions,
        "raw_text": raw_text,
        "tarot_cards": order.get("tarotCards", []),
        "customer_info": customer_info,
        "embedding": embedding,
        "keywords": insights.get("keywords", []),
        "topics": insights.get("topics", []),
        "sentiment": insights.get("sentiment", {}),
        "emotional_tone": insights.get("emotional_tone", []),
        "insight_tags": insights.get("insight_tags", []),
        "possible_needs": insights.get("possible_needs", []),
        "processed_at": datetime.utcnow(),
        "embedding_model": "text-embedding-3-small",
        "pipeline_version": "v2.0",
    }

    ai_insight.update_one(
        {"source_id": str(order_id)},
        {"$set": enriched_doc},
        upsert=True
    )

    print(f"Processed order {order_id}")


# -----------------------------
# Main
# -----------------------------
def main():
    print("Starting AI preprocessing with customer context...")
    orders = list(get_unprocessed_orders())
    print(f"Found {len(orders)} new orders to process.")

    if not orders:
        print("No new data to process.")
        return

    for idx, order in enumerate(orders, start=1):
        try:
            print(f"[{idx}/{len(orders)}] Processing...")
            process_order(order)
        except Exception as e:
            print(f"Error processing order {order.get('_id')}: {e}")

    print("All insights generated successfully.")


if __name__ == "__main__":
    main()
