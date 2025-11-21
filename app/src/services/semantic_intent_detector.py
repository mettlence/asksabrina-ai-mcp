"""
Semantic Intent Detection using OpenAI Embeddings
Handles queries that don't match rigid patterns through similarity matching
"""

from openai import OpenAI
import numpy as np
from typing import Dict, Tuple, Optional, List
import json
from pathlib import Path
from src.config import settings

class SemanticIntentDetector:
    """Detect intent using semantic similarity with embeddings"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.intent_embeddings = None
        self.cache_file = Path("app/src/services/intent_embeddings_cache.json")
        
        # Rich intent descriptions with multiple phrasings
        self.intent_descriptions = {
            # Customer Analytics
            "customer_segments": """
                Group or categorize customers by their behavior, value, or characteristics.
                Segment customers into different types or groups.
                Show me different customer categories or classifications.
                How can we divide our customers into segments?
            """,
            
            "customer_value": """
                Show the most valuable customers by lifetime value or total spending.
                Who are our top customers, best customers, or highest value clients?
                Which customers spend the most or generate the most revenue?
                Customer lifetime value rankings or CLV analysis.
            """,
            
            "repeat_customers": """
                Identify loyal customers who make repeat purchases or return to buy again.
                Show customer retention rates or returning customer analysis.
                How many customers come back versus one-time buyers?
                Analyze customer loyalty and repeat purchase behavior.
            """,
            
            # Payment Analytics
            "payment_time": """
                How long does it take customers to complete payment after ordering?
                Average time from order creation to payment completion.
                Payment duration or time between order and payment.
                How fast do customers pay after placing orders?
            """,
            
            "fast_slow_payers": """
                Which customers pay quickly versus slowly?
                Segment customers by payment speed or payment velocity.
                Show fast payers and slow payers comparison.
                Analyze customer payment behavior and speed patterns.
            """,
            
            "abandoned_carts": """
                Which orders were abandoned or not completed?
                Show customers who didn't finish payment or left items unpaid.
                Incomplete orders or pending payment analysis.
                Cart abandonment rate and abandoned order details.
            """,
            
            "unpaid_orders_count": """
                How many orders are unpaid or pending payment?
                Total count of incomplete or unpaid transactions.
                Number of orders waiting for payment.
                Volume of unpaid orders and their total value.
            """,
            
            # Topic Analytics
            "trending_topics": """
                What are customers asking about most frequently?
                Show popular topics, hot topics, or trending questions.
                What themes or subjects are most common in customer inquiries?
                Top discussion topics or most mentioned themes.
            """,
            
            "topic_revenue": """
                Which topics or themes generate the most revenue or income?
                Show profitable topics or high-earning question categories.
                Revenue analysis by topic or theme performance.
                What subjects or topics drive the most sales?
            """,
            
            "topics_by_emotion": """
                What topics are anxious, happy, stressed, or worried customers asking about?
                Show topics filtered by customer emotional state or mood.
                What do customers with specific emotions talk about?
                Topic analysis for customers feeling a particular way.
            """,
            
            # Emotional Analytics
            "emotions": """
                What emotions or feelings are customers expressing?
                Show customer mood distribution or emotional tone breakdown.
                Are customers happy, sad, anxious, or stressed?
                Emotional sentiment analysis across customer interactions.
            """,
            
            "emotion_conversion": """
                Which emotions lead to completed purchases or conversions?
                Do happy or anxious customers convert better?
                Correlation between customer emotion and payment completion.
                How does emotional state impact conversion rates?
            """,
            
            "high_risk": """
                Which customers need support or are showing distress?
                Identify customers with negative emotions who may need help.
                Show at-risk customers or those expressing concern.
                Flag customers who might be struggling or need attention.
            """,
            
            # Revenue Analytics
            "revenue_trends": """
                Show revenue, sales, or income over time.
                What are our earnings trends daily, weekly, or monthly?
                Revenue growth patterns or sales performance over periods.
                Financial results, sales metrics, or income statistics.
                How is our performance or how are we doing financially?
            """,
            
            "payment_rate": """
                What percentage of orders result in completed payments?
                Show conversion rate, success rate, or completion rate.
                How many customers actually pay versus abandon?
                Payment success metrics or conversion statistics.
            """,
            
            "product_performance": """
                Which products sell best or generate most revenue?
                Show top-selling products or best performers.
                Product revenue rankings or sales by product.
                What are our most successful or profitable products?
            """,
            
            # Customer Needs
            "customer_needs": """
                What are customers looking for or seeking?
                Show customer needs, wants, or requirements.
                What do customers need help with or want to achieve?
                Customer intent analysis or goal identification.
            """,
            
            "unmet_needs": """
                What customer needs aren't being fulfilled?
                Show service gaps or unfulfilled requirements.
                Where are we failing to meet customer expectations?
                Missing services or unaddressed customer needs.
            """,
            
            # Sentiment Analytics
            "sentiment_overview": """
                Overall customer satisfaction or happiness levels.
                Are customers generally positive or negative?
                Customer sentiment distribution or feedback analysis.
                How do customers feel about us overall?
            """,
            
            "keywords": """
                What words or terms do customers use most frequently?
                Show popular keywords, common phrases, or frequent mentions.
                Top words or most-used terminology in customer communications.
                Word frequency analysis or keyword trends.
            """,
            
            # Age Analytics
            "purchases_by_age": """
                Show purchases or revenue broken down by customer age.
                Which age groups buy most or spend most?
                Customer demographics by age bracket or generation.
                Sales analysis by age range or age demographics.
            """,
            
            # Country Analytics
            "revenue_by_country": """
                Show revenue, sales, or income by country or location.
                Which countries or regions generate most revenue?
                Geographic revenue breakdown or sales by location.
                Earnings per country or international sales analysis.
            """,
            
            "top_countries_sales": """
                Which countries have the most customers or orders?
                Show top countries by number of sales or transactions.
                Country rankings by order volume or customer count.
                Best-performing countries or regions by sales volume.
            """,
            
            "country_performance": """
                Compare performance metrics across different countries.
                Show country-level conversion rates or success metrics.
                How do different countries or regions perform?
                Geographic performance comparison or country benchmarking.
            """,
            
            "country_growth": """
                Which countries are growing or declining?
                Show country growth trends or changes over time.
                Geographic expansion or contraction analysis.
                How are different countries trending?
            """,
            
            "country_ltv": """
                Customer lifetime value by country or geographic location.
                Which countries have the most valuable customers?
                Average customer worth by country or region.
                Geographic CLV analysis or country value rankings.
            """,
            
            "country_summary": """
                Overall geographic distribution or location overview.
                Show all countries we operate in or serve.
                Complete country breakdown or geographic summary.
                Dashboard view of all location metrics.
            """,
        }
        
        # Load or generate embeddings
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Load cached embeddings or generate new ones"""
        
        # Try loading from cache
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    
                # Convert lists back to numpy arrays
                self.intent_embeddings = {
                    intent: np.array(embedding) 
                    for intent, embedding in cache.items()
                }
                print(f"✅ Loaded {len(self.intent_embeddings)} intent embeddings from cache")
                return
            except Exception as e:
                print(f"⚠️ Failed to load cache: {e}")
        
        # Generate new embeddings
        print("🔄 Generating intent embeddings...")
        self._generate_embeddings()
    
    def _generate_embeddings(self):
        """Generate embeddings for all intent descriptions"""
        self.intent_embeddings = {}
        
        for intent, description in self.intent_descriptions.items():
            # Clean up description (remove extra whitespace)
            clean_desc = " ".join(description.split())
            
            try:
                response = self.client.embeddings.create(
                    input=clean_desc,
                    model=settings.OPENAI_EMBEDDING_MODEL
                )
                embedding = np.array(response.data[0].embedding)
                self.intent_embeddings[intent] = embedding
                
            except Exception as e:
                print(f"❌ Failed to generate embedding for {intent}: {e}")
        
        # Save to cache
        self._save_cache()
        print(f"✅ Generated and cached {len(self.intent_embeddings)} intent embeddings")
    
    def _save_cache(self):
        """Save embeddings to cache file"""
        try:
            # Convert numpy arrays to lists for JSON serialization
            cache = {
                intent: embedding.tolist()
                for intent, embedding in self.intent_embeddings.items()
            }
            
            # Create directory if it doesn't exist
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
                
        except Exception as e:
            print(f"⚠️ Failed to save cache: {e}")
    
    def detect(self, question: str, context_info: Dict = None) -> Tuple[str, float]:
        """
        Detect intent using semantic similarity
        Returns: (intent_name, confidence_score)
        """
        
        if not self.intent_embeddings:
            print("⚠️ No embeddings available, falling back to pattern matching")
            return "unknown", 0.0
        
        try:
            # Generate embedding for the question
            response = self.client.embeddings.create(
                input=question,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            question_embedding = np.array(response.data[0].embedding)
            
            # Calculate cosine similarity with all intent embeddings
            similarities = {}
            for intent, intent_embedding in self.intent_embeddings.items():
                similarity = self._cosine_similarity(question_embedding, intent_embedding)
                similarities[intent] = similarity
            
            # Get best match
            best_intent = max(similarities, key=similarities.get)
            confidence = similarities[best_intent]
            
            # Apply confidence threshold
            if confidence < 0.65:
                return "unknown", confidence
            
            return best_intent, confidence
            
        except Exception as e:
            print(f"❌ Semantic detection error: {e}")
            return "unknown", 0.0
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_top_matches(self, question: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Get top N intent matches for debugging/analysis
        Returns: [(intent, confidence), ...]
        """
        
        if not self.intent_embeddings:
            return []
        
        try:
            response = self.client.embeddings.create(
                input=question,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            question_embedding = np.array(response.data[0].embedding)
            
            similarities = {
                intent: self._cosine_similarity(question_embedding, intent_embedding)
                for intent, intent_embedding in self.intent_embeddings.items()
            }
            
            # Sort by similarity
            sorted_matches = sorted(
                similarities.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return sorted_matches[:top_n]
            
        except Exception as e:
            print(f"❌ Error getting top matches: {e}")
            return []