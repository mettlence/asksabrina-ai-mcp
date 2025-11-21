"""
Multi-Step Agent: Execute complex queries requiring multiple tool calls
Example: "Show trending topics and break down by country"
"""

from typing import List, Dict, Any, Tuple
from openai import OpenAI
from src.config import settings
from src.tools import (
    customer_insights, 
    topic_analysis, 
    emotional_insights, 
    revenue_metrics, 
    customer_needs,
    sentiment_analysis,
    country_analytics
)
import json

class MultiStepAgent:
    """Execute multi-step analytics queries"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Tool registry with descriptions
        self.tools = {
            # Customer Analytics
            "get_customer_segments": {
                "function": customer_insights.get_customer_segments,
                "description": "Segment customers by value and behavior",
                "params": ["period_days"]
            },
            "get_customer_lifetime_value": {
                "function": customer_insights.get_customer_lifetime_value,
                "description": "Get top customers by lifetime value",
                "params": ["top_n"]
            },
            "get_repeat_customers": {
                "function": customer_insights.get_repeat_customers,
                "description": "Analyze loyal vs one-time customers",
                "params": ["period_days"]
            },
            "get_purchases_by_age": {
                "function": customer_insights.get_purchases_by_age_group,
                "description": "Purchases breakdown by age groups",
                "params": ["period_days"]
            },
            "get_payment_time_analysis": {
                "function": customer_insights.get_payment_time_analysis,
                "description": "Average time from order to payment",
                "params": ["period_days"]
            },
            "get_fast_vs_slow_payers": {
                "function": customer_insights.get_fast_vs_slow_payers,
                "description": "Segment customers by payment speed",
                "params": ["period_days", "threshold_hours"]
            },
            "get_abandoned_carts": {
                "function": customer_insights.get_abandoned_carts,
                "description": "Find unpaid orders (abandoned carts)",
                "params": ["hours_threshold"]
            },
            
            # Topic Analytics
            "get_trending_topics": {
                "function": topic_analysis.get_trending_topics,
                "description": "Get most popular topics/questions",
                "params": ["period_days", "limit"]
            },
            "get_topic_revenue": {
                "function": topic_analysis.get_topic_revenue_correlation,
                "description": "Topics ranked by revenue generated",
                "params": ["period_days"]
            },
            "get_topics_by_emotion": {
                "function": topic_analysis.get_topics_by_emotion,
                "description": "Topics filtered by customer emotion",
                "params": ["emotion_filter", "period_days"]
            },
            
            # Emotional Analytics
            "get_emotion_distribution": {
                "function": emotional_insights.get_emotion_distribution,
                "description": "Customer emotion breakdown",
                "params": ["period_days"]
            },
            "get_emotion_conversion": {
                "function": emotional_insights.get_emotion_conversion_rate,
                "description": "Emotion to conversion correlation",
                "params": ["period_days"]
            },
            "get_high_risk_customers": {
                "function": emotional_insights.get_high_risk_customers,
                "description": "Customers needing support",
                "params": []
            },
            
            # Revenue Analytics
            "get_payment_success_rate": {
                "function": revenue_metrics.get_payment_success_rate,
                "description": "Payment completion rates",
                "params": ["period_days"]
            },
            "get_revenue_trends": {
                "function": revenue_metrics.get_revenue_trends,
                "description": "Revenue over time (day/week/month)",
                "params": ["period_days", "group_by"]
            },
            "get_product_performance": {
                "function": revenue_metrics.get_product_performance,
                "description": "Best performing products",
                "params": ["period_days"]
            },
            
            # Country Analytics
            "get_revenue_by_country": {
                "function": country_analytics.get_revenue_by_country,
                "description": "Revenue breakdown by country",
                "params": ["period_days", "limit"]
            },
            "get_top_countries_sales": {
                "function": country_analytics.get_top_countries_by_sales,
                "description": "Countries ranked by sales volume",
                "params": ["period_days", "limit"]
            },
            "get_country_performance": {
                "function": country_analytics.get_country_performance_comparison,
                "description": "Compare country performance metrics",
                "params": ["period_days"]
            },
            "get_country_growth": {
                "function": country_analytics.get_country_growth_trends,
                "description": "Country growth trends over time",
                "params": ["period_days", "comparison_days"]
            },
            
            # Sentiment Analytics
            "get_sentiment_distribution": {
                "function": sentiment_analysis.get_sentiment_distribution,
                "description": "Overall sentiment breakdown",
                "params": ["period_days"]
            },
            "get_keyword_frequency": {
                "function": sentiment_analysis.get_keyword_frequency,
                "description": "Most mentioned keywords",
                "params": ["period_days", "limit"]
            },
            
            # Customer Needs
            "get_customer_needs_distribution": {
                "function": customer_needs.get_customer_needs_distribution,
                "description": "What customers are looking for",
                "params": ["period_days"]
            },
            "get_unmet_needs_analysis": {
                "function": customer_needs.get_unmet_needs_analysis,
                "description": "Service gaps and unmet needs",
                "params": ["period_days"]
            }
        }
    
    def detect_multi_step_query(self, question: str) -> bool:
        """Check if query requires multiple steps"""
        multi_step_indicators = [
            "and then", "then show", "also", "after that",
            "break down", "breakdown", "split by", "segment by",
            "compare", "vs", "versus",
            "along with", "together with", "as well as"
        ]
        
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in multi_step_indicators)
    
    def plan_execution(self, question: str, default_params: Dict = None) -> Dict:
        """Use GPT to create execution plan"""
        
        default_params = default_params or {}
        
        # Build tool descriptions for GPT
        tool_list = []
        for tool_name, tool_info in self.tools.items():
            params_str = ", ".join(tool_info["params"])
            tool_list.append(f"- {tool_name}({params_str}): {tool_info['description']}")
        
        tools_text = "\n".join(tool_list)
        
        planning_prompt = f"""
            You are a data analytics query planner. Break down this question into execution steps.

            Available tools:
            {tools_text}

            User question: "{question}"

            Default parameters available: {json.dumps(default_params)}

            Create an execution plan. Respond ONLY with valid JSON in this format:
            {{
                "requires_multi_step": true/false,
                "steps": [
                    {{
                        "step_number": 1,
                        "tool": "tool_name",
                        "params": {{}},
                        "description": "what this step does",
                        "output_key": "unique_key_for_result"
                    }}
                ],
                "combine_strategy": "merge_results" | "compare_side_by_side" | "sequence"
            }}

            Rules:
            1. Use actual tool names from the list above
            2. Only include params that the tool accepts
            3. Set requires_multi_step to true only if multiple tools needed
            4. Keep it simple - max 3 steps
            """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": planning_prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            plan = json.loads(response.choices[0].message.content)
            return plan
            
        except Exception as e:
            print(f"❌ Planning error: {e}")
            return {
                "requires_multi_step": False,
                "steps": [],
                "combine_strategy": "sequence"
            }
    
    def execute_plan(self, plan: Dict) -> Dict:
        """Execute the planned steps"""
        
        if not plan.get("requires_multi_step") or not plan.get("steps"):
            return None
        
        results = {}
        
        for step in plan["steps"]:
            tool_name = step.get("tool")
            params = step.get("params", {})
            output_key = step.get("output_key", f"step_{step.get('step_number')}")
            
            if tool_name not in self.tools:
                print(f"⚠️ Unknown tool: {tool_name}")
                continue
            
            try:
                # Execute tool
                tool_func = self.tools[tool_name]["function"]
                
                # Filter params to only those the function accepts
                valid_params = {
                    k: v for k, v in params.items() 
                    if k in self.tools[tool_name]["params"]
                }
                
                result = tool_func(**valid_params)
                results[output_key] = {
                    "tool": tool_name,
                    "description": step.get("description"),
                    "data": result
                }
                
                print(f"✅ Executed: {tool_name}")
                
            except Exception as e:
                print(f"❌ Error executing {tool_name}: {e}")
                results[output_key] = {
                    "tool": tool_name,
                    "error": str(e)
                }
        
        return {
            "steps": results,
            "combine_strategy": plan.get("combine_strategy", "sequence")
        }
    
    def combine_results(self, execution_results: Dict) -> str:
        """Combine multi-step results into coherent response"""
        
        steps = execution_results.get("steps", {})
        strategy = execution_results.get("combine_strategy", "sequence")
        
        # Prepare data for GPT
        combined_data = []
        for key, step_result in steps.items():
            if "error" not in step_result:
                combined_data.append({
                    "step": step_result.get("description"),
                    "data": step_result.get("data")
                })
        
        synthesis_prompt = f"""
            You are a marketing analyst. Multiple data queries were executed. Synthesize them into a coherent response.

            Combination Strategy: {strategy}

            Data from each step:
            {json.dumps(combined_data, indent=2, default=str)}

            Instructions:
            - If strategy is "compare_side_by_side": Compare and contrast the results
            - If strategy is "merge_results": Present as a unified analysis
            - If strategy is "sequence": Present in logical order, showing progression

            Provide a clear, actionable summary (3-5 paragraphs max).
            """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.7,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Synthesis error: {e}")
            return "Multiple analyses completed but couldn't synthesize results."
    
    def handle_complex_query(self, question: str, default_params: Dict = None) -> Tuple[str, Dict]:
        """Main entry point for multi-step queries"""
        
        default_params = default_params or {"period_days": 30}
        
        # Check if multi-step is needed
        if not self.detect_multi_step_query(question):
            return None, {"requires_multi_step": False}
        
        # Plan execution
        plan = self.plan_execution(question, default_params)
        
        if not plan.get("requires_multi_step"):
            return None, {"requires_multi_step": False}
        
        # Execute plan
        execution_results = self.execute_plan(plan)
        
        if not execution_results:
            return None, {"error": "Execution failed"}
        
        # Combine results
        answer = self.combine_results(execution_results)
        
        metadata = {
            "multi_step": True,
            "num_steps": len(plan.get("steps", [])),
            "tools_used": [step.get("tool") for step in plan.get("steps", [])],
            "combine_strategy": plan.get("combine_strategy")
        }
        
        return answer, metadata