from openai import OpenAI
from src.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def summarize_data(data, context: str, original_question: str):
    """Use GPT to summarize analytics data naturally"""
    
    system_prompt = """You are a marketing data analyst assistant. 
    Your job is to interpret analytics data and provide clear, actionable insights.
    
    Guidelines:
    - Be concise but informative
    - Highlight key trends and patterns
    - Provide actionable recommendations when relevant
    - Use percentages and comparisons to make data meaningful
    - Speak naturally, as if explaining to a colleague
    """
    
    user_prompt = f"""
    The marketing team asked: "{original_question}"
    
    Context: {context}
    
    Here is the data:
    {data}
    
    Please provide a clear summary with key insights and recommendations.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content