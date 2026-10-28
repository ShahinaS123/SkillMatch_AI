from typing import TypedDict, List, Dict

class SkillMatchingState(TypedDict):
    job_description: str
    candidate_profile: str
    extracted_jd_skills: List[str]
    extracted_candidate_skills: List[str]
    matching_score: float
    gap_analysis: dict
    score_breakdown: Dict[str, float]  # NEW: For Technical/Experience/Education breakdown
    evidence: List[str] 