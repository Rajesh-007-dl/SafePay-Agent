from typing import List
from src.core.state import AgentState, POMatchCandidate
from src.core.database import PurchaseOrderDatabase
from difflib import SequenceMatcher


class MatchingAgent:
    def __init__(self, db_path: str):
        self.db = PurchaseOrderDatabase(db_path)

    def _calculate_string_similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def match(self, state: AgentState) -> AgentState:
        state.match_candidates = []

     
        if state.extracted_po_ref:
            exact_match = self.db.get_exact_match(state.extracted_po_ref)
            if exact_match:
                candidate = POMatchCandidate(
                    po_number=state.extracted_po_ref,
                    confidence=0.95,
                    method="exact_ref",
                    reasoning=f"Identified specific PO reference {state.extracted_po_ref}.",
                )
                state.match_candidates.append(candidate)
                state.matched_po_id = candidate.po_number
                state.match_reasoning = candidate.reasoning
                return state

    
        query_parts = []
        if state.extracted_supplier:
            query_parts.append(f"Supplier: {state.extracted_supplier}")
        if state.extracted_items:
            items_str = ", ".join([item.description for item in state.extracted_items])
            query_parts.append(f"Items: {items_str}")
        fuzzy_query = ". ".join(query_parts)

        raw_results = self.db.search_fuzzy(fuzzy_query, threshold=0.40)

        ranked_candidates = []
        for po_id, vector_score in raw_results:
            po_data = self.db.get_exact_match(po_id)
            if not po_data:
                continue

            supplier_sim = self._calculate_string_similarity(
                state.extracted_supplier or "", po_data["supplier"]
            )
            final_score = min((vector_score * 0.4) + (supplier_sim * 0.6), 0.85)

            if final_score > 0.45: 
                ranked_candidates.append(
                    {
                        "po_id": po_id,
                        "score": final_score,
                        "supplier": po_data["supplier"],
                    }
                )

 
        ranked_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_3 = ranked_candidates[:3]

        for cand in top_3:
            state.match_candidates.append(
                POMatchCandidate(
                    po_number=cand["po_id"],
                    confidence=float(f"{cand['score']:.2f}"),
                    method="fuzzy_hybrid",
                    reasoning=f"Supplier: {cand['supplier']} (Score: {cand['score']:.2f})",
                )
            )

        if state.match_candidates:
            best = state.match_candidates[0]
            if best.confidence > 0.60:
                state.matched_po_id = best.po_number
                state.match_reasoning = f"Hypothesized {best.po_number} as best match. Alternatives considered: {[c.po_number for c in state.match_candidates[1:]]}"
            else:
                state.matched_po_id = None
                state.match_reasoning = "Top matches had low confidence."
        else:
            state.matched_po_id = None
            state.match_reasoning = "No viable PO candidates found."

        return state
