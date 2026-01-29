import os
import json
import glob
from dotenv import load_dotenv
from src.graph import build_graph
from src.core.state import AgentState

load_dotenv()


def load_existing_results():
    if os.path.exists("output/results.json"):
        try:
            with open("output/results.json", "r") as f:
                return json.load(f)
        except:
            return []
    return []


def run_pipeline():
    print("🚀 Starting Invoice Reconciliation Agent...")
    graph = build_graph()

    invoice_files = sorted(glob.glob("data/invoices/*.pdf"))
    if not invoice_files:
        print("❌ No PDFs found in data/invoices/")
        return

  
    all_results = load_existing_results()
    processed_files = {
        r.get("source_file") for r in all_results if r.get("source_file")
    }

    for file_path in invoice_files:
        filename = os.path.basename(file_path)

     
        if filename in processed_files:
            print(f"⏭️ Skipping {filename} (Already Processed)")
            continue

        print(f"\n--- Processing: {filename} ---")

        initial_state = AgentState(file_path=file_path, retry_count=0, agent_trace=[])
        final_state = graph.invoke(initial_state)

        output = {
            "source_file": filename,
            "invoice_id": final_state.get("extracted_invoice_id") or "UNKNOWN",
            "processing_results": {
                "extraction_confidence": final_state.get("extraction_confidence", 0.0),
                "extracted_data": {
                    "supplier": final_state.get("extracted_supplier"),
                    "po_reference": final_state.get("extracted_po_ref"),
              
                    "line_items": [
                        item.model_dump()
                        for item in final_state.get("extracted_items", [])
                    ],
                },
                "matching_results": {
                    "matched_po": final_state.get("matched_po_id"),
                    "match_reasoning": final_state.get("match_reasoning", ""),
                    "candidates_considered": [
                        c.model_dump() for c in final_state.get("match_candidates", [])
                    ],
                },
                "discrepancies": [
                    d.model_dump() for d in final_state.get("discrepancies", [])
                ],
                "recommended_action": final_state.get("final_action", "error"),
                "agent_reasoning": final_state.get("final_report_reasoning", ""),
                "agent_execution_trace": final_state.get("agent_trace", []),
            },
        }

        all_results.append(output)

        with open("output/results.json", "w") as f:
            json.dump(all_results, f, indent=2)

        print(
            f"✅ Finished {filename}. Action: {final_state.get('final_action', 'unknown')}"
        )

    print("\n🎉 Processing Complete. Results saved to output/results.json")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    run_pipeline()
