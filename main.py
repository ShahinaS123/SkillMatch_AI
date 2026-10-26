import os
from dotenv import load_dotenv
from graph import create_graph

# Load API keys from .env file
load_dotenv()

def main():
    print("Starting Skill Matching AI...\n")
    
    # 1. Initialize the compiled graph
    app = create_graph()

    # 2. Define Test Data
    test_input = {
        "job_description": "We are looking for a Data Scientist with strong Python skills, experience in machine learning, and critical thinking. Must know SQL and AI literacy.",
        "candidate_profile": "The candidate has a degree in Computer Science. They know Python, SQL, and have strong problem-solving skills. They recently completed a course in AI literacy.",
        "extracted_jd_skills": [],
        "extracted_candidate_skills": [],
        "matching_score": 0.0,
        "gap_analysis": {},
        "evidence": []
    }

    # 3. Run the workflow
    print("Processing...")
    result = app.invoke(test_input)
    
    # 4. Print the results
    print("\n--- RESULTS ---")
    print(f"JD Skills: {result['extracted_jd_skills']}")
    print(f"Candidate Skills: {result['extracted_candidate_skills']}")
    print(f"Matching Score: {result['matching_score']}%")
    print(f"Gap Analysis (Missing Skills): {result['gap_analysis']['missing']}")

if __name__ == "__main__":
    main()