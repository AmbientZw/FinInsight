from pydantic import BaseModel


class ReportMeta(BaseModel):
    id: str
    filename: str
    title: str | None = None
    page_count: int = 0
    char_count: int = 0


class StructuredSummary(BaseModel):
    core_conclusions: list[str]
    key_data: list[str]
    main_risks: list[str]
    investment_advice: list[str]
    points_to_verify: list[str]
    disclaimer: str


class QARequest(BaseModel):
    report_id: str
    question: str
    reasoning_effort: str = "high"


class QAResponse(BaseModel):
    answer: str
    sources: list[str]
    disclaimer: str


class EvalScore(BaseModel):
    dimension: str
    score: float
    max_score: float = 5.0
    reasoning: str
    evidence: list[str] = []


class EvalResult(BaseModel):
    sample_id: str
    scores: list[EvalScore]
    overall_score: float
    safety_red_flag: bool = False


class CompareReportInput(BaseModel):
    title: str
    summary: StructuredSummary


class CompareRequest(BaseModel):
    reports: list[CompareReportInput]
