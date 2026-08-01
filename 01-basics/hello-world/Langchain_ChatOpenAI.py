import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

llm = ChatOpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    model="groq/compound"
)

response = llm.invoke("What is the capital of India?")
print(response.content)