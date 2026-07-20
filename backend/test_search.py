import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from rag import RAGPipeline

load_dotenv()

async def test():
    rag = RAGPipeline()
    question = "what is sai's tech stack"
    
    print(f"Testing search for: '{question}'...")
    
    try:
        results = await rag.retrieve(question)
        
        if not results:
            print("No results found. Did you ingest documents yet?")
            return

        for r in results:
            print(f"sim={float(r['similarity']):.3f} | {r['source']} chunk {r['chunk_index']} | {r['content'][:80]}...")
    
    except Exception as e:
        print(f"Error during search: {e}")

if __name__ == "__main__":
    asyncio.run(test())