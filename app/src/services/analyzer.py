from openai import OpenAI
from src.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def summarize_data(data, context: str, original_question: str, history=None):
    """Use GPT to summarize analytics data naturally with conversation context"""
    
    # Build rich conversation context
    context_summary = ""
    conversation_pattern = ""
    
    if history:
        # Last 2 exchanges
        recent_exchanges = []
        for msg in history[-4:]:
            role = "User" if msg.role == "user" else "Assistant"
            recent_exchanges.append(f"{role}: {msg.content[:200]}")
        context_summary = "\n".join(recent_exchanges)
        
        # Detect conversation pattern
        user_questions = [m.content for m in history if m.role == "user"]
        if len(user_questions) >= 2:
            if any(word in user_questions[-1].lower() for word in ["what about", "how about"]):
                conversation_pattern = "The user is refining their previous query."
            elif any(word in user_questions[-1].lower() for word in ["break down", "breakdown"]):
                conversation_pattern = "The user wants to see the data broken down further."
            elif any(word in user_questions[-1].lower() for word in ["compare", "vs"]):
                conversation_pattern = "The user wants to compare metrics."
    
    system_prompt = """You are a marketing data analyst assistant. 
    Your job is to interpret analytics data and provide clear, actionable insights.
    
    Guidelines:
    - Be concise but informative (2-4 paragraphs max)
    - Highlight key trends and patterns
    - Provide actionable recommendations when relevant
    - Use percentages and comparisons to make data meaningful
    - Speak naturally, as if explaining to a colleague
    - When this is a follow-up question, acknowledge the context naturally
    - Don't repeat information already discussed in the conversation
    - Focus on what's NEW or DIFFERENT in this response
    """
    
    conv_pattern_text = f"Conversation Pattern: {conversation_pattern}" if conversation_pattern else ""
    recent_conv_text = f"Recent conversation:\n{context_summary}" if context_summary else ""
    context_note = "If this builds on the previous conversation, reference it naturally without repeating yourself." if context_summary else ""

    user_prompt = f"""
    The marketing team asked: "{original_question}"

    Context: {context}

    {conv_pattern_text}

    Here is the data:
    {data}

    {recent_conv_text}

    Please provide a clear summary with key insights and recommendations.
    {context_note}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=500  # Keep responses concise
    )
    
    return response.choices[0].message.content