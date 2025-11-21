"""
Hybrid Intent Detector: Combines pattern matching + semantic understanding
Uses pattern matching for high-confidence cases, semantic for ambiguous queries
"""

from typing import Dict, Tuple, Optional
from src.services.intent_detector import IntentDetector
from src.services.semantic_intent_detector import SemanticIntentDetector

class HybridIntentDetector:
    """
    Intelligent intent detection using multiple strategies:
    1. Pattern matching for exact/high-confidence matches
    2. Semantic similarity for natural language variations
    3. Context-aware follow-up handling
    """
    
    def __init__(self):
        self.pattern_detector = IntentDetector()
        self.semantic_detector = SemanticIntentDetector()
        
        # Confidence thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = 0.85
        self.SEMANTIC_FALLBACK_THRESHOLD = 0.70
    
    def detect(self, question: str, context_info: Dict = None) -> Tuple[str, float, str]:
        """
        Detect intent using hybrid approach
        Returns: (intent_name, confidence_score, detection_method)
        """
        context_info = context_info or {}
        
        # ===== STEP 1: Try pattern matching first =====
        pattern_intent, pattern_confidence = self.pattern_detector.detect(
            question, context_info
        )
        
        # If pattern matching is confident, use it
        if pattern_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return pattern_intent, pattern_confidence, "pattern"
        
        # ===== STEP 2: Try semantic matching =====
        semantic_intent, semantic_confidence = self.semantic_detector.detect(
            question, context_info
        )
        
        # Compare both approaches
        if semantic_confidence >= self.SEMANTIC_FALLBACK_THRESHOLD:
            # Semantic is confident enough
            if semantic_confidence > pattern_confidence:
                return semantic_intent, semantic_confidence, "semantic"
            else:
                # Pattern has decent confidence, prefer it
                return pattern_intent, pattern_confidence, "pattern"
        
        # ===== STEP 3: Use whichever has higher confidence =====
        if pattern_confidence > semantic_confidence:
            return pattern_intent, pattern_confidence, "pattern"
        elif semantic_confidence > 0:
            return semantic_intent, semantic_confidence, "semantic"
        else:
            return "unknown", 0.0, "none"
    
    def extract_parameters(self, question: str, context_info: Dict = None) -> Dict:
        """Delegate to pattern detector for parameter extraction"""
        return self.pattern_detector.extract_parameters(question, context_info)
    
    def get_intent_explanation(self, question: str) -> Dict:
        """
        Debug/explain how intent was detected
        Useful for improving the system
        """
        
        # Get pattern matches
        pattern_intent, pattern_conf = self.pattern_detector.detect(question)
        
        # Get semantic top matches
        semantic_matches = self.semantic_detector.get_top_matches(question, top_n=3)
        
        # Get final decision
        final_intent, final_conf, method = self.detect(question)
        
        return {
            "question": question,
            "final_decision": {
                "intent": final_intent,
                "confidence": final_conf,
                "method": method
            },
            "pattern_matching": {
                "intent": pattern_intent,
                "confidence": pattern_conf
            },
            "semantic_matching": {
                "top_3_matches": [
                    {"intent": intent, "confidence": round(conf, 3)}
                    for intent, conf in semantic_matches
                ]
            }
        }