import os
import asyncio
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from config.db import chunk_collection

# environment
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


#  1. initialize pinecone client
pc=Pinecone(api_key=PINECONE_API_KEY)
index=pc.Index(PINECONE_INDEX_NAME)
#  2. define embedding model
embed_model=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
#  3. define llm model
llm=ChatGroq(temperature=0.3, model_name="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY)
#  4. define chat prompt
rag_prompt=PromptTemplate.from_template(
    """
You are a helpful educational assistant.
Answer the question using ONLY the context below.

Question:
{question}

Context:
{context}

If relevant, mention the document source.

"""
)

quiz_prompt=PromptTemplate.from_template(
     """
You are a test-generating assistant.

Using the context below, generate {num_questions}
multiple-choice questions.

Format STRICTLY as:

Question 1: ...
A) ...
B) ...
C) ...
Correct Answer: A

Context:
{context}
"""
)
# 5. define rag chain
rag_chain=rag_prompt | llm
quiz_chain=quiz_prompt | llm

#  6. define the chat function
async def answer_query(query:str,user_role:str,user_grade:int)->dict:
    # 1. embedding generation
    embedding=await asyncio.to_thread(embed_model.embed_query,query)
    #  2. retrieve relevant embedding from vector db
    results=await asyncio.to_thread(
        index.query,vector=embedding,top_k=5,include_metadata=True,filter={
            "grade":user_grade,
            "role":{"$in":["Public",user_role]}
        },
    )
    #  3. validation check 
    if not results.get("matches"):
        return {"answer":"No relevant information found","sources":[]}

    #  4.  retrieve context from mongodb
    # 4.1 get chunk id
    chunk_ids=[ m["id"] for m in results["matches"]]
    #  4.2 get document/text
    docs=list(chunk_collection.find({"chunk_id":{"$in":chunk_ids}}))
    #  4.3 validation check
    if not docs:
        return {"answer":"Context unavailable","sources":[]}
    #  4.4 preserve context order 
    #  4.4.1
    doc_map={ d["chunk_id"]:d for d in docs}
    ordered_map=[doc_map[cid] for cid in chunk_ids if cid in doc_map]
    # 4.4.2
    context="\n\n".join(d["text"] for d in ordered_map)
    sources=list({ d["source"] for d in ordered_map})
    # 4.5 gather response
    response= await asyncio.to_thread(
        rag_chain.invoke,
        {"question":query,"context":context}
    )
    #  5 get proper answer
    answer_text=(
        response.content
        if hasattr(response,"content")
        else str(response)
    )

    return {
        "answer":answer_text,
        "sources":sources,
    }



async def quiz_generation(topic:str,user_role:str,user_grade:int,num_question:int=3,)->dict:
    # 1. embedding generation
    embedding=await asyncio.to_thread(embed_model.embed_query,topic)
    #  2. retrieve relevant embedding from vector db
    results=await asyncio.to_thread(
        index.query,vector=embedding,top_k=5,include_metadata=True,filter={
            "grade":user_grade,
            "role":{"$in":["Public",user_role]}
        },
    )
    #  3. validation check 
    if not results.get("matches"):
        return {"quiz":"No relevant information found to generate quiz","sources":[]}

    #  4.  retrieve context from mongodb
    # 4.1 get chunk id
    chunk_ids=[ m["id"] for m in results["matches"]]
    #  4.2 get document/text
    docs=list(chunk_collection.find({"chunk_id":{"$in":chunk_ids}}))
    #  4.3 validation check
    if not docs:
        return {"quiz":"Context unavailable to generate quiz","sources":[]}
    #  4.4 preserve context order 
    #  4.4.1
    doc_map={ d["chunk_id"]:d for d in docs}
    ordered_map=[doc_map[cid] for cid in chunk_ids if cid in doc_map]
    # 4.4.2
    context="\n\n".join(d["text"] for d in ordered_map)
    sources=list({ d["source"] for d in ordered_map})
    # 4.5 gather response
    response= await asyncio.to_thread(
        quiz_chain.invoke,
        {"num_quetion":num_question,"context":context}
    )
    #  5 get proper answer
    quiz_text=(
        response.content
        if hasattr(response,"content")
        else str(response)
    )

    return {
        "quiz":quiz_text,
        "sources":sources,
    }

