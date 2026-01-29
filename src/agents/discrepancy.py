from src.core.state import AgentState, Discrepancy
from src.core.database import PurchaseOrderDatabase
from difflib import SequenceMatcher  


class DiscrepancyDetectorAgent:
    def __init__(self, db_path: str):
        self.db = PurchaseOrderDatabase(db_path)

    def _find_best_match_item(self, inv_item, po_items):
        """
        Aligns an Invoice Item to the correct PO Item using description similarity.
        Prevents comparing "Apples" to "Oranges" just because they are on the same row.
        """
        best_match = None
        best_score = 0.0

        for po_item in po_items:
            score = SequenceMatcher(
                None, inv_item.description.lower(), po_item["description"].lower()
            ).ratio()
            if score > best_score:
                best_score = score
                best_match = po_item

     
        if best_score > 0.6:
            return best_match
        return None

    def check(self, state: AgentState) -> AgentState:
        state.discrepancies = []

        if not state.matched_po_id:
            return state

        po_data = self.db.get_exact_match(state.matched_po_id)
        if not po_data:
            return state

      
        if state.extracted_po_ref != state.matched_po_id:
            state.discrepancies.append(
                Discrepancy(
                    type="missing_po",
                    severity="medium",
                    field="po_reference",
                    details=f"Document lacks explicit reference to {state.matched_po_id}; match inferred via supplier/content.",
                    invoice_value=state.extracted_po_ref,
                    po_value=state.matched_po_id,
                    confidence=0.85,
                )
            )

        extracted_items = state.extracted_items
        po_items = po_data["line_items"]

        matched_po_indices = set()

        for i, ext_item in enumerate(extracted_items):
         
            po_item = self._find_best_match_item(ext_item, po_items)

            if not po_item:
                state.discrepancies.append(
                    Discrepancy(
                        type="qty_mismatch",  
                        severity="medium",
                        field=f"line_item_{i}",
                        details=f"Item '{ext_item.description}' not found on Purchase Order.",
                        invoice_value=ext_item.description,
                        po_value="Not Found",
                        confidence=0.9,
                    )
                )
                continue

       
            price_variance = (ext_item.unit_price - po_item["unit_price"]) / po_item[
                "unit_price"
            ]

            if price_variance > 0.05:  
                severity = "high" if price_variance > 0.15 else "medium"
                state.discrepancies.append(
                    Discrepancy(
                        type="price_mismatch",
                        severity=severity,
                        field=f"line_item_{i}_price",
                        details=f"Unit price deviation of {price_variance:.1%} ({ext_item.unit_price} vs {po_item['unit_price']}) exceeds standard tolerance.",
                        invoice_value=ext_item.unit_price,
                        po_value=po_item["unit_price"],
                        confidence=0.95,
                    )
                )

          
            if ext_item.quantity != po_item["quantity"]:
                state.discrepancies.append(
                    Discrepancy(
                        type="qty_mismatch",
                        severity="medium",
                        field=f"line_item_{i}_qty",
                        details=f"Quantity mismatch ({ext_item.quantity} vs {po_item['quantity']}) for verified item.",
                        invoice_value=ext_item.quantity,
                        po_value=po_item["quantity"],
                        confidence=0.95,
                    )
                )

        return state
