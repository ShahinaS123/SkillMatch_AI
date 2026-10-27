import os
import re
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from state import SkillMatchingState
from typing import List

load_dotenv()
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

class SkillList(BaseModel):
    skills: list[str] = Field(description="A list of professional skills extracted from the text")

def jd_analyzer_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template("Extract a structured list of professional skills from this job description:\n\nJD: {jd}")
    structured_llm = llm.with_structured_output(SkillList)
    chain = prompt | structured_llm
    result = chain.invoke({"jd": state["job_description"]})
    state["extracted_jd_skills"] = result.skills 
    return state

def candidate_analyzer_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template("Extract a structured list of professional skills from this candidate profile or syllabus:\n\nProfile: {profile}")
    structured_llm = llm.with_structured_output(SkillList)
    chain = prompt | structured_llm
    result = chain.invoke({"profile": state["candidate_profile"]})
    state["extracted_candidate_skills"] = result.skills
    return state

class MatchResult(BaseModel):
    matched_skills: List[str] = Field(description="Skills from the JD that are present in the CV.")
    missing_skills: List[str] = Field(description="Skills from the JD that are completely missing from the CV.")
    match_score: float = Field(description="A score from 0 to 100.")

def matching_engine_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        """You are an expert HR Director and Physics Professor. 
        Compare the Job Description skills with the Candidate skills.
        Be generous with semantic matches but accurate.
        
        Job Description Skills: {jd_skills}
        Candidate CV Skills: {cv_skills}
        """
    )
    structured_llm = llm.with_structured_output(MatchResult)
    chain = prompt | structured_llm
    result = chain.invoke({
        "jd_skills": ", ".join(state["extracted_jd_skills"]),
        "cv_skills": ", ".join(state["extracted_candidate_skills"])
    })
    state["matching_score"] = round(result.match_score, 2)
    state["gap_analysis"] = {"matched": result.matched_skills, "missing": result.missing_skills}
    return state

def clean_ai_output(text):
    if not text: return ""
    text = re.sub(r'<[^>]+>', ', ', text)
    text = re.sub(r',\s*,', ',', text)
    return text.strip()

def market_strategy_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        """You are a Senior Career Strategist and Academic Dean. Write an exhaustive, professional report based on the analysis.
        
        Matched Skills: {matched}
        Missing Skills: {missing}
        Match Score: {score}%
        
        CRITICAL INSTRUCTIONS:
        1. Do NOT use HTML tags (no <br>, no <table>).
        2. Use ONLY Markdown tables.
        3. Be highly specific. Recommend exact certifications, specific software tools, and concrete project ideas.
        
        Use EXACTLY this structure:

        ### Executive Summary
        (Write a 3-sentence overview of the candidate's readiness and primary gaps.)

        ### Detailed Gap Analysis & Action Plan
        | Identified Gap | Strategic Action Plan | Specific Resources & Certifications | Timeline |
        |---|---|---|---|
        | [Gap 1] | [Detailed steps] | [Exact course names, e.g., Coursera X, or IEEE Cert] | [e.g., 2-3 Months] |

        ### Market Targeting Strategy
        | Skill Cluster | Target Industries | Relevant Job Titles | Strategic Value / Why It Fits |
        |---|---|---|---|
        | [Cluster 1] | [Specific sectors] | [Specific titles] | [Detailed justification] |

        ### Key Deliverables for Portfolio
        - [Specific project idea 1]
        - [Specific project idea 2]
        - [Specific publication/paper idea]
        """
    )
    chain = prompt | llm
    result = chain.invoke({
        "matched": ", ".join(state["gap_analysis"]["matched"]),
        "missing": ", ".join(state["gap_analysis"]["missing"]),
        "score": state["matching_score"]
    })
    state["evidence"] = [clean_ai_output(result.content)]
    return state