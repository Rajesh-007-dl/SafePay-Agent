from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class ExtractedLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    line_total: float
    confidence: float


class Discrepancy(BaseModel):
    type: str
    severity: str
    field: str
    details: str
    invoice_value: Optional[Any]
    po_value: Optional[Any]
    confidence: float


class POMatchCandidate(BaseModel):
    po_number: str
    confidence: float
    method: str
    reasoning: str


class AgentState(BaseModel):

    file_path: str

 
    retry_count: int = 0
    agent_trace: List[Dict[str, Any]] = Field(default_factory=list)

    extracted_invoice_id: Optional[str] = None
    extracted_supplier: Optional[str] = None
    extracted_date: Optional[str] = None
    extracted_po_ref: Optional[str] = None
    extracted_items: List[ExtractedLineItem] = Field(default_factory=list)
    extraction_confidence: float = 0.0
    extraction_reasoning: str = ""


    verification_flags: List[str] = Field(default_factory=list)
    math_verification_passed: bool = False


    matched_po_id: Optional[str] = None
    match_candidates: List[POMatchCandidate] = Field(default_factory=list)
    match_reasoning: str = ""


    discrepancies: List[Discrepancy] = Field(default_factory=list)


    final_action: str = "pending"
    final_report_reasoning: str = ""
