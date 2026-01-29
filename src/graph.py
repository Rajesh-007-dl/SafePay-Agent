from langgraph.graph import StateGraph, END
from src.core.state import AgentState
from src.agents.doc_intelligence import DocumentIntelligenceAgent
from src.agents.verifier import ExtractionVerifier
from src.agents.matching import MatchingAgent
from src.agents.discrepancy import DiscrepancyDetectorAgent
from src.agents.resolution import ResolutionAgent

def extract_node(state: AgentState):
    agent = DocumentIntelligenceAgent()
    new_state = agent.process(state)

    
    new_state.agent_trace.append(
        {
            "agent": "Document Intelligence",
            "status": "Success",
            "confidence": new_state.extraction_confidence,
            "detail": f"Extracted {len(new_state.extracted_items)} line items. Notes: {new_state.extraction_reasoning}",
        }
    )
    return new_state


def verify_node(state: AgentState):
    agent = ExtractionVerifier()
    new_state = agent.verify(state)

   
    status = "Passed" if new_state.math_verification_passed else "Failed"
    detail = (
        "Math checks passed."
        if new_state.math_verification_passed
        else f"Found math errors: {new_state.verification_flags}"
    )

    new_state.agent_trace.append(
        {
            "agent": "Extraction Verifier",
            "status": status,
            "confidence": 1.0,
            "detail": detail,
        }
    )
    return new_state


def retry_node(state: AgentState):
    """
    Increments retry count and logs the loop.
    This must be a Node (not an edge) to persist the state change.
    """
    state.retry_count += 1
    state.agent_trace.append(
        {
            "agent": "Orchestrator",
            "status": "Looping",
            "confidence": 1.0,
            "detail": "Triggering re-extraction due to math verification failure.",
        }
    )
    return state


def match_node(state: AgentState):
  
    agent = MatchingAgent(db_path="data/purchase_orders.json")
    new_state = agent.match(state)

    if new_state.matched_po_id:
        status = "Success"
        conf = (
            new_state.match_candidates[0].confidence
            if new_state.match_candidates
            else 0.0
        )
    else:
        status = "No Match"
        conf = 0.0

    new_state.agent_trace.append(
        {
            "agent": "Matching Agent",
            "status": status,
            "confidence": conf,
            "detail": new_state.match_reasoning,
        }
    )
    return new_state


def discrepancy_node(state: AgentState):
    agent = DiscrepancyDetectorAgent(db_path="data/purchase_orders.json")
    new_state = agent.check(state)

    count = len(new_state.discrepancies)
    detail = f"Found {count} discrepancies."
    if count > 0:
        types = [d.type for d in new_state.discrepancies]
        detail += f" Types: {', '.join(types)}"

    new_state.agent_trace.append(
        {
            "agent": "Discrepancy Detector",
            "status": "Flagged" if count > 0 else "Clean",
            "confidence": 1.0,  
            "detail": detail,
        }
    )
    return new_state


def resolution_node(state: AgentState):
    agent = ResolutionAgent()
    new_state = agent.resolve(state)

    new_state.agent_trace.append(
        {
            "agent": "Resolution Agent",
            "status": "Complete",
            "confidence": 1.0,
            "detail": f"Action: {new_state.final_action}. Reason: {new_state.final_report_reasoning}",
        }
    )
    return new_state


def should_retry_extraction(state: AgentState):
    """
    Decides if we should loop back.
    Checks state, returns string. Does NOT modify state.
    """
    if not state.math_verification_passed and state.retry_count < 1:
        return "retry"
    return "continue"

def build_graph():
    builder = StateGraph(AgentState)

  
    builder.add_node("extract", extract_node)
    builder.add_node("verify", verify_node)
    builder.add_node("retry_logic", retry_node)  
    builder.add_node("match", match_node)
    builder.add_node("discrepancy", discrepancy_node)
    builder.add_node("resolve", resolution_node)


    builder.set_entry_point("extract")

    builder.add_edge("extract", "verify")

    builder.add_conditional_edges(
        "verify",
        should_retry_extraction,
        {"retry": "retry_logic", "continue": "match"},  
    )

    builder.add_edge("retry_logic", "extract") 

    builder.add_edge("match", "discrepancy")
    builder.add_edge("discrepancy", "resolve")
    builder.add_edge("resolve", END)

    return builder.compile()
