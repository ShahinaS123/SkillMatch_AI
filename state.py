from typing import Dict, List, Optional, TypedDict


class SkillMatchingState(TypedDict, total=False):
    """
    Shared state for the SkillMatch AI LangGraph workflow.

    `total=False` allows each graph node to return only the fields it updates.
    Existing required input fields should still be supplied when invoking the graph.
    """

    # Inputs
    job_description: str
    candidate_profile: str

    # Extracted skills
    extracted_jd_skills: List[str]
    extracted_candidate_skills: List[str]

    # Matching output
    matching_score: float
    gap_analysis: Dict[str, List[str]]
    score_breakdown: Dict[str, Optional[float]]

    # Evidence and score transparency
    evidence: List[str]
    total_jd_skills: int
    total_candidate_skills: int
    score_method: str
