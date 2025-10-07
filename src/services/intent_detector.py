from typing import Dict, List, Tuple

class IntentDetector:
    """Detect user intent from natural language queries"""
    
    INTENT_PATTERNS = {
        # Customer Analytics
        "customer_segments": ["segment", "customer group", "type of customer", "categorize customer"],
        "customer_value": ["clv", "lifetime value", "top customer", "best customer", "high value", "most valuable"],
        "repeat_customers": ["loyal", "repeat", "returning customer", "retention", "come back"],
        
        # Payment Time Analytics (NEW)
        "payment_time": [
            "payment time", "time to pay", "how long to pay", "payment duration", 
            "order to payment", "time between order", "average payment", "how fast pay"
        ],
        "fast_slow_payers": [
            "fast payer", "slow payer", "payment speed", "quick payment", 
            "who pays fast", "who pays slow", "payment velocity"
        ],
        "abandoned_carts": [
            "abandoned", "unpaid order", "cart abandon", "didn't pay", 
            "incomplete order", "not paid", "pending payment", "waiting payment"
        ],
        
        # Topic Analytics
        "trending_topics": ["trending", "popular topic", "what people ask", "common question", "hot topic"],
        "topic_revenue": ["topic revenue", "profitable topic", "which topic make", "topic performance", "topic income"],
        "question_patterns": ["question pattern", "common question", "what they ask", "question theme"],
        
        # Emotional Analytics
        "emotions": ["emotion", "feeling", "emotional", "mood"],
        "emotion_conversion": ["emotion conversion", "which emotion convert", "emotional impact", "emotion payment"],
        "high_risk": ["risk", "distress", "negative", "support", "worried customer", "need help"],
        
        # Revenue Analytics
        "payment_rate": ["payment rate", "success rate", "conversion", "completion rate", "how many paid"],
        "revenue_trends": ["revenue trend", "sales over time", "daily revenue", "monthly revenue", "revenue growth"],
        "product_performance": ["product performance", "best product", "top selling", "product revenue", "best seller"],
        
        # Customer Needs Analytics
        "customer_needs": ["need", "looking for", "customer want", "seeking", "what do they need"],
        "unmet_needs": ["gap", "unmet need", "unfulfilled", "missing service", "not satisfied"],
        
        # Sentiment Analytics
        "sentiment_overview": ["overall sentiment", "customer satisfaction", "positive negative", "happy sad"],
        "sentiment_product": ["sentiment by product", "product sentiment", "which product happy"],
        "keywords": ["keyword", "common word", "popular term", "frequently mentioned", "top word"]
    }
    
    def detect(self, question: str) -> Tuple[str, float]:
        """
        Detect intent from question
        Returns: (intent_name, confidence_score)
        """
        question_lower = question.lower()
        
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
        params = {}
        question_lower = question.lower()
        
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
            # Fallback to static patterns
            time_patterns = {
                "today": 1,
                "yesterday": 1,
                "this week": 7,
                "last week": 7,
                "this month": 30,
                "last month": 30,
                "last quarter": 90,
                "this quarter": 90,
                "this year": 365,
                "last year": 365
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
        
        # Extract hour thresholds for abandoned carts or payment speed
        hour_pattern = r'(\d+)\s+(?:hour|hours|hrs?)'
        hour_match = re.search(hour_pattern, question_lower)
        
        if hour_match:
            hours = int(hour_match.group(1))
            # Determine context
            if any(word in question_lower for word in ["abandon", "unpaid", "waiting"]):
                params["hours_threshold"] = hours
            elif any(word in question_lower for word in ["fast", "slow", "quick", "speed"]):
                params["threshold_hours"] = hours
        
        return params
    
    def detect(self, question: str) -> Tuple[str, float]:
        """
        Detect intent from question
        Returns: (intent_name, confidence_score)
        """
        question_lower = question.lower()
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in question_lower:
                    return intent, 0.9
        
        # Fuzzy matching for partial matches
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                words = pattern.split()
                matches = sum(1 for word in words if word in question_lower)
                if matches >= len(words) * 0.6:  # 60% word match
                    return intent, 0.7
        
        return "unknown", 0.0
    
    def extract_parameters(self, question: str) -> Dict:
        """Extract parameters like time period, limits from question"""
        import re
        params = {}
        question_lower = question.lower()
        
        # Dynamic time period extraction (e.g., "last 20 days", "past 3 months")
        time_unit_multipliers = {
            "day": 1,
            "days": 1,
            "week": 7,
            "weeks": 7,
            "month": 30,
            "months": 30,
            "year": 365,
            "years": 365
        }
        
        # Pattern: "last/past N days/weeks/months/years"
        dynamic_pattern = r'(?:last|past)\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)'
        match = re.search(dynamic_pattern, question_lower)
        
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            params["period_days"] = number * time_unit_multipliers.get(unit, 1)
        else:
            # Fallback to static patterns
            time_patterns = {
                "today": 1,
                "yesterday": 1,
                "this week": 7,
                "last week": 7,
                "this month": 30,
                "last month": 30,
                "last quarter": 90,
                "this quarter": 90,
                "this year": 365,
                "last year": 365
            }
            
            for pattern, days in time_patterns.items():
                if pattern in question_lower:
                    params["period_days"] = days
                    break
        
        # Extract numbers for limits (top N, etc)
        # Look for patterns like "top 5", "first 10", "best 20"
        limit_pattern = r'(?:top|first|best|show)\s+(\d+)'
        limit_match = re.search(limit_pattern, question_lower)
        
        if limit_match:
            params["limit"] = int(limit_match.group(1))
        else:
            # Fallback: just find numbers near relevant keywords
            numbers = re.findall(r'\b(\d+)\b', question)
            if numbers and any(word in question_lower for word in ["top", "first", "best", "show"]):
                params["limit"] = int(numbers[0])
        
        return params