import os
from dotenv import load_dotenv
from openai import OpenAI
from langgraph.graph import StateGraph, END

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")


client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

resp = client.chat.completions.create(
    model="groq/compound",
    messages=[{"role": "user", "content": "What is the capital of India?"}]
)
print(resp.choices[0].message.content)