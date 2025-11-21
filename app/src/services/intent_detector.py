from typing import Dict, List, Tuple, Optional
import re
from datetime import datetime, timedelta

class IntentDetector:
    """Detect user intent from natural language queries with conversation context"""
    
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
            "incomplete order", "not paid", "pending payment", "waiting payment",
            "which customer abandoned", "who abandoned"
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
        
        # Revenue Analytics
        "revenue_trends": [
            "revenue", "sales", "income", "earnings", "money made", "total sales",
            "performance", "results", "metrics", "numbers", "statistics",
            "trend", "over time", "growth", "daily", "weekly", "monthly"
        ],
        "payment_rate": ["payment rate", "success rate", "conversion rate", "completion rate", "how many paid"],
        "product_performance": ["product performance", "best product", "top selling", "product revenue", "best seller"],
        
        # Customer Needs Analytics
        "customer_needs": ["need", "looking for", "customer want", "seeking", "what do they need"],
        "unmet_needs": ["gap", "unmet need", "unfulfilled", "missing service", "not satisfied"],
        
        # Sentiment Analytics
        "sentiment_overview": [
            "overall sentiment", "customer sentiment", "sentiment distribution",
            "are customers happy", "customer feedback", "satisfaction score",
            "happy or sad", "positive or negative"
        ],
        "sentiment_product": ["sentiment by product", "product sentiment", "which product happy"],
        "keywords": ["keyword", "common word", "popular term", "frequently mentioned", "top word"],

        # Age Analytics
        "purchases_by_age": [
            "age group", "age groups", "which age", "what age", 
            "by age", "age bracket", "age range", "age demographics",
            "oldest customer", "youngest customer", "age purchase"
        ],

        # Country Analytics
        "revenue_by_country": [
            "country revenue", "revenue country", "by country", "per country"
        ],
        "top_countries_sales": [
            "top countries", "best countries", "countries sales", 
            "which country", "what country", "countries by"
        ],
        "country_performance": [
            "country performance", "country comparison", "country metrics"
        ],
        "country_growth": [
            "country growth", "country trend", "country over time"
        ],
        "country_ltv": [
            "country lifetime", "country ltv", "country customer value"
        ],
        "country_summary": [
            "country distribution", "country overview", "country summary",
            "all countries", "geographic"
        ],
    }
    
    # Follow-up pattern definitions
    FOLLOWUP_PATTERNS = {
        "refine_filter": [
            "what about", "how about", "for", "only", "just",
            "specifically", "in particular", "focus on"
        ],
        "show_more": [
            "more detail", "tell me more", "show me more", "elaborate",
            "expand", "deeper", "full", "complete"
        ],
        "breakdown": [
            "break down", "breakdown by", "split by", "segment by",
            "group by", "divide by", "separate by"
        ],
        "compare": [
            "compare", "vs", "versus", "difference", "compared to",
            "against", "contrast"
        ],
        "trend_over_time": [
            "trend", "over time", "history", "historical",
            "past", "previous", "change"
        ],
        "filter_modify": [
            "exclude", "without", "except", "remove",
            "add", "include", "also"
        ]
    }
    
    # Semantic keyword groups
    SEMANTIC_GROUPS = {
        "revenue_related": ["revenue", "sales", "income", "earnings", "money", "profit", "performance", "results"],
        "time_related": ["today", "yesterday", "this week", "last week", "this month", "last month"],
        "customer_related": ["customer", "client", "buyer", "user"],
        "order_related": ["order", "purchase", "transaction", "sale"],
        "age_related": ["age", "age group", "old", "young", "generation"],
        "location_related": ["country", "countries", "location", "region", "geographic", "where"]
    }
    
    def detect(self, question: str, context_info: Dict = None) -> Tuple[str, float]:
        """
        Detect intent from question with conversation context
        Returns: (intent_name, confidence_score)
        """
        question_lower = question.lower()
        context_info = context_info or {}
        
        # ===== STEP 1: Check for follow-up patterns =====
        followup_result = self._detect_followup(question_lower, context_info)
        if followup_result:
            return followup_result
        
        # ===== STEP 2: Priority pattern matching =====
        
        # Priority 1: Emotion-specific topic queries
        emotion_words = ["anxious", "happy", "sad", "stressed", "worried", "confused", "hopeful", "angry", "calm"]
        has_emotion = any(emotion in question_lower for emotion in emotion_words)
        
        if has_emotion and any(word in question_lower for word in ["topic", "topics"]):
            return "topics_by_emotion", 0.95
        
        # Priority 2: Country-related queries
        if "countr" in question_lower:
            country_intent = self._detect_country_intent(question_lower)
            if country_intent:
                return country_intent
        
        # Priority 3: Semantic matching for revenue/performance queries
        has_revenue_keyword = any(kw in question_lower for kw in self.SEMANTIC_GROUPS["revenue_related"])
        has_time_keyword = any(kw in question_lower for kw in self.SEMANTIC_GROUPS["time_related"])
        
        if has_revenue_keyword and has_time_keyword:
            return "revenue_trends", 0.90
        
        if has_revenue_keyword:
            return "revenue_trends", 0.85
        
        # Priority 4: Exact pattern matching
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in question_lower:
                    return intent, 0.95
        
        # Priority 5: Fuzzy matching
        best_match = self._fuzzy_match(question_lower)
        if best_match:
            return best_match
        
        return "unknown", 0.0
    
    def _detect_followup(self, question: str, context_info: Dict) -> Optional[Tuple[str, float]]:
        """Detect and handle follow-up questions"""
        
        if not context_info.get("last_intent"):
            return None
        
        last_intent = context_info["last_intent"]
        last_params = context_info.get("last_params", {})
        
        # Check which follow-up type
        followup_type = None
        for ftype, patterns in self.FOLLOWUP_PATTERNS.items():
            if any(pattern in question for pattern in patterns):
                followup_type = ftype
                break
        
        if not followup_type:
            return None
        
        # ===== Handle different follow-up types =====
        
        # 1. REFINE FILTER: "What about US customers?"
        if followup_type == "refine_filter":
            # Detect what filter is being added
            if any(word in question for word in ["us", "usa", "united states", "america"]):
                # Keep same intent, new filter will be extracted in extract_parameters
                return last_intent, 0.90
            
            if any(emotion in question for emotion in ["anxious", "happy", "sad", "stressed", "worried"]):
                # Filtering by emotion
                return last_intent, 0.90
            
            # Generic refinement
            return last_intent, 0.85
        
        # 2. SHOW MORE: "Tell me more details"
        elif followup_type == "show_more":
            return last_intent, 0.95  # Same query, just want elaboration
        
        # 3. BREAKDOWN: "Break it down by country"
        elif followup_type == "breakdown":
            if "country" in question or "countries" in question:
                return "revenue_by_country", 0.90
            elif "age" in question:
                return "purchases_by_age", 0.90
            elif "emotion" in question:
                return "emotions", 0.90
            elif "topic" in question:
                return "trending_topics", 0.90
            else:
                # Generic breakdown, keep context
                return last_intent, 0.80
        
        # 4. COMPARE: "Compare to last month"
        elif followup_type == "compare":
            # Route to same intent but params will handle comparison
            return last_intent, 0.85
        
        # 5. TREND: "Show me the trend"
        elif followup_type == "trend_over_time":
            # If last intent was about revenue/country, show trends
            if "revenue" in last_intent or "country" in last_intent:
                return "revenue_trends", 0.85
            else:
                return last_intent, 0.80
        
        # 6. FILTER MODIFY: "Exclude US" or "Add Canada"
        elif followup_type == "filter_modify":
            return last_intent, 0.85
        
        return None
    
    def _detect_country_intent(self, question: str) -> Optional[Tuple[str, float]]:
        """Specialized detection for country-related queries"""
        
        if any(word in question for word in ["sales", "most", "top", "best", "which"]):
            return "top_countries_sales", 0.90
        elif any(word in question for word in ["revenue", "money", "income", "earn"]):
            return "revenue_by_country", 0.90
        elif any(word in question for word in ["growth", "growing", "trend"]):
            return "country_growth", 0.90
        elif any(word in question for word in ["ltv", "lifetime", "valuable"]):
            return "country_ltv", 0.90
        elif any(word in question for word in ["performance", "comparison", "compare"]):
            return "country_performance", 0.90
        elif any(word in question for word in ["distribution", "summary", "overview", "all"]):
            return "country_summary", 0.90
        else:
            return "top_countries_sales", 0.85
    
    def _fuzzy_match(self, question: str) -> Optional[Tuple[str, float]]:
        """Fuzzy matching when exact patterns don't match"""
        
        best_match = None
        best_score = 0
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                words = pattern.split()
                matches = sum(1 for word in words if word in question)
                score = matches / len(words)
                
                if score > best_score and score >= 0.6:
                    best_score = score
                    best_match = intent
        
        if best_match:
            return best_match, 0.7
        
        return None
    
    def extract_parameters(self, question: str, context_info: Dict = None) -> Dict:
        """Extract parameters with context inheritance"""
        
        params = {}
        question_lower = question.lower()
        context_info = context_info or {}
        
        # ===== INHERIT from previous context =====
        if context_info.get("last_params"):
            params = context_info["last_params"].copy()
        
        # ===== EXTRACT EMOTION FILTERS =====
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
        
        # ===== EXTRACT TIME PERIODS =====
        time_params = self._extract_time_period(question_lower)
        params.update(time_params)
        
        # ===== EXTRACT LIMITS =====
        limit_pattern = r'(?:top|first|best|show|give\s+me)\s+(\d+)'
        limit_match = re.search(limit_pattern, question_lower)
        
        if limit_match:
            params["limit"] = int(limit_match.group(1))
        
        # ===== EXTRACT THRESHOLDS =====
        threshold_params = self._extract_thresholds(question_lower)
        params.update(threshold_params)
        
        # ===== EXTRACT COUNTRY FILTERS =====
        country_params = self._extract_country_filter(question_lower)
        params.update(country_params)
        
        # ===== DETECT COMPARISON MODE =====
        if any(word in question_lower for word in ["compare", "vs", "versus", "compared to"]):
            params["comparison_mode"] = True
        
        return params
    
    def _extract_time_period(self, question: str) -> Dict:
        """Extract time period parameters"""
        params = {}
        
        # Dynamic pattern: "last/past N days/weeks/months/years"
        time_unit_multipliers = {
            "day": 1, "days": 1,
            "week": 7, "weeks": 7,
            "month": 30, "months": 30,
            "quarter": 90, "quarters": 90,
            "year": 365, "years": 365
        }
        
        dynamic_pattern = r'(?:last|past|previous)\s+(\d+)\s+(day|days|week|weeks|month|months|quarter|quarters|year|years)'
        match = re.search(dynamic_pattern, question)
        
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            params["period_days"] = number * time_unit_multipliers.get(unit, 1)
            return params
        
        # Special cases
        if "today" in question or "today's" in question:
            start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            hours_since_start = (datetime.now() - start_of_day).total_seconds() / 3600
            params["period_days"] = max(hours_since_start / 24, 0.1)
        
        elif "yesterday" in question or "yesterday's" in question:
            params["period_days"] = 1
            params["specific_date"] = "yesterday"
        
        elif any(phrase in question for phrase in ["lifetime", "all time", "ever", "since beginning", "total history"]):
            params["period_days"] = 99999
        
        elif "this year" in question:
            start_of_year = datetime(datetime.now().year, 1, 1)
            days_since_start = (datetime.now() - start_of_year).days + 1
            params["period_days"] = days_since_start
        
        elif any(phrase in question for phrase in ["last year", "past year", "in 1 year"]):
            params["period_days"] = 365
        
        else:
            # Static patterns
            time_patterns = {
                "this week": 7,
                "last week": 7,
                "this month": 30,
                "last month": 30,
                "last quarter": 90,
                "this quarter": 90
            }
            
            for pattern, days in time_patterns.items():
                if pattern in question:
                    params["period_days"] = days
                    break
        
        return params
    
    def _extract_thresholds(self, question: str) -> Dict:
        """Extract threshold parameters for payment time analysis"""
        params = {}
        
        # Hours
        hour_pattern = r'(\d+)\s+(?:hour|hours|hrs?)'
        hour_match = re.search(hour_pattern, question)
        
        if hour_match:
            hours = int(hour_match.group(1))
            if any(word in question for word in ["abandon", "unpaid", "waiting"]):
                params["hours_threshold"] = hours
            elif any(word in question for word in ["fast", "slow", "quick", "speed", "payer"]):
                params["threshold_hours"] = hours
        
        # Minutes
        minute_pattern = r'(\d+)\s+(?:minute|minutes|mins?)'
        minute_match = re.search(minute_pattern, question)
        
        if minute_match:
            minutes = int(minute_match.group(1))
            hours_equivalent = minutes / 60
            if any(word in question for word in ["abandon", "unpaid", "waiting"]):
                params["hours_threshold"] = hours_equivalent
            elif any(word in question for word in ["fast", "slow", "quick", "speed", "payer"]):
                params["threshold_hours"] = hours_equivalent
        
        return params
    
    def _extract_country_filter(self, question: str) -> Dict:
        """Extract country-specific filters"""
        params = {}
        
        # Common country mentions
        country_patterns = {
            "us": ["us", "usa", "united states", "america"],
            "uk": ["uk", "united kingdom", "britain"],
            "ca": ["canada", "canadian"],
            "au": ["australia", "australian"],
            "de": ["germany", "german"],
            "fr": ["france", "french"],
            "jp": ["japan", "japanese"],
            "cn": ["china", "chinese"]
        }
        
        for country_code, keywords in country_patterns.items():
            if any(kw in question for kw in keywords):
                params["country_filter"] = country_code.upper()
                break
        
        return params