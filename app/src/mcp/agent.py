from src.tools import customer_insights, topic_analysis
from src.tools import emotional_insights, revenue_metrics, customer_needs
from src.tools import sentiment_analysis
from src.services.analyzer import summarize_data
from src.services.intent_detector import IntentDetector

intent_detector = IntentDetector()

def handle_question(question: str):
    """Main handler for marketing analytics questions"""
    
    # Detect intent
    intent, confidence = intent_detector.detect(question)
    params = intent_detector.extract_parameters(question)
    
    if confidence < 0.5:
        return "I'm not sure what you're asking. Try questions like: 'Show me trending topics' or 'What are the top emotions this month?'"
    
    # Route to appropriate tool
    try:
        data = None
        context = ""
        
        if intent == "customer_segments":
            data = customer_insights.get_customer_segments(params.get("period_days", 30))
            context = "customer segmentation by value and behavior"
        
        elif intent == "customer_value":
            data = customer_insights.get_customer_lifetime_value(top_n=params.get("limit", 20))
            context = "customer lifetime value rankings"
        
        elif intent == "repeat_customers":
            data = customer_insights.get_repeat_customers(params.get("period_days", 30))
            context = "repeat vs one-time customer analysis"

        elif intent == "purchases_by_age":
            data = customer_insights.get_purchases_by_age_group(params.get("period_days", 30))
            context = "purchases and revenue breakdown by customer age groups"
        
        elif intent == "payment_time":
            data = customer_insights.get_payment_time_analysis(params.get("period_days", 30))
            context = "payment time analysis - time between order and payment"
        
        elif intent == "fast_slow_payers":
            data = customer_insights.get_fast_vs_slow_payers(
                params.get("period_days", 30),
                params.get("threshold_hours", 24)
            )
            context = "fast vs slow payers segmentation"
        
        elif intent == "abandoned_carts":
            data = customer_insights.get_abandoned_carts(params.get("hours_threshold", 48))
            context = "abandoned cart analysis - unpaid orders"

        elif intent == "unpaid_orders_count":
            data = customer_insights.get_unpaid_orders_count(params.get("period_days", 30))
            context = "total unpaid orders count and value"
        
        elif intent == "trending_topics":
            data = topic_analysis.get_trending_topics(
                params.get("period_days", 7),
                params.get("limit", 10)
            )
            context = "trending topics analysis"
        
        elif intent == "topic_revenue":
            data = topic_analysis.get_topic_revenue_correlation(params.get("period_days", 30))
            context = "topic revenue correlation"

        elif intent == "topics_by_emotion":
            emotion_filter = params.get("emotion_filter")
            data = topic_analysis.get_topics_by_emotion(emotion_filter, params.get("period_days", 30))
            emotion_text = f" from {emotion_filter} customers" if emotion_filter else ""
            context = f"topics{emotion_text} and their revenue performance"
        
        elif intent == "emotions":
            data = emotional_insights.get_emotion_distribution(params.get("period_days", 30))
            context = "emotional tone distribution"
        
        elif intent == "emotion_conversion":
            data = emotional_insights.get_emotion_conversion_rate(params.get("period_days", 30))
            context = "emotion to conversion correlation"
        
        elif intent == "high_risk":
            data = emotional_insights.get_high_risk_customers()
            context = "high-risk customers needing support"
        
        elif intent == "payment_rate":
            data = revenue_metrics.get_payment_success_rate(params.get("period_days", 30))
            context = "payment success rate analysis"
        
        elif intent == "revenue_trends":
            group_by = "day"
            if "week" in question.lower():
                group_by = "week"
            elif "month" in question.lower():
                group_by = "month"
            data = revenue_metrics.get_revenue_trends(params.get("period_days", 30), group_by)
            context = f"revenue trends by {group_by}"
        
        elif intent == "product_performance":
            data = revenue_metrics.get_product_performance(params.get("period_days", 30))
            context = "product performance metrics"
        
        elif intent == "customer_needs":
            data = customer_needs.get_customer_needs_distribution(params.get("period_days", 30))
            context = "customer needs distribution"
        
        elif intent == "unmet_needs":
            data = customer_needs.get_unmet_needs_analysis(params.get("period_days", 30))
            context = "unmet needs and service gaps"
        
        elif intent == "sentiment_overview":
            data = sentiment_analysis.get_sentiment_distribution(params.get("period_days", 30))
            context = "sentiment distribution overview"
        
        elif intent == "keywords":
            data = sentiment_analysis.get_keyword_frequency(
                params.get("period_days", 30),
                params.get("limit", 20)
            )
            context = "keyword frequency analysis"
        
        if data is not None:
            return summarize_data(data, context, question)
        
        return "I couldn't process that query. Please try rephrasing."
    
    except Exception as e:
        return f"Error processing query: {str(e)}"