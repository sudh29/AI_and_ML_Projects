import re
import logging

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.runnables import Runnable
from operator import itemgetter

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("faiss").setLevel(logging.WARNING)

# Constants
DEFAULT_PDF_FILE = "DOCKER.pdf"
DEFAULT_MODEL = "qwen3:0.6b"
DEFAULT_TEMPLATE = """
You are an assistant that provides answers to questions based on
a given context.

Answer the question based on the context. If you can't answer the
question, reply "I don't know".

Be as concise as possible and go straight to the point.

Context: {context}

Question: {question}
"""


class RAG:
    """
    Retrieval-Augmented Generation (RAG) pipeline using LangChain with Ollama and FAISS.
    Loads a PDF, splits it into chunks, generates embeddings, stores them in a vectorstore,
    and uses a language model to answer questions based on retrieved context.
    """

    def __init__(
        self, pdf_file: str = DEFAULT_PDF_FILE, model_name: str = DEFAULT_MODEL
    ) -> None:
        self.pdf_file = pdf_file
        self.model_name = model_name
        self.pages: list[Document] | None = None

        logger.info("Initializing RAG pipeline.")
        self.retriever, self.prompt, self.model, self.parser = (
            self.__create_rag_pipeline()
        )

    def __load_pdf(self) -> None:
        """
        Load PDF and extract pages as documents.

        Returns:
            None
        """
        loader = PyPDFLoader(self.pdf_file)
        self.pages = loader.load()
        logger.debug(f"Loaded {len(self.pages)} pages from PDF.")

    def __create_chunks(self) -> list[Document]:
        """
        Split pages into smaller overlapping text chunks.

        Returns:
            list[Document]: A list of document chunks.
        """
        if not self.pages:
            raise ValueError("PDF pages not loaded.")
        splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
        chunks = splitter.split_documents(self.pages)
        logger.debug(f"Created {len(chunks)} text chunks.")
        return chunks

    def __create_embeddings(self) -> OllamaEmbeddings:
        """
        Initialize the embedding model.

        Returns:
            OllamaEmbeddings: An OllamaEmbeddings object for computing vector embeddings.
        """
        return OllamaEmbeddings(model=self.model_name)

    def __create_vectorstore(
        self, chunks: list[Document], embeddings: OllamaEmbeddings
    ) -> FAISS:
        """
        Create a FAISS vector store from chunks and embeddings.

        Args:
            chunks (list[Document]): List of document chunks.
            embeddings (OllamaEmbeddings): The embeddings generator.

        Returns:
            FAISS: A FAISS vector store instance.
        """
        return FAISS.from_documents(chunks, embeddings)

    def __create_retriever(self, vectorstore: FAISS) -> VectorStoreRetriever:
        """
        Create retriever from vector store.

        Args:
            vectorstore (FAISS): The FAISS vector store.

        Returns:
            VectorStoreRetriever: A retriever for similarity-based document search.
        """
        return vectorstore.as_retriever()

    def __create_model(self) -> ChatOllama:
        """
        Create the Ollama chat model.

        Returns:
            ChatOllama: An Ollama chat model instance.
        """
        return ChatOllama(model=self.model_name, temperature=0)

    def __create_rag_pipeline(
        self,
    ) -> tuple[VectorStoreRetriever, PromptTemplate, ChatOllama, StrOutputParser]:
        """
        Create the full RAG pipeline components.

        Returns:
            tuple: A tuple containing (retriever, prompt, model, parser).
        """
        self.__load_pdf()
        chunks = self.__create_chunks()
        embeddings = self.__create_embeddings()
        vectorstore = self.__create_vectorstore(chunks, embeddings)
        retriever = self.__create_retriever(vectorstore)
        prompt = PromptTemplate.from_template(DEFAULT_TEMPLATE)
        model = self.__create_model()
        parser = StrOutputParser()

        return retriever, prompt, model, parser

    def _create_chain(
        self,
        retriever: VectorStoreRetriever,
        prompt: PromptTemplate,
        model: ChatOllama,
        parser: StrOutputParser,
    ) -> Runnable:
        """
        Compose the RAG chain from retriever, prompt, model, and output parser.

        Returns:
            Runnable: The end-to-end RAG chain.
        """
        chain = (
            {
                "context": itemgetter("question") | retriever,
                "question": itemgetter("question"),
            }
            | prompt
            | model
            | parser
        )
        return chain

    def run(self, question: str | None) -> None:
        """
        Execute the RAG pipeline for a user-provided question.

        Args:
            question (str | None): The user input question.

        Returns:
            None
        """
        if not question:
            logger.warning("No question provided.")
            return

        logger.info(f"User Question: {question}")
        chain = self._create_chain(self.retriever, self.prompt, self.model, self.parser)

        try:
            answer: str = chain.invoke({"question": question})
            answer = (
                re.sub(r"<think>\n?.*?\n?</think>", "", answer, flags=re.DOTALL)
                .replace("\n", "")
                .strip()
            )
            logger.info(f"Answer: {answer}")
        except Exception as e:
            logger.error(f"Failed to process question: {e}")


def main() -> None:
    """Main interaction loop."""
    rag = RAG()
    logger.info("RAG system ready.")

    while True:
        question = input("Enter your question (or 'q' to quit): ").strip()
        if question.lower() == "q":
            break
        rag.run(question)

    logger.info("RAG session ended.")


if __name__ == "__main__":
    main()
