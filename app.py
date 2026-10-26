import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from graph import create_graph
from file_processor import extract_text_from_file

load_dotenv()
st.set_page_config(page_title="SkillMatch AI", layout="wide", page_icon="🎓")

# ==========================================
# 1. INITIALIZE SUPABASE & SESSION
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_supabase()

# Initialize session state for authentication
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# 2. LOGIN / SIGNUP SCREEN
# ==========================================
def show_auth_screen():
    st.title("🔐 Welcome to SkillMatch AI")
    st.markdown("Please log in or create an account to access your research library.")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In", type="primary"):
            try:
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = response.user
                st.rerun() # Refresh to show the main app
            except Exception as e:
                st.error(f"Login failed: {e}")
                
    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account"):
            try:
                response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("Account created! You can now log in.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# ==========================================
# 3. MAIN APP LOGIC
# ==========================================
def show_main_app():
    # Sidebar with Logout
    with st.sidebar:
        st.write(f"👤 Logged in as: **{st.session_state.user.email}**")
        if st.button("Log Out"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    # Create two main tabs: One for Analysis, One for Library
    app_tab, library_tab = st.tabs(["🔬 New Analysis", "📚 My Library"])

    # --- TAB 1: NEW ANALYSIS ---
    with app_tab:
        st.title("🎓 Industry Matching Module")
        st.markdown("Aligning Cultivated Talent Competencies with Industry Requirements.")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏢 Industry Requirements")
            jd_tab1, jd_tab2 = st.tabs(["📝 Paste Text", "📄 Upload File/Image"])
            with jd_tab1:
                jd_text = st.text_area("Paste Job Description here:", height=250)
            with jd_tab2:
                jd_file = st.file_uploader("Upload JD (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])

        with col2:
            st.subheader("🎓 Candidate Profile")
            cv_tab1, cv_tab2 = st.tabs(["📝 Paste Text", "📄 Upload File"])
            with cv_tab1:
                cv_text = st.text_area("Paste Resume/Syllabus here:", height=250)
            with cv_tab2:
                cv_file = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])

        if st.button("Run Matching Algorithm", type="primary", use_container_width=True):
            final_jd, final_cv = "", ""
            
            # Process files
            if jd_file: final_jd = extract_text_from_file(jd_file)
            elif jd_text: final_jd = jd_text
            
            if cv_file: final_cv = extract_text_from_file(cv_file)
            elif cv_text: final_cv = cv_text

            if final_jd and final_cv:
                with st.spinner("AI Agents are analyzing..."):
                    app = create_graph()
                    result = app.invoke({
                        "job_description": final_jd, "candidate_profile": final_cv,
                        "extracted_jd_skills": [], "extracted_candidate_skills": [],
                        "matching_score": 0.0, "gap_analysis": {}, "evidence": []
                    })
                    
                    # SAVE TO SUPABASE
                    try:
                        data_to_save = {
                            "user_id": str(st.session_state.user.id),
                            "jd_text": final_jd[:500], # Save snippet to save space
                            "cv_text": final_cv[:500],
                            "match_score": result['matching_score'],
                            "matched_skills": ", ".join(result['gap_analysis']['matched']),
                            "missing_skills": ", ".join(result['gap_analysis']['missing'])
                        }
                        supabase.table("analysis_history").insert(data_to_save).execute()
                        st.toast("✅ Analysis saved to your Library!")
                    except Exception as e:
                        st.error(f"Database Error: {e}")

                    # Display Results
                    st.divider()
                    st.metric("Overall Matching Score", f"{result['matching_score']}%")
                    
                    r1, r2 = st.columns(2)
                    with r1:
                        st.subheader("✅ Matched Skills")
                        for s in result['gap_analysis']['matched']: st.write(f"- {s}")
                    with r2:
                        st.subheader("⚠️ Missing Skills")
                        for s in result['gap_analysis']['missing']: st.write(f"- {s}")
                    
                    st.divider()
                    st.subheader("📊 AI Career & Market Strategy")
                    st.markdown(result["evidence"][0])
            else:
                st.warning("Please provide both JD and CV.")

    # --- TAB 2: MY LIBRARY ---
    with library_tab:
        st.title("📚 My Saved Analyses")
        st.markdown("View your past matching results.")
        
        # Fetch data from Supabase
        try:
            response = supabase.table("analysis_history").select("*").order("created_at", desc=True).execute()
            history = response.data
            
            if not history:
                st.info("You haven't run any analyses yet.")
            else:
                for item in history:
                    with st.expander(f"Score: {item['match_score']}% | Date: {item['created_at'][:10]}"):
                        st.write(f"**Job Description Snippet:** {item['jd_text']}...")
                        st.write(f"**Matched:** {item['matched_skills']}")
                        st.write(f"**Missing:** {item['missing_skills']}")
        except Exception as e:
            st.error(f"Could not load library: {e}")

# ==========================================
# 4. ROUTER
# ==========================================
if st.session_state.user is None:
    show_auth_screen()
else:
    show_main_app()