from typing import List, Dict, Any, Tuple, Optional
from src.tools import customer_insights, topic_analysis
from src.tools import emotional_insights, revenue_metrics, customer_needs
from src.tools import sentiment_analysis
from src.tools import country_analytics
from src.services.analyzer import summarize_data
from src.services.hybrid_intent_detector import HybridIntentDetector
from src.models.conversation import Message
from src.mcp.multi_step_agent import MultiStepAgent
from src.mcp.agentic_handler import AgenticHandler

intent_detector = HybridIntentDetector()
multi_step_agent = MultiStepAgent()
agentic_handler = AgenticHandler()

def handle_question(question: str, history: Optional[List[Message]] = None, use_agentic: bool = False) -> Tuple[str, Dict[str, Any]]:
    """Main handler for marketing analytics questions with conversation context"""
    
    # Agentic mode if enabled
    if use_agentic:
        return agentic_handler.handle_question_agentic(question, history)
    
    # Extract context from conversation history
    context_info = _extract_conversation_context(history) if history else {}

    # Check multi step query
    if multi_step_agent.detect_multi_step_query(question):
        # Extract params from question
        default_params = intent_detector.extract_parameters(question, context_info)
        
        # Try multi-step execution
        answer, metadata = multi_step_agent.handle_complex_query(question, default_params)
        
        if answer:  # Multi-step succeeded
            return answer, metadata
        # If failed, fall through to single-step
    
    # Detect intent with hybrid approach
    intent, confidence, detection_method = intent_detector.detect(question, context_info)
    params = intent_detector.extract_parameters(question, context_info)
    
    # If low confidence, try agentic as fallback
    if confidence < 0.5:
        print("⚠️ Low confidence, trying agentic fallback...")
        return agentic_handler.handle_question_agentic(question, history)
    
    # Route to appropriate tool
    try:
        data = None
        context = ""

        if intent == "context_followup" and context_info.get("last_intent"):
            intent = context_info["last_intent"]
            params = {**context_info.get("last_params", {}), **params}
        
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

        # Country Analytics
        elif intent == "revenue_by_country":
            data = country_analytics.get_revenue_by_country(params.get("period_days", 30), params.get("limit", 20))
            context = "revenue breakdown by customer country"

        elif intent == "top_countries_sales":
            data = country_analytics.get_top_countries_by_sales(params.get("period_days", 30), params.get("limit", 10))
            context = "top countries ranked by number of sales"

        elif intent == "country_performance":
            data = country_analytics.get_country_performance_comparison(params.get("period_days", 30))
            context = "country performance comparison with conversion rates"

        elif intent == "country_growth":
            data = country_analytics.get_country_growth_trends(params.get("period_days", 30), params.get("period_days", 30))
            context = "country growth trends comparing current vs previous period"

        elif intent == "country_ltv":
            data = country_analytics.get_country_customer_lifetime_value(params.get("period_days", 30), params.get("limit", 20))
            context = "average customer lifetime value by country"

        elif intent == "country_summary":
            data = country_analytics.get_country_distribution_summary(params.get("period_days", 30))
            context = "overall geographic distribution summary"
        
        elif intent == "keywords":
            data = sentiment_analysis.get_keyword_frequency(
                params.get("period_days", 30),
                params.get("limit", 20)
            )
            context = "keyword frequency analysis"
        
        if data is not None:
            answer = summarize_data(data, context, question, history)
            
            # Return answer with metadata
            metadata = {
                "intent": intent,
                "params": params,
                "confidence": confidence,
                "detection_method": detection_method,
                "data_type": context,
                "data_summary": _summarize_data_for_context(data)
            }
            return answer, metadata
        
        return (
            "I couldn't process that query. Please try rephrasing.",
            {
                "intent": intent, 
                "confidence": confidence,
                "detection_method": detection_method
            }
        )
    
    except Exception as e:
        return (
            f"Error processing query: {str(e)}",
            {"intent": intent, "error": str(e)}
        )
    
def _extract_conversation_context(history: List[Message]) -> Dict[str, Any]:
    """Extract rich context from conversation history"""
    if not history:
        return {}
    
    # Get last assistant response with metadata
    last_assistant = next(
        (m for m in reversed(history) if m.role == "assistant"),
        None
    )
    
    context = {}
    if last_assistant and last_assistant.metadata:
        context["last_intent"] = last_assistant.metadata.get("intent")
        context["last_params"] = last_assistant.metadata.get("params", {})
        context["last_data_type"] = last_assistant.metadata.get("data_type")
        context["last_data_summary"] = last_assistant.metadata.get("data_summary")
        context["last_confidence"] = last_assistant.metadata.get("confidence", 0)
    
    # Get last few user questions for pattern detection
    recent_questions = [
        m.content for m in reversed(history) 
        if m.role == "user"
    ][:3]
    context["recent_questions"] = recent_questions
    
    # Detect conversation patterns
    context["conversation_length"] = len([m for m in history if m.role == "user"])
    
    # Check if user is refining/drilling down
    if len(recent_questions) >= 2:
        current = recent_questions[0].lower()
        previous = recent_questions[1].lower()
        
        # Detect refinement patterns
        if any(word in current for word in ["what about", "how about", "also", "and"]):
            context["is_refinement"] = True
        
        # Detect comparison patterns
        if any(word in current for word in ["compare", "vs", "versus", "difference"]):
            context["is_comparison"] = True
    
    return context


def _summarize_data_for_context(data: Any) -> Dict[str, Any]:
    """Create lightweight summary of data for context storage"""
    if isinstance(data, dict):
        return {
            "type": "dict",
            "keys": list(data.keys())[:5],  # First 5 keys
            "size": len(data)
        }
    elif isinstance(data, list):
        return {
            "type": "list",
            "length": len(data),
            "sample": data[0] if data else None
        }
    else:
        return {"type": str(type(data))}