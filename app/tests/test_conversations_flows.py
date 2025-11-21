def test_basic_followup():
    """Test: Show trending topics → What about anxious customers?"""
    
    # First question
    question1 = "Show me trending topics this month"
    intent1, conf1 = intent_detector.detect(question1)
    assert intent1 == "trending_topics"
    
    # Context from first response
    context = {
        "last_intent": "trending_topics",
        "last_params": {"period_days": 30}
    }
    
    # Follow-up question
    question2 = "What about anxious customers?"
    intent2, conf2 = intent_detector.detect(question2, context)
    params2 = intent_detector.extract_parameters(question2, context)
    
    assert intent2 == "trending_topics"  # Same intent
    assert params2["emotion_filter"] == "anxious"  # New filter
    assert params2["period_days"] == 30  # Inherited


def test_breakdown_followup():
    """Test: Show revenue → Break it down by country"""
    
    context = {
        "last_intent": "revenue_trends",
        "last_params": {"period_days": 30}
    }
    
    question = "Break it down by country"
    intent, conf = intent_detector.detect(question, context)
    
    assert intent == "revenue_by_country"
    assert conf > 0.85


def test_comparison_followup():
    """Test: Show sales → Compare to last month"""
    
    context = {
        "last_intent": "revenue_trends",
        "last_params": {"period_days": 7}
    }
    
    question = "Compare to last month"
    intent, conf = intent_detector.detect(question, context)
    params = intent_detector.extract_parameters(question, context)
    
    assert intent == "revenue_trends"
    assert params["comparison_mode"] == True


def test_show_more():
    """Test: Show topics → Tell me more details"""
    
    context = {
        "last_intent": "trending_topics",
        "last_params": {"limit": 10}
    }
    
    question = "Tell me more details"
    intent, conf = intent_detector.detect(question, context)
    
    assert intent == "trending_topics"
    assert conf == 0.95  # High confidence for "show more"


def test_filter_refinement():
    """Test: Show countries → Only US and Canada"""
    
    context = {
        "last_intent": "top_countries_sales",
        "last_params": {"period_days": 30, "limit": 10}
    }
    
    question = "Only US and Canada"
    intent, conf = intent_detector.detect(question, context)
    params = intent_detector.extract_parameters(question, context)
    
    assert intent == "top_countries_sales"
    assert params["country_filter"] in ["US", "CA"]