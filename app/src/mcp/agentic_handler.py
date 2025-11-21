"""
Agentic Tool Orchestration: Let GPT-4 decide which tools to call dynamically
More flexible than multi-step planning - adapts based on data
"""

from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from src.config import settings
from src.models.conversation import Message
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

class AgenticHandler:
    """GPT-4 powered agentic tool orchestration"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.max_iterations = 5
        
        # Tool definitions in OpenAI function calling format
        self.tool_definitions = self._build_tool_definitions()
        self.tool_functions = self._build_tool_registry()
    
    def _build_tool_definitions(self) -> List[Dict]:
        """Build OpenAI function calling tool definitions"""
        
        return [
            # Customer Analytics
            {
                "type": "function",
                "function": {
                    "name": "get_customer_segments",
                    "description": "Segment customers by their behavior, value, and purchase patterns. Shows different customer groups.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_customer_lifetime_value",
                    "description": "Get top customers ranked by total lifetime value and revenue generated.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "top_n": {
                                "type": "integer",
                                "description": "Number of top customers to return (default: 20)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_repeat_customers",
                    "description": "Analyze loyal vs one-time customers. Shows retention and repeat purchase rates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_purchases_by_age",
                    "description": "Show purchases and revenue broken down by customer age groups.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_payment_time_analysis",
                    "description": "Average time between order creation and payment completion.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_fast_vs_slow_payers",
                    "description": "Segment customers by payment speed. Shows fast payers vs slow payers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            },
                            "threshold_hours": {
                                "type": "integer",
                                "description": "Hours threshold to classify as fast/slow (default: 24)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_abandoned_carts",
                    "description": "Find unpaid orders that were abandoned. Shows potential lost revenue.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hours_threshold": {
                                "type": "integer",
                                "description": "Hours since order to consider abandoned (default: 48)"
                            }
                        }
                    }
                }
            },
            
            # Topic Analytics
            {
                "type": "function",
                "function": {
                    "name": "get_trending_topics",
                    "description": "Get the most popular topics and questions customers are asking about.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 7)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max number of topics to return (default: 10)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_topic_revenue",
                    "description": "Show which topics generate the most revenue. Revenue by topic analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_topics_by_emotion",
                    "description": "Get topics filtered by customer emotional state (anxious, happy, sad, etc).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "emotion_filter": {
                                "type": "string",
                                "description": "Emotion to filter by: anxious, happy, sad, stressed, worried, confused, hopeful"
                            },
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            
            # Emotional Analytics
            {
                "type": "function",
                "function": {
                    "name": "get_emotion_distribution",
                    "description": "Distribution of customer emotions. Shows what customers are feeling.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_emotion_conversion",
                    "description": "Correlation between customer emotion and payment completion rates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_high_risk_customers",
                    "description": "Identify customers showing distress or negative emotions who may need support.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            
            # Revenue Analytics
            {
                "type": "function",
                "function": {
                    "name": "get_payment_success_rate",
                    "description": "Payment completion and conversion rates. Shows paid vs unpaid orders.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_revenue_trends",
                    "description": "Revenue trends over time. Can be grouped by day, week, or month.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            },
                            "group_by": {
                                "type": "string",
                                "enum": ["day", "week", "month"],
                                "description": "Time grouping (default: day)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_product_performance",
                    "description": "Best performing products by revenue and sales volume.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            
            # Country Analytics
            {
                "type": "function",
                "function": {
                    "name": "get_revenue_by_country",
                    "description": "Revenue breakdown by customer country/location.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max countries to return (default: 20)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_top_countries_sales",
                    "description": "Countries ranked by number of sales/orders.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max countries to return (default: 10)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_country_performance",
                    "description": "Compare performance metrics across countries. Includes conversion rates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_country_growth",
                    "description": "Country growth trends comparing current vs previous period.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Current period days (default: 30)"
                            },
                            "comparison_days": {
                                "type": "integer",
                                "description": "Previous period days to compare (default: 30)"
                            }
                        }
                    }
                }
            },
            
            # Sentiment Analytics
            {
                "type": "function",
                "function": {
                    "name": "get_sentiment_distribution",
                    "description": "Overall customer sentiment breakdown. Positive, negative, neutral.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_keyword_frequency",
                    "description": "Most frequently mentioned keywords in customer communications.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max keywords to return (default: 20)"
                            }
                        }
                    }
                }
            },
            
            # Customer Needs
            {
                "type": "function",
                "function": {
                    "name": "get_customer_needs_distribution",
                    "description": "What customers are looking for and seeking. Customer intent analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_unmet_needs_analysis",
                    "description": "Service gaps and unmet customer needs. Where we're falling short.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default: 30)"
                            }
                        }
                    }
                }
            }
        ]
    
    def _build_tool_registry(self) -> Dict:
        """Map function names to actual Python functions"""
        
        return {
            # Customer Analytics
            "get_customer_segments": customer_insights.get_customer_segments,
            "get_customer_lifetime_value": customer_insights.get_customer_lifetime_value,
            "get_repeat_customers": customer_insights.get_repeat_customers,
            "get_purchases_by_age": customer_insights.get_purchases_by_age_group,
            "get_payment_time_analysis": customer_insights.get_payment_time_analysis,
            "get_fast_vs_slow_payers": customer_insights.get_fast_vs_slow_payers,
            "get_abandoned_carts": customer_insights.get_abandoned_carts,
            
            # Topic Analytics
            "get_trending_topics": topic_analysis.get_trending_topics,
            "get_topic_revenue": topic_analysis.get_topic_revenue_correlation,
            "get_topics_by_emotion": topic_analysis.get_topics_by_emotion,
            
            # Emotional Analytics
            "get_emotion_distribution": emotional_insights.get_emotion_distribution,
            "get_emotion_conversion": emotional_insights.get_emotion_conversion_rate,
            "get_high_risk_customers": emotional_insights.get_high_risk_customers,
            
            # Revenue Analytics
            "get_payment_success_rate": revenue_metrics.get_payment_success_rate,
            "get_revenue_trends": revenue_metrics.get_revenue_trends,
            "get_product_performance": revenue_metrics.get_product_performance,
            
            # Country Analytics
            "get_revenue_by_country": country_analytics.get_revenue_by_country,
            "get_top_countries_sales": country_analytics.get_top_countries_by_sales,
            "get_country_performance": country_analytics.get_country_performance_comparison,
            "get_country_growth": country_analytics.get_country_growth_trends,
            
            # Sentiment Analytics
            "get_sentiment_distribution": sentiment_analysis.get_sentiment_distribution,
            "get_keyword_frequency": sentiment_analysis.get_keyword_frequency,
            
            # Customer Needs
            "get_customer_needs_distribution": customer_needs.get_customer_needs_distribution,
            "get_unmet_needs_analysis": customer_needs.get_unmet_needs_analysis
        }
    
    def _build_system_prompt(self, conversation_history: List[Message] = None) -> str:
        """Build system prompt with context"""
        
        context_summary = ""
        if conversation_history:
            recent = []
            for msg in conversation_history[-4:]:
                role = "User" if msg.role == "user" else "Assistant"
                recent.append(f"{role}: {msg.content[:150]}")
            context_summary = "\n".join(recent)
        
        # Build context text separately (no backslash in f-string)
        recent_context_text = ""
        if context_summary:
            recent_context_text = f"Recent conversation context:\n{context_summary}"
        
        return f"""You are a marketing analytics assistant with access to powerful data analysis tools.

            Your role:
            - Answer marketing and analytics questions using the available tools
            - Call tools to gather data before responding
            - You can call multiple tools if needed to answer comprehensively
            - Synthesize data from multiple sources into clear insights
            - Provide actionable recommendations

            Guidelines:
            - Always use tools to get actual data - don't make up numbers
            - If the question requires multiple analyses, call multiple tools
            - For complex questions, break them down and use appropriate tools
            - Be concise but thorough (2-4 paragraphs)
            - Focus on actionable insights

            {recent_context_text}

            Current date context: Assume queries about "this month" or "today" refer to recent data within the last 30 days unless specified otherwise.
            """
    
    def handle_question_agentic(
        self, 
        question: str, 
        history: Optional[List[Message]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Main agentic handler - GPT decides what tools to call
        Returns: (answer, metadata)
        """
        
        # Build system prompt with context
        system_prompt = self._build_system_prompt(history)
        
        # Initialize conversation
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        tools_called = []
        iterations = 0
        
        # Agentic loop
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # Call GPT with tool definitions
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=self.tool_definitions,
                    tool_choice="auto",
                    max_tokens=1000,
                    temperature=0.7
                )
                
                message = response.choices[0].message
                messages.append(message)
                
                # Check if GPT wants to call tools
                if message.tool_calls:
                    # Execute each tool call
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                        
                        # Execute tool
                        result = self._execute_tool(function_name, arguments)
                        tools_called.append(function_name)
                        
                        # Add result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, default=str)
                        })
                        
                        print(f"✅ Tool called: {function_name}")
                
                else:
                    # GPT has final answer
                    answer = message.content
                    
                    metadata = {
                        "agentic": True,
                        "tools_called": tools_called,
                        "num_tools": len(tools_called),
                        "iterations": iterations
                    }
                    
                    return answer, metadata
            
            except Exception as e:
                print(f"❌ Agentic loop error: {e}")
                return (
                    f"I encountered an error while processing: {str(e)}",
                    {"agentic": True, "error": str(e)}
                )
        
        # Max iterations reached
        return (
            "I couldn't complete the full analysis. Please try breaking down your question.",
            {"agentic": True, "max_iterations_reached": True}
        )
    
    def _execute_tool(self, function_name: str, arguments: Dict) -> Any:
        """Execute a tool function with error handling"""
        
        if function_name not in self.tool_functions:
            return {"error": f"Unknown function: {function_name}"}
        
        try:
            tool_func = self.tool_functions[function_name]
            result = tool_func(**arguments)
            return result
        
        except Exception as e:
            print(f"❌ Tool execution error ({function_name}): {e}")
            return {"error": str(e)}