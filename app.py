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

if "user" not in st.session_state:
    st.session_state.user = None

# Define the levels based on your research architecture
ROLES = [
    "Student", 
    "Teacher / Professor", 
    "Organization (HR)", 
    "Industry Level", 
    "Institutional Level", 
    "Recruitment Level", 
    "Researcher"
]

# ==========================================
# 2. LOGIN / SIGNUP SCREEN
# ==========================================
def show_auth_screen():
    st.title("🔐 Welcome to SkillMatch AI")
    st.markdown("Please log in or create an account to access your personalized research library.")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In", type="primary"):
            try:
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = response.user
                st.rerun() 
            except Exception as e:
                st.error(f"Login failed: {e}")
                
    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_pass")
        # New: Role Selection Dropdown
        user_role = st.selectbox("Select your user profile:", ROLES, key="signup_role")
        
        if st.button("Create Account"):
            try:
                # Save the role in Supabase user metadata
                response = supabase.auth.sign_up({
                    "email": new_email, 
                    "password": new_password,
                    "options": {"data": {"role": user_role}}
                })
                st.success(f"Account created as {user_role}! You can now log in.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# ==========================================
# 3. MAIN APP LOGIC
# ==========================================
def show_main_app():
    # Get user role from metadata (default to 'Student' if missing)
    user_role = st.session_state.user.user_metadata.get("role", "Student")

    # --- SIDEBAR: Navigation & Library ---
    with st.sidebar:
        st.header("Navigation")
        st.write(f"👤 **{st.session_state.user.email}**")
        st.info(f"Role: {user_role}")
        
        # NEW: The Library is now in the Sidebar
        menu = st.radio("Go to:", ["🔬 New Analysis", "📚 My Library"])
        
        st.divider()
        if st.button("Log Out", type="primary"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    # --- MAIN AREA: NEW ANALYSIS ---
    if menu == "🔬 New Analysis":
        # Dynamic titles based on role
        if user_role == "Student":
            st.title("🎓 Student Career Alignment")
            st.markdown("Upload your CV and a target job description to find your skill gaps.")
        elif user_role in ["Organization (HR)", "Recruitment Level"]:
            st.title("🏢 Enterprise Talent Matching")
            st.markdown("Match candidate CVs against industry requirements.")
        else:
            st.title(f"📊 {user_role} Dashboard")
            st.markdown("Align Cultivated Talent Competencies with Industry Requirements.")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏢 Industry Requirements (JD)")
            jd_tab1, jd_tab2 = st.tabs(["📝 Paste Text", "📄 Upload File"])
            with jd_tab1:
                jd_text = st.text_area("Paste Job Description here:", height=250)
            with jd_tab2:
                jd_file = st.file_uploader("Upload JD (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])

        with col2:
            st.subheader("🎓 Candidate Profile (CV/Syllabus)")
            cv_tab1, cv_tab2 = st.tabs(["📝 Paste Text", "📄 Upload File"])
            with cv_tab1:
                cv_text = st.text_area("Paste Resume or Syllabus here:", height=250)
            with cv_tab2:
                cv_file = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])

        if st.button("Run Matching Algorithm", type="primary", use_container_width=True):
            final_jd, final_cv = "", ""
            
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
                            "jd_text": final_jd[:500], 
                            "cv_text": final_cv[:500],
                            "match_score": result['matching_score'],
                            "matched_skills": ", ".join(result['gap_analysis']['matched']),
                            "missing_skills": ", ".join(result['gap_analysis']['missing'])
                        }
                        supabase.table("analysis_history").insert(data_to_save).execute()
                        st.toast("✅ Analysis saved to your Library!")
                    except Exception as e:
                        st.error(f"Database Error: {e}")

                    # --- DISPLAY RESULTS ---
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
                    report_text = result["evidence"][0]
                    st.markdown(report_text)
                    
                    # NEW: Download Button for the Assessment Report
                    st.download_button(
                        label="📥 Download Full Assessment Report",
                        data=report_text,
                        file_name=f"SkillMatch_Report_{user_role}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
            else:
                st.warning("Please provide both JD and CV.")

    # --- MAIN AREA: MY LIBRARY ---
    elif menu == "📚 My Library":
        st.title("📚 My Saved Analyses")
        st.markdown(f"Viewing historical data for: **{user_role}**")
        
        try:
            # Because of RLS in Supabase, this only fetches the logged-in user's data
            response = supabase.table("analysis_history").select("*").order("created_at", desc=True).execute()
            history = response.data
            
            if not history:
                st.info("You haven't run any analyses yet.")
            else:
                for item in history:
                    with st.expander(f"Score: {item['match_score']}% | Date: {item['created_at'][:10]}"):
                        st.write(f"**JD Snippet:** {item['jd_text']}...")
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