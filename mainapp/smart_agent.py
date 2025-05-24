from typing import Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.manus import Manus
from app.logger import logger
import asyncio
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize agents
gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0,
    api_key=os.getenv("GOOGLE_API_KEY"),
)


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-05-20",
    temperature=0.2,
    api_key=os.getenv("GOOGLE_API_KEY"),
    model_kwargs={
        "system_prompt": "You are a helpful assistant that can answer questions and help with stuff"
    },
)


manus = Manus()


async def process_query(query: str) -> str:
    """
    Process a query using either Gemini or Manus based on complexity.
    Simple queries go to Gemini, complex ones to Manus.
    """
    try:
        # Quick complexity check using ainvoke for async operation
        analysis = await gemini.ainvoke(
            f"""Is this a simple question for which i do not need any tools or llm and that can be answered directly? 
            Answer with just YES or NO.
            Question: {query}"""
        )

        is_simple = analysis.content.strip().upper() == "YES"

        if is_simple:
            logger.info("Using Gemini for simple query")
            # Use ainvoke for async operation
            response = await llm.ainvoke(query)
            return response.content
        else:
            logger.info("Using Manus for complex task")
            return await manus.run(query)

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return f"I encountered an error: {str(e)}"


async def main():
    """Example usage of the smart agent"""
    # Test queries
    query = input("Enter a query: ")

    # Process each query

    response = await process_query(query)
    print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
