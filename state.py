from typing import TypedDict, List

class SkillMatchingState(TypedDict):
    job_description: str
    candidate_profile: str
    extracted_jd_skills: List[str]
    extracted_candidate_skills: List[str]
    matching_score: float
    gap_analysis: dict
    evidence: List[str]