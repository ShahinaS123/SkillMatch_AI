import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from state import SkillMatchingState

# Load environment variables
load_dotenv()

# Initialize the LLM (Using the stable free model)
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

# Define the structure for our expected output
class SkillList(BaseModel):
    skills: list[str] = Field(description="A list of professional skills extracted from the text")

def jd_analyzer_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        "Extract a structured list of professional skills from this job description:\n\nJD: {jd}"
    )
    # Force the LLM to output data matching our SkillList schema
    structured_llm = llm.with_structured_output(SkillList)
    chain = prompt | structured_llm
    
    result = chain.invoke({"jd": state["job_description"]})
    state["extracted_jd_skills"] = result.skills 
    return state

def candidate_analyzer_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        "Extract a structured list of professional skills from this candidate profile or syllabus:\n\nProfile: {profile}"
    )
    structured_llm = llm.with_structured_output(SkillList)
    chain = prompt | structured_llm
    
    result = chain.invoke({"profile": state["candidate_profile"]})
    state["extracted_candidate_skills"] = result.skills
    return state

# ... [Keep your imports and other nodes above this] ...

# NEW SCHEMA for the Matching Engine
from pydantic import BaseModel, Field
from typing import List

class MatchResult(BaseModel):
    matched_skills: List[str] = Field(description="Skills from the JD that are present in the CV, even if worded differently. Include the JD's phrasing.")
    missing_skills: List[str] = Field(description="Skills from the JD that are completely missing from the CV.")
    match_score: float = Field(description="A score from 0 to 100 representing the percentage of JD skills matched.")

def matching_engine_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        """You are an expert HR Director and Physics Professor. 
        Compare the Job Description skills with the Candidate skills.
        
        CRITICAL INSTRUCTIONS:
        - Look for semantic matches. If the JD asks for "Hands-On Experience with LAMMPS" and the CV says "Knowledge of LAMMPS", that is a MATCH.
        - If the JD asks for "Academic Writing" and the CV lists multiple publications, that is a MATCH.
        - Be generous but accurate. 
        
        Job Description Skills: {jd_skills}
        Candidate CV Skills: {cv_skills}
        
        Calculate the match score based purely on the skills requested in the JD.
        """
    )
    
    # Force the LLM to output structured data based on our schema
    structured_llm = llm.with_structured_output(MatchResult)
    chain = prompt | structured_llm
    
    result = chain.invoke({
        "jd_skills": ", ".join(state["extracted_jd_skills"]),
        "cv_skills": ", ".join(state["extracted_candidate_skills"])
    })
    
    state["matching_score"] = round(result.match_score, 2)
    state["gap_analysis"] = {
        "matched": result.matched_skills,
        "missing": result.missing_skills
    }
    return state

# ... [Keep your report_generator_node below this] ...
def market_strategy_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        """You are an expert Career Coach and Academic Mentor.
        Based on the gap analysis between the Job Description and the Candidate, write a strategic report.
        
        Candidate's Matched Skills: {matched}
        Candidate's Missing Skills: {missing}
        Match Score: {score}%
        
        Please structure your response with these exact headings:
        ### 📈 Areas for Improvement
        (What specific courses, certifications, or projects should the candidate do to bridge the gap?)
        
        ### 🎯 Market Targeting Strategy
        (Based on their current matched skills, what other industries or job titles should they target if this specific job doesn't work out? e.g., Data Science, Material Science R&D, etc.)
        """
    )
    chain = prompt | llm
    result = chain.invoke({
        "matched": ", ".join(state["gap_analysis"]["matched"]),
        "missing": ", ".join(state["gap_analysis"]["missing"]),
        "score": state["matching_score"]
    })
    
    # We will store this new report in the evidence list
    state["evidence"] = [result.content]
    return state