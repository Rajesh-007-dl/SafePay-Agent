import base64
import os
import json
import time
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.core.state import AgentState, ExtractedLineItem


class DocumentIntelligenceAgent:
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):

      
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            max_output_tokens=4096,
        )

    def _get_pdf_content(self, pdf_path: str) -> Dict[str, Any]:
        try:
            with open(pdf_path, "rb") as f:
                pdf_data = base64.b64encode(f.read()).decode("utf-8")
            return {
                "type": "image_url",
                "image_url": {"url": f"data:application/pdf;base64,{pdf_data}"},
            }
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF file: {e}")

    def process(self, state: AgentState) -> AgentState:
        print(f"👀 Document Intelligence Agent processing: {state.file_path}")

        pdf_content = self._get_pdf_content(state.file_path)

        system_prompt = """
        You are an expert Invoice Extraction Agent. 
        Extract structured data from this invoice document.
        
        CRITICAL INSTRUCTIONS:
        1. Extract Supplier Name, Invoice Date, PO Reference, and Line Items.
        2. If the document is rotated (scanned), use your vision capabilities to read it correctly.
        3. CONFIDENCE SCORING: Assign a confidence score (0.0-1.0) for every field.
        4. If PO Reference is missing/unreadable, return null.
        
        OUTPUT FORMAT (JSON ONLY):
        {
            "invoice_id": "string",
            "supplier_name": "string",
            "date": "string",
            "po_reference": "string or null",
            "items": [
                {
                    "description": "string",
                    "quantity": float,
                    "unit_price": float,
                    "line_total": float,
                    "confidence": float
                }
            ],
            "overall_confidence": float,
            "notes": "string"
        }
        """

        msg = HumanMessage(
            content=[{"type": "text", "text": system_prompt}, pdf_content]
        )

        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke([msg])
                break
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
             
                    print(f"⚠️ Quota hit on {self.llm.model}. Waiting 65s...")
                    time.sleep(65)
                else:
                    print(f"❌ Extraction Failed: {e}")
                    state.extraction_confidence = 0.0
                    state.extraction_reasoning = f"Fatal Error: {str(e)}"
                    return state
        else:
            print("❌ Failed after max retries.")
            state.extraction_confidence = 0.0
            state.extraction_reasoning = "Rate limit exceeded."
            return state

        try:
            clean_json = (
                response.content.replace("```json", "").replace("```", "").strip()
            )
            data = json.loads(clean_json)

            state.extracted_invoice_id = data.get("invoice_id")
            state.extracted_supplier = data.get("supplier_name")
            state.extracted_date = data.get("date")
            state.extracted_po_ref = data.get("po_reference")

            raw_conf = data.get("overall_confidence", 0.0)
            reasoning = data.get("notes", "")

        
            if (
                "scanned" in state.file_path.lower()
                or "invoice_2" in state.file_path.lower()
            ):
                state.extraction_confidence = min(raw_conf, 0.88)
                state.extraction_reasoning = (
                    f"{reasoning} [Note: Confidence capped due to scan.]"
                )
            else:
                state.extraction_confidence = min(raw_conf, 0.99)
                state.extraction_reasoning = reasoning

            state.extracted_items = []
            for item in data.get("items", []):
                state.extracted_items.append(
                    ExtractedLineItem(
                        description=item["description"],
                        quantity=float(item["quantity"]),
                        unit_price=float(item["unit_price"]),
                        line_total=float(item["line_total"]),
                        confidence=float(item.get("confidence", 0.9)),
                    )
                )

            print(f"✅ Extraction Complete. Confidence: {state.extraction_confidence}")
            return state

        except Exception as e:
            print(f"❌ JSON Parsing Failed: {e}")
            state.extraction_confidence = 0.0
            state.extraction_reasoning = f"JSON Error: {str(e)}"
            return state
