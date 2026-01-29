from src.core.state import AgentState


class ResolutionAgent:
    def resolve(self, state: AgentState) -> AgentState:

        reasons = []
        action = "escalate_to_human"

        has_discrepancies = len(state.discrepancies) > 0
        high_severity = any(d.severity == "high" for d in state.discrepancies)
        conf_score = min(state.extraction_confidence, 0.95)

        if conf_score < 0.80:
            action = "escalate_to_human"
            reasons.append(
                f"Low extraction confidence ({conf_score:.2f}) requires human eyes."
            )
        elif high_severity:
            action = "escalate_to_human"
     
            for d in state.discrepancies:
                if d.severity == "high":
                    reasons.append(f"CRITICAL: {d.details}")


        elif has_discrepancies:
            action = "flag_for_review"
            for d in state.discrepancies:
                if d.type == "price_mismatch":
                    reasons.append(
                        f"Price variance detected ({d.invoice_value} vs {d.po_value})."
                    )
                elif d.type == "missing_po":
                    reasons.append(
                        f"PO inferred ({d.po_value}) but not explicit on doc."
                    )
                elif d.type == "qty_mismatch":
                    reasons.append(
                        f"Quantity difference ({d.invoice_value} vs {d.po_value})."
                    )

   
        elif (
            state.matched_po_id
            and not has_discrepancies
            and state.math_verification_passed
        ):
            action = "auto_approve"
            reasons.append("Perfect 3-way match (Invoice ↔ PO ↔ Math).")

        else:
            reasons.append("System uncertainty regarding PO match.")

        state.final_action = action
        state.final_report_reasoning = "; ".join(reasons)

        return state
