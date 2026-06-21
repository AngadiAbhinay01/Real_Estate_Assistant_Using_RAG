# @Author: Dhaval Patel Copyrights Codebasics Inc. and LearnerX Pvt Ltd.

from uuid import uuid4
from pathlib import Path

from dotenv import load_dotenv

from langchain_community.document_loaders import UnstructuredURLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# =========================
# Constants
# =========================

CHUNK_SIZE = 1000
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

VECTORSTORE_DIR = Path(__file__).parent / "resources" / "vectorstore"
COLLECTION_NAME = "real_estate"

llm = None
vector_store = None


# =========================
# Initialization
# =========================

def initialize_components():
    global llm, vector_store

    if llm is None:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=500
        )

    if vector_store is None:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL
        )

        vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(VECTORSTORE_DIR)
        )


# =========================
# URL Processing
# =========================

def process_urls(urls):
    """
    Loads URLs, chunks text and stores embeddings in ChromaDB.
    """

    yield "Initializing Components..."
    initialize_components()

    yield "Resetting Vector Store..."
    try:
        vector_store.reset_collection()
    except Exception:
        pass

    yield "Loading URLs..."
    loader = UnstructuredURLLoader(urls=urls)
    documents = loader.load()

    yield "Splitting Documents..."

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "]
    )

    docs = splitter.split_documents(documents)

    yield f"Creating {len(docs)} Chunks..."

    ids = [str(uuid4()) for _ in docs]

    vector_store.add_documents(
        documents=docs,
        ids=ids
    )

    yield "Documents Added Successfully!"


# =========================
# Question Answering
# =========================

def generate_answer(query):
    """
    Retrieve relevant chunks and ask LLM.
    """

    initialize_components()

    docs = vector_store.similarity_search(
        query=query,
        k=4
    )

    context = "\n\n".join(
        [doc.page_content for doc in docs]
    )

    prompt = f"""
You are a Real Estate Assistant.

Answer the user's question ONLY using the provided context.

If the answer is not available in the context, say:
"I could not find that information in the provided documents."

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:
"""

    response = llm.invoke(prompt)

    sources = []

    for doc in docs:
        source = doc.metadata.get("source")
        if source:
            sources.append(source)

    return response.content, list(set(sources))


# =========================
# Testing
# =========================

if __name__ == "__main__":

    urls = [
        "https://www.cnbc.com/2024/12/21/how-the-federal-reserves-rate-policy-affects-mortgages.html",
        "https://www.cnbc.com/2024/12/20/why-mortgage-rates-jumped-despite-fed-interest-rate-cut.html"
    ]

    for status in process_urls(urls):
        print(status)

    answer, sources = generate_answer(
        "Tell me what was the 30 year fixed mortgage rate along with the date?"
    )

    print("\nANSWER:")
    print(answer)

    print("\nSOURCES:")
    print(sources)