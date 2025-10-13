from typing import Dict, List, Tuple

class IntentDetector:
    """Detect user intent from natural language queries"""
    
    INTENT_PATTERNS = {
        # Customer Analytics
        "customer_segments": ["segment", "customer group", "type of customer", "categorize customer"],
        "customer_value": ["clv", "lifetime value", "top customer", "best customer", "high value", "most valuable"],
        "repeat_customers": ["loyal", "repeat", "returning customer", "retention", "come back"],
        
        # Payment Time Analytics
        "payment_time": [
            "payment time", "time to pay", "how long to pay", "payment duration", 
            "order to payment", "time between order", "average payment time", "how fast pay"
        ],
        "fast_slow_payers": [
            "fast payer", "slow payer", "payment speed", "quick payment", 
            "who pays fast", "who pays slow", "payment velocity"
        ],
        "abandoned_carts": [
            "abandoned", "cart abandon", "didn't pay", 
            "incomplete order", "not paid", "pending payment", "waiting payment"
        ],
        "unpaid_orders_count": ["how many unpaid", "unpaid orders", "count unpaid", "total unpaid"],
        
        # Topic Analytics
        "trending_topics": ["trending", "popular topic", "what people ask", "common question", "hot topic"],
        "topic_revenue": ["topic revenue", "profitable topic", "which topic make", "topic performance", "topic income"],
        "topics_by_emotion": [
            "topic from", "topics from", "which topic", "what topic",
            "from anxious", "from happy", "from sad", "from stressed", 
            "from worried", "from confused", "from hopeful",
            "anxious customer topic", "happy customer topic"
        ],
        "question_patterns": ["question pattern", "common question", "what they ask", "question theme"],
        
        # Emotional Analytics
        "emotions": ["emotion", "feeling", "emotional", "mood"],
        "emotion_conversion": ["emotion conversion", "which emotion convert", "emotional impact", "emotion payment"],
        "high_risk": ["risk", "distress", "negative", "support", "worried customer", "need help"],
        
        # Revenue Analytics - ENHANCED
        "payment_rate": ["payment rate", "success rate", "conversion rate", "completion rate", "how many paid"],
        "revenue_trends": [
            "revenue trend", "sales over time", "daily revenue", "monthly revenue", "revenue growth",
            "all revenue", "total revenue", "total sales", "how much money", "total income",
            "revenue this", "revenue last", "sales this", "sales last", "money made"
        ],
        "product_performance": ["product performance", "best product", "top selling", "product revenue", "best seller"],
        
        # Customer Needs Analytics
        "customer_needs": ["need", "looking for", "customer want", "seeking", "what do they need"],
        "unmet_needs": ["gap", "unmet need", "unfulfilled", "missing service", "not satisfied"],
        
        # Sentiment Analytics - ENHANCED & SEPARATED
        "sentiment_overview": [
            "overall sentiment", "customer sentiment", "sentiment distribution",
            "are customers happy", "customer feedback", "satisfaction score",
            "happy or sad", "positive or negative"
        ],
        "sentiment_product": ["sentiment by product", "product sentiment", "which product happy"],
        "keywords": ["keyword", "common word", "popular term", "frequently mentioned", "top word"]
    }
    
    def detect(self, question: str) -> Tuple[str, float]:
        """
        Detect intent from question
        Returns: (intent_name, confidence_score)
        """
        question_lower = question.lower()
        
        # Check for emotion-specific patterns first (higher priority)
        emotion_words = ["anxious", "happy", "sad", "stressed", "worried", "confused", "hopeful", "angry", "calm"]
        has_emotion = any(emotion in question_lower for emotion in emotion_words)
        
        if has_emotion and any(word in question_lower for word in ["topic", "topics"]):
            return "topics_by_emotion", 0.95
        
        # Exact match - highest confidence
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in question_lower:
                    return intent, 0.95
        
        # Fuzzy matching for partial matches
        best_match = None
        best_score = 0
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                words = pattern.split()
                matches = sum(1 for word in words if word in question_lower)
                score = matches / len(words)
                
                if score > best_score and score >= 0.6:  # 60% word match
                    best_score = score
                    best_match = intent
        
        if best_match:
            return best_match, 0.7
        
        return "unknown", 0.0
    
    def extract_parameters(self, question: str) -> Dict:
        """Extract parameters like time period, limits, thresholds from question"""
        import re
        from datetime import datetime
        params = {}
        question_lower = question.lower()
        
        # Extract emotion filters from question
        emotion_keywords = {
            "anxious": ["anxious", "anxiety", "worried", "nervous"],
            "happy": ["happy", "joyful", "satisfied", "pleased"],
            "sad": ["sad", "unhappy", "disappointed", "down"],
            "stressed": ["stressed", "overwhelmed", "pressured"],
            "confused": ["confused", "uncertain", "unclear"],
            "hopeful": ["hopeful", "optimistic", "positive"],
            "angry": ["angry", "frustrated", "annoyed"],
            "calm": ["calm", "relaxed", "peaceful"]
        }
        
        detected_emotions = []
        for emotion, keywords in emotion_keywords.items():
            if any(kw in question_lower for kw in keywords):
                detected_emotions.append(emotion)
        
        if detected_emotions:
            params["emotion_filter"] = detected_emotions if len(detected_emotions) > 1 else detected_emotions[0]
        
        # Dynamic time period extraction (e.g., "last 20 days", "past 3 months")
        time_unit_multipliers = {
            "day": 1,
            "days": 1,
            "week": 7,
            "weeks": 7,
            "month": 30,
            "months": 30,
            "quarter": 90,
            "quarters": 90,
            "year": 365,
            "years": 365
        }
        
        # Pattern: "last/past N days/weeks/months/years"
        dynamic_pattern = r'(?:last|past|previous)\s+(\d+)\s+(day|days|week|weeks|month|months|quarter|quarters|year|years)'
        match = re.search(dynamic_pattern, question_lower)
        
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            params["period_days"] = number * time_unit_multipliers.get(unit, 1)
        else:
            # Special handling for "lifetime" or "all time"
            if any(phrase in question_lower for phrase in ["lifetime", "all time", "ever", "since beginning", "total history"]):
                params["period_days"] = 99999  # Very large number to capture all data
            # Special handling for "this year" - calculate days from Jan 1 to now
            elif "this year" in question_lower:
                start_of_year = datetime(datetime.utcnow().year, 1, 1)
                days_since_start = (datetime.utcnow() - start_of_year).days + 1
                params["period_days"] = days_since_start
            # Handle "last year" or "1 year"
            elif any(phrase in question_lower for phrase in ["last year", "past year", "in 1 year"]):
                params["period_days"] = 365
            # Fallback to static patterns
            else:
                time_patterns = {
                    "today": 1,
                    "yesterday": 1,
                    "this week": 7,
                    "last week": 7,
                    "this month": 30,
                    "last month": 30,
                    "last quarter": 90,
                    "this quarter": 90
                }
                
                for pattern, days in time_patterns.items():
                    if pattern in question_lower:
                        params["period_days"] = days
                        break
        
        # Extract limits (top N, show N, first N)
        limit_pattern = r'(?:top|first|best|show|give\s+me)\s+(\d+)'
        limit_match = re.search(limit_pattern, question_lower)
        
        if limit_match:
            params["limit"] = int(limit_match.group(1))
        
        # Extract time thresholds - support hours, minutes, seconds
        # Hours pattern
        hour_pattern = r'(\d+)\s+(?:hour|hours|hrs?)\s+threshold'
        hour_match = re.search(hour_pattern, question_lower)
        
        # Minutes pattern
        minute_pattern = r'(\d+)\s+(?:minute|minutes|mins?)\s+threshold'
        minute_match = re.search(minute_pattern, question_lower)
        
        # Seconds pattern  
        second_pattern = r'(\d+)\s+(?:second|seconds|secs?)\s+threshold'
        second_match = re.search(second_pattern, question_lower)
        
        if hour_match:
            hours = int(hour_match.group(1))
            if any(word in question_lower for word in ["abandon", "unpaid", "waiting"]):
                params["hours_threshold"] = hours
            elif any(word in question_lower for word in ["fast", "slow", "quick", "speed", "payer"]):
                params["threshold_hours"] = hours
        elif minute_match:
            minutes = int(minute_match.group(1))
            hours_equivalent = minutes / 60
            if any(word in question_lower for word in ["abandon", "unpaid", "waiting"]):
                params["hours_threshold"] = hours_equivalent
            elif any(word in question_lower for word in ["fast", "slow", "quick", "speed", "payer"]):
                params["threshold_hours"] = hours_equivalent
        elif second_match:
            seconds = int(second_match.group(1))
            hours_equivalent = seconds / 3600
            if any(word in question_lower for word in ["abandon", "unpaid", "waiting"]):
                params["hours_threshold"] = hours_equivalent
            elif any(word in question_lower for word in ["fast", "slow", "quick", "speed", "payer"]):
                params["threshold_hours"] = hours_equivalent
        
        return params