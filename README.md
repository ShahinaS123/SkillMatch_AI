# 🎓 SkillMatch AI: Industry Alignment Module

**Project Overview:**
SkillMatch AI is a PhD research prototype designed to bridge the gap between academic curricula/candidate competencies and real-time industry requirements. It utilizes an Agentic Large Language Model (LLM) workflow to extract skills, match them semantically, and generate a strategic career roadmap for users.

**Key Features:**
*   **Document Extraction:** Upload PDFs or images (JDs/CVs) using built-in OCR.
*   **Semantic Matching:** Uses LangGraph and Groq (Llama-3) to match skills conceptually (e.g., matching "Knowledge of LAMMPS" with "Hands-on experience with LAMMPS").
*   **Gap Analysis:** Identifies missing skills and generates an "AI Career & Market Strategy" report.
*   **User Authentication & Library:** Secure login via Supabase, allowing users to save and review past analyses.

**Tech Stack:**
*   **Frontend:** Streamlit
*   **AI Orchestration:** LangChain, LangGraph
*   **LLM Engine:** Groq API (openai/gpt-oss-120b)
*   **Database & Auth:** Supabase (PostgreSQL)
*   **Document Processing:** PyTesseract, PyPDF

**Live App:** [Insert your Streamlit URL here]