import os
import re
import streamlit as st
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from state import SkillMatchingState
from typing import List

# 1. Load local .env file (for local testing)
load_dotenv()

# 2. Get API Key (Checks local env first, then Streamlit Secrets)
def get_api_key():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            # Check Streamlit Cloud Secrets
            api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
            
    if not api_key:
        raise ValueError("GROQ_API_KEY missing. Check .env file or Streamlit Secrets.")
    return api_key

# 3. Initialize LLM with the key
api_key = get_api_key()
llm = ChatGroq(
    model="openai/gpt-oss-120b", 
    temperature=0,
    api_key=api_key 
)

# ==========================================
# 2. STATE SCHEMAS
# ==========================================
class SkillList(BaseModel):
    skills: list[str] = Field(description="A list of professional skills extracted from the text")

class MatchResult(BaseModel):
    matched_skills: List[str] = Field(description="Skills from the JD that are present in the CV.")
    missing_skills: List[str] = Field(description="Skills from the JD that are completely missing from the CV.")
    match_score: float = Field(description="A score from 0 to 100.")
    
    # Breakdown for professional dashboard
    technical_score: float = Field(description="Score for technical/hard skills match (0-100).")
    experience_score: float = Field(description="Score for experience level match (0-100).")
    education_score: float = Field(description="Score for education match (0-100).")

# ==========================================
# 3. CORE GRAPH NODES
# ==========================================
def jd_analyzer_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        "Extract a structured list of professional skills from this job description:\n\nJD: {jd}"
    )
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

def matching_engine_node(state: SkillMatchingState):
    prompt = ChatPromptTemplate.from_template(
        """You are an expert HR Director and Physics Professor. 
        Compare the Job Description skills with the Candidate skills.
        Be generous with semantic matches but accurate.
        
        Also, provide a breakdown score for Technical Skills, Experience, and Education.
        
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
    
    state["score_breakdown"] = {
        "technical": round(result.technical_score, 2),
        "experience": round(result.experience_score, 2),
        "education": round(result.education_score, 2)
    }
    
    state["gap_analysis"] = {"matched": result.matched_skills, "missing": result.missing_skills}
    return state

# ==========================================
# 4. AI UTILITIES & REPORTING
# ==========================================
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

# ==========================================
# 5. MEDIA & MULTIMODAL ANALYSIS
# ==========================================
def analyze_media_transcript(transcript):
    prompt = ChatPromptTemplate.from_template(
        """You are an expert Communication Coach and Technical Interviewer for Engineering graduates.
        Analyze the following transcript of a candidate's spoken presentation or interview.
        
        Transcript:
        {transcript}
        
        Please provide a professional report with the following sections:
        ### 🗣️ Communication & Clarity
        (Assess their tone, pace, and clarity based on the text. Note any excessive filler words like "um", "uh", "like".)
        
        ### 🧠 Technical Explanation
        (Did they explain engineering concepts clearly? Were they able to break down complex ideas?)
        
        ### 💡 Areas for Improvement
        (Provide 3 actionable tips to improve their verbal communication and interview presence.)
        """
    )
    chain = prompt | llm
    result = chain.invoke({"transcript": transcript})
    return result.content

# ==========================================
# 6. ADVANCED CAREER TOOLS
# ==========================================
def generate_cover_letter_node(cv_text, jd_text, matched_skills):
    prompt = ChatPromptTemplate.from_template(
        """You are an expert career coach. Write a professional, 3-paragraph cover letter for a candidate applying to this job.
        
        Job Description: {jd}
        Candidate CV: {cv}
        Key Matched Skills to Highlight: {skills}
        
        Make the letter engaging, highlight how their specific skills solve the employer's needs, and confidently address any potential gaps. Do not use placeholders like [Company Name]; invent a generic professional tone.
        """
    )
    chain = prompt | llm
    result = chain.invoke({
        "jd": jd_text[:3000], 
        "cv": cv_text[:3000],
        "skills": ", ".join(matched_skills)
    })
    return result.content

def generate_interview_questions_node(cv_text, jd_text, missing_skills):
    prompt = ChatPromptTemplate.from_template(
        """You are a Senior Technical Interviewer for an Engineering position. 
        Based on the candidate's profile and the missing skills, generate 5 challenging technical interview questions.
        
        Job Description: {jd}
        Missing Skills: {missing}
        
        Format the output as a numbered list (1-5). For each question, briefly state the "Purpose" of the question.
        """
    )
    chain = prompt | llm
    result = chain.invoke({
        "jd": jd_text[:3000],
        "missing": ", ".join(missing_skills)
    })
    return result.content

def simulate_what_if_node(current_missing, proposed_course):
    prompt = ChatPromptTemplate.from_template(
        """You are an Academic Curriculum Auditor. 
        Currently, the students are missing these skills: {missing}.
        The university is considering adding a new course described as: "{course}".
        
        Based on the course description, estimate the impact.
        Output:
        1. Which specific missing skills this course would address.
        2. The estimated new match score percentage (assume the current score is 60%, how much would it increase?).
        3. A brief justification.
        """
    )
    chain = prompt | llm
    result = chain.invoke({
        "missing": ", ".join(current_missing),
        "course": proposed_course
    })
    return result.content
# ... [Keep existing code] ...

def anonymize_cv_node(cv_text):
    """Strips PII (names, photos, gender, age) from a CV."""
    prompt = ChatPromptTemplate.from_template(
        """Rewrite the following CV text to completely remove all personal identifiers.
        Remove the candidate's name, email, phone number, physical address, date of birth, gender, and nationality.
        Replace the name with "Candidate". Keep all technical skills, education, and experience intact.
        
        Original CV:
        {cv}
        """
    )
    chain = prompt | llm
    result = chain.invoke({"cv": cv_text})
    return result.content

def tailor_cv_node(cv_text, jd_text, missing_skills):
    """Rewrites CV bullets to highlight matched skills and bridge gaps."""
    prompt = ChatPromptTemplate.from_template(
        """You are an expert resume writer. Rewrite the candidate's professional summary and 3 bullet points to better align with the Job Description.
        Address the following missing skills by showing how the candidate's past experience demonstrates transferable abilities: {missing}.
        
        Job Description: {jd}
        Original CV: {cv}
        
        Provide the output in Markdown format.
        """
    )
    chain = prompt | llm
    result = chain.invoke({"cv": cv_text[:2000], "jd": jd_text[:2000], "missing": ", ".join(missing_skills)})
    return result.content