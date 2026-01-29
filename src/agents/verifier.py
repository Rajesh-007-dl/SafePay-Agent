from src.core.state import AgentState


class ExtractionVerifier:
    def verify(self, state: AgentState) -> AgentState:
        state.verification_flags = []
        state.math_verification_passed = True

      
        if "Invoice_1" in state.file_path and state.retry_count == 0:
            state.math_verification_passed = False
            state.verification_flags.append(
                "Simulated verification failure to demonstrate self-correction loop."
            )
            return state
      

   
        for item in state.extracted_items:
            calculated = item.quantity * item.unit_price
       
            if abs(calculated - item.line_total) > 0.01:
                state.math_verification_passed = False
                state.verification_flags.append(
                    f"Math error for {item.description}: {item.quantity}*{item.unit_price}={calculated} != {item.line_total}"
                )

        return state
