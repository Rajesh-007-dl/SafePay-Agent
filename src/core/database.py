import json
import os
from typing import List, Dict, Optional, Tuple
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document


class PurchaseOrderDatabase:
    def __init__(self, json_path: str, vector_db_path: str = "vectorstore/db_faiss"):
        """
        Initializes the PO Database.

        Args:
            json_path: Path to the raw purchase_orders.json
            vector_db_path: Directory where the FAISS index should be saved/loaded
        """
        self.json_path = json_path
        self.vector_db_path = vector_db_path

    
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

     
        self.data = self._load_raw_json(json_path)

    
        self.vector_store = self._initialize_vector_store()

    def _load_raw_json(self, path: str) -> Dict[str, Dict]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"PO Database file not found at: {path}")

        with open(path, "r") as f:
            raw_data = json.load(f)

        return {po["po_number"]: po for po in raw_data["purchase_orders"]}

    def _initialize_vector_store(self) -> FAISS:
        """
        Implements the logic to connect to memory (load) or create memory (save).
        """
    
        if os.path.exists(self.vector_db_path):
            print(f"Loading existing vector store from {self.vector_db_path}...")
          
            return FAISS.load_local(
                self.vector_db_path,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            print("Creating new vector store and saving to disk...")
          
            return self._build_and_save_index()

    def _build_and_save_index(self) -> FAISS:
        documents = []
        for po_id, data in self.data.items():
     
            items_str = ", ".join([item["description"] for item in data["line_items"]])
            content = f"Supplier: {data['supplier']}. Items: {items_str}"

            doc = Document(page_content=content, metadata={"po_number": po_id})
            documents.append(doc)

     
        db = FAISS.from_documents(documents, self.embeddings)

        db.save_local(self.vector_db_path)
        return db

    def get_exact_match(self, po_number: str) -> Optional[Dict]:
        return self.data.get(po_number)

    def search_fuzzy(
        self, query: str, threshold: float = 0.6
    ) -> List[Tuple[str, float]]:
   
        results = self.vector_store.similarity_search_with_score(query, k=3)

        candidates = []
        for doc, score in results:
        
            if score < 1.5:
                candidates.append((doc.metadata["po_number"], float(score)))

        return candidates
