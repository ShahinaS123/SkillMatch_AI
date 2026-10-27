import streamlit as st
import os
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from graph import create_graph
from file_processor import extract_text_from_file
from pdf_generator import generate_pdf_report
import db_utils

load_dotenv()

# ==========================================
# 0. PAGE CONFIG & LOGO SETUP
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(current_dir, "logo.png")
page_icon = logo_path if os.path.exists(logo_path) else "⚙️"
st.set_page_config(page_title="SkillMatch AI", layout="wide", page_icon=page_icon)

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
if "page" not in st.session_state:
    st.session_state.page = 1
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "latest_analysis_context" not in st.session_state:
    st.session_state.latest_analysis_context = "No recent analysis available."

chat_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.7)

ROLES = {
    "Student": ["Bachelor's Student (Instrumentation)", "Master's Student", "PhD Student"],
    "Teacher / Professor": ["Lecturer", "Assistant Professor", "Associate Professor", "Full Professor"],
    "Organization (HR)": ["HR Recruiter", "Talent Acquisition", "HR Manager"],
    "Industry Level": ["R&D Scientist", "Engineering Manager", "Director of Innovation"],
    "Institutional Level": ["University Admin", "Program Director", "Policy Maker"],
    "Recruitment Level": ["Agency Recruiter", "Headhunter", "Staffing Specialist"],
    "Researcher": ["Postdoctoral Fellow", "Principal Investigator", "Research Scientist"]
}

# ==========================================
# HELPER: T-SHAPED RADAR CHART
# ==========================================
def create_radar_chart(matched_count, missing_count):
    total = matched_count + missing_count if (matched_count + missing_count) > 0 else 1
    score_pct = (matched_count / total) * 100
    categories = ['Hardware (Circuits)', 'Software (Coding)', 'Theory (Physics/Math)', 'Instrumentation (Sensors)']
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[score_pct, score_pct-10, score_pct+5, score_pct], 
        theta=categories, fill='toself', name='Candidate Profile',
        line_color='#0066cc', fillcolor='rgba(0, 102, 204, 0.3)'
    ))
    fig.add_trace(go.Scatterpolar(
        r=[100, 100, 100, 100], theta=categories, fill='toself', 
        name='Industry Requirement', line_color='#dc3545', fillcolor='rgba(220, 53, 69, 0.1)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True, margin=dict(t=30, b=30, l=30, r=30), height=300
    )
    return fig

def run_graph_with_retry(graph_app, inputs, max_retries=3):
    for attempt in range(max_retries):
        try:
            return graph_app.invoke(inputs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(3)
            st.warning(f"API hiccup detected. Retrying... (Attempt {attempt + 2}/{max_retries})")

# NEW HELPER: Generate SPSS Syntax
def generate_spss_syntax(score, matched_skills, missing_skills):
    prompt = ChatPromptTemplate.from_template(
        """You are an expert statistician. Write a valid IBM SPSS Syntax script (.sps) for a PhD researcher.
        The researcher has the following data for a single candidate:
        - Match Score (Scale): {score}
        - Matched Skills Count (Scale): {matched_count}
        - Missing Skills Count (Scale): {missing_count}

        Write SPSS syntax to:
        1. Create a dataset with these variables.
        2. Run a Descriptive Statistics command (FREQUENCIES or DESCRIPTIVES).
        3. Run a Correlation command between Match Score and Missing Skills Count.
        
        Only output the raw SPSS syntax. Do not output any markdown formatting or explanations.
        """
    )
    chain = prompt | chat_llm
    result = chain.invoke({
        "score": score,
        "matched_count": len(matched_skills),
        "missing_count": len(missing_skills)
    })
    return result.content

# ==========================================
# 2. LOGIN / SIGNUP / RESET SCREEN
# ==========================================
def show_auth_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(logo_path):
            st.image(logo_path, width="stretch")
            
        st.title("Welcome to SkillMatch AI")
        st.markdown("Bridging the gap between Engineering Education and Industry 4.0.")
        
        tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Reset Password"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In", type="primary", use_container_width=True):
                try:
                    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = response.user
                    st.session_state.chat_messages = [] 
                    st.rerun() 
                except Exception as e:
                    st.error(f"Login failed: {e}")
                    
        with tab2:
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_pass")
            main_role = st.selectbox("Select your main category:", list(ROLES.keys()), key="signup_main_role")
            sub_role = st.selectbox("Select your specific level:", ROLES[main_role], key="signup_sub_role")
            
            if st.button("Create Account", use_container_width=True):
                try:
                    response = supabase.auth.sign_up({
                        "email": new_email, "password": new_password,
                        "options": {"data": {"main_role": main_role, "sub_role": sub_role}}
                    })
                    st.success(f"Account created as {sub_role}!")
                except Exception as e:
                    st.error(f"Signup failed: {e}")
                    
        with tab3:
            reset_email = st.text_input("Enter your email:", key="reset_email")
            if st.button("Send Reset Link", use_container_width=True):
                try:
                    supabase.auth.reset_password_for_email(reset_email)
                    st.success("Password reset link sent!")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# 3. MAIN APP LOGIC
# ==========================================
def show_main_app():
    user_meta = st.session_state.user.user_metadata
    main_role = user_meta.get("main_role", "Student")
    sub_role = user_meta.get("sub_role", "General")

    with st.sidebar:
        if os.path.exists(logo_path):
            st.image(logo_path, width="stretch")
            
        st.header("Navigation")
        st.write(f"👤 **{st.session_state.user.email}**")
        st.info(f"Role: {sub_role} ({main_role})")
        
        menu_options = ["🔬 New Analysis", "📚 My Library"]
        if main_role in ["Researcher", "Institutional Level"]:
            menu_options.append("📊 Macro Dashboard")
            
        menu = st.radio("Go to:", menu_options)
        
        st.divider()
        if st.button("Log Out", type="primary", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.chat_messages = [] 
            st.rerun()

    # --- MAIN AREA: NEW ANALYSIS ---
    if menu == "🔬 New Analysis":
        if main_role == "Teacher / Professor":
            st.title("📚 Curriculum Audit Mode (Instrumentation)")
            label_1 = "1. Industry Requirements (Target JD)"
            label_2 = "2. Your Course Syllabus"
            placeholder_2 = "Paste Course Syllabus here..."
        elif main_role == "Student":
            st.title(f"🎓 {sub_role} Career Alignment")
            label_1 = "1. Industry Requirements (Job Description)"
            label_2 = "2. Your CV / Resume"
            placeholder_2 = "Paste your CV here..."
        else:
            st.title(f"📊 {sub_role} Dashboard")
            label_1 = "1. Industry Requirements (Job Description)"
            label_2 = "2. Candidate Profile / Syllabus"
            placeholder_2 = "Paste Resume or Syllabus here..."

        # --- NEW: ANALYSIS TYPE SELECTOR ---
        st.markdown("### ⚙️ Configuration")
        analysis_type = st.radio(
            "Select Analysis Output Type:",
            ["Comprehensive AI Report (Standard)", "SPSS Statistical Data (Research)"],
            horizontal=True
        )

        st.divider()

        st.subheader(label_1)
        jd_tab1, jd_tab2 = st.tabs(["📝 Paste Text", "📄 Upload File"])
        with jd_tab1:
            jd_text = st.text_area("Paste text here:", height=150)
        with jd_tab2:
            jd_file = st.file_uploader("Upload (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])

        st.divider()
        st.subheader(label_2)
        
        if main_role in ["Organization (HR)", "Recruitment Level"]:
            cv_files = st.file_uploader("Upload Multiple Resumes (PDF/TXT)", type=["pdf", "txt"], accept_multiple_files=True)
            cv_text = ""
        else:
            cv_tab1, cv_tab2 = st.tabs(["📝 Paste Text", "📄 Upload File"])
            with cv_tab1:
                cv_text = st.text_area(placeholder_2, height=150)
            with cv_tab2:
                cv_file = st.file_uploader("Upload (PDF/TXT)", type=["pdf", "txt"])
            cv_files = [cv_file] if cv_file else []

        # --- NEW: TWO BUTTONS ---
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            run_ai = st.button("Run Standard Matching Algorithm", type="primary", use_container_width=True)
        with col_btn2:
            run_spss = st.button("Run & Export for SPSS", type="secondary", use_container_width=True)

        if run_ai or run_spss:
            final_jd = ""
            if jd_file: final_jd = extract_text_from_file(jd_file)
            elif jd_text: final_jd = jd_text

            if not final_jd or (not cv_files and not cv_text):
                st.warning("Please provide both the Requirement and the Profile.")
            else:
                with st.status("AI Agents are analyzing data...", expanded=True) as status:
                    st.write("Extracting requirements...")
                    app = create_graph()
                    
                    # Batch processing (HR) logic remains the same
                    if main_role in ["Organization (HR)", "Recruitment Level"] and cv_files:
                        leaderboard = []
                        progress_bar = st.progress(0)
                        total_files = len(cv_files)
                        
                        for i, cv_file in enumerate(cv_files):
                            st.write(f"Analyzing {cv_file.name}...")
                            final_cv = extract_text_from_file(cv_file)
                            
                            input_data = {
                                "job_description": final_jd, "candidate_profile": final_cv,
                                "extracted_jd_skills": [], "extracted_candidate_skills": [],
                                "matching_score": 0.0, "gap_analysis": {}, "evidence": []
                            }
                            
                            result = run_graph_with_retry(app, input_data)
                            
                            try:
                                db_utils.save_analysis_record(
                                    supabase_client=supabase, user_id=st.session_state.user.id, 
                                    jd_text=final_jd, cv_text=final_cv, score=result['matching_score'], 
                                    matched_skills=result['gap_analysis']['matched'], missing_skills=result['gap_analysis']['missing'], 
                                    report_text=result["evidence"][0]
                                )
                            except Exception as db_err:
                                st.error(f"⚠️ Failed to save to database: {db_err}")
                            
                            leaderboard.append({
                                "Candidate Name": cv_file.name,
                                "Match Score (%)": result['matching_score'],
                                "Missing Skills Count": len(result['gap_analysis']['missing'])
                            })
                            progress_bar.progress((i + 1) / total_files)
                        
                        progress_bar.empty()
                        status.update(label="Batch Analysis Complete!", state="complete", expanded=False)
                        st.divider()
                        st.subheader("🏆 Candidate Leaderboard")
                        leaderboard = sorted(leaderboard, key=lambda x: x["Match Score (%)"], reverse=True)
                        st.dataframe(leaderboard, use_container_width=True)
                        st.rerun()

                    # Single processing logic
                    else:
                        final_cv = cv_text
                        if cv_files and cv_files[0]: final_cv = extract_text_from_file(cv_files[0])
                        
                        input_data = {
                            "job_description": final_jd, "candidate_profile": final_cv,
                            "extracted_jd_skills": [], "extracted_candidate_skills": [],
                            "matching_score": 0.0, "gap_analysis": {}, "evidence": []
                        }
                        
                        result = run_graph_with_retry(app, input_data)
                        
                        st.session_state.latest_analysis_context = f"""
                        Match Score: {result['matching_score']}%
                        Matched Skills: {', '.join(result['gap_analysis']['matched'])}
                        Missing Skills: {', '.join(result['gap_analysis']['missing'])}
                        """
                        
                        inserted_id = None
                        try:
                            inserted_id = db_utils.save_analysis_record(
                                supabase_client=supabase, user_id=st.session_state.user.id, 
                                jd_text=final_jd, cv_text=final_cv, score=result['matching_score'], 
                                matched_skills=result['gap_analysis']['matched'], missing_skills=result['gap_analysis']['missing'], 
                                report_text=result["evidence"][0]
                            )
                            st.toast("✅ Analysis successfully saved to Library!")
                        except Exception as db_err:
                            st.error(f"⚠️ Failed to save to database: {db_err}")
                        
                        status.update(label="Analysis Complete!", state="complete", expanded=False)
                        st.divider()
                        
                        # --- DISPLAY RESULTS ---
                        if run_spss:
                            # SPSS SPECIFIC VIEW
                            st.subheader("📊 SPSS Statistical Data Export")
                            st.info("Below is the raw data formatted for SPSS and the auto-generated Syntax file.")
                            
                            # Create DataFrame
                            spss_data = pd.DataFrame({
                                "Candidate_ID": [str(st.session_state.user.id)[:8]],
                                "Match_Score": [result['matching_score']],
                                "Matched_Count": [len(result['gap_analysis']['matched'])],
                                "Missing_Count": [len(result['gap_analysis']['missing'])],
                                "Matched_Skills": [", ".join(result['gap_analysis']['matched'])],
                                "Missing_Skills": [", ".join(result['gap_analysis']['missing'])]
                            })
                            
                            st.dataframe(spss_data, use_container_width=True)
                            
                            # Export buttons
                            c1, c2 = st.columns(2)
                            with c1:
                                csv = spss_data.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="📥 Download Data for SPSS (.csv)",
                                    data=csv,
                                    file_name="spss_data_export.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                            with c2:
                                # Generate SPSS Syntax
                                with st.spinner("Generating SPSS Syntax..."):
                                    syntax = generate_spss_syntax(
                                        result['matching_score'], 
                                        result['gap_analysis']['matched'], 
                                        result['gap_analysis']['missing']
                                    )
                                    st.download_button(
                                        label="📥 Download SPSS Syntax (.sps)",
                                        data=syntax,
                                        file_name="analysis_syntax.sps",
                                        mime="text/plain",
                                        use_container_width=True
                                    )
                            st.code(syntax, language="text")
                            
                        else:
                            # STANDARD VIEW (UI + PDF)
                            col_score, col_chart = st.columns([1, 2])
                            with col_score:
                                st.metric("Overall Matching Score", f"{result['matching_score']}%")
                                st.info("T-Shaped Skill Balance")
                            with col_chart:
                                radar_fig = create_radar_chart(len(result['gap_analysis']['matched']), len(result['gap_analysis']['missing']))
                                st.plotly_chart(radar_fig, use_container_width=True, key="radar_chart", config={'displayModeBar': False})

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
                            
                            matched_str = ", ".join(result['gap_analysis']['matched'])
                            missing_str = ", ".join(result['gap_analysis']['missing'])
                            
                            try:
                                pdf_bytes = generate_pdf_report(
                                    report_text=report_text, score=result['matching_score'],
                                    matched_skills=matched_str, missing_skills=missing_str
                                )
                                st.download_button(
                                    label="📥 Download Full Report (PDF)", data=pdf_bytes,
                                    file_name="Instrumentation_Analysis.pdf", mime="application/pdf", use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Could not generate PDF: {e}")
                            
                            st.divider()
                            st.write("**Was this AI report accurate?**")
                            feedback = st.feedback("thumbs")
                            if feedback is not None and inserted_id:
                                try:
                                    rating_value = 1 if feedback == 1 else 0
                                    db_utils.update_feedback(supabase, inserted_id, rating_value)
                                    st.toast("Feedback saved!")
                                except Exception as e:
                                    st.error(f"Failed to save feedback: {e}")

        # DASHBOARD CHATBOT
        st.write("") 
        with st.expander("💬 Ask the AI Career Assistant", expanded=False):
            st.write("Have questions about your gaps, interview prep, or learning resources? Ask below.")
            
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("Type your question here..."):
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            system_prompt = f"""You are an expert academic advisor and career coach for Instrumentation and Engineering students.
                            Use the following context about the user's latest analysis to answer their question. 
                            If they ask for learning resources, suggest specific platforms (Coursera, edX, IEEE). Be encouraging, professional, and actionable.
                            
                            CONTEXT:
                            {st.session_state.latest_analysis_context}
                            """
                            
                            chat_prompt = ChatPromptTemplate.from_messages([
                                ("system", system_prompt),
                                ("human", prompt)
                            ])
                            
                            chain = chat_prompt | chat_llm
                            response = chain.invoke({"prompt": prompt})
                            
                            st.markdown(response.content)
                            st.session_state.chat_messages.append({"role": "assistant", "content": response.content})
                        except Exception as e:
                            st.error(f"Error communicating with AI: {e}")

    # --- MAIN AREA: MY LIBRARY ---
    elif menu == "📚 My Library":
        st.title("📚 My Saved Analyses")
        
        col_title, col_clear = st.columns([3, 1])
        with col_title:
            st.markdown("Review your historical reports and track your skill growth.")
        with col_clear:
            if st.button("🗑️ Clear Entire History", type="secondary", use_container_width=True):
                try:
                    res = supabase.table("analysis_history").delete().eq("user_id", str(st.session_state.user.id)).execute()
                    if len(res.data) > 0:
                        st.success(f"Deleted {len(res.data)} records successfully!")
                        st.rerun()
                    else:
                        st.warning("No records deleted. Check Supabase RLS delete policy.")
                except Exception as e:
                    st.error(f"Could not clear history: {e}")

        st.divider()
        
        try:
            items_per_page = 5
            offset = (st.session_state.page - 1) * items_per_page
            
            response = supabase.table("analysis_history")\
                .select("*").order("created_at", desc=True).range(offset, offset + items_per_page - 1).execute()
            
            history = response.data
            
            if not history:
                st.info("No analyses found on this page.")
            else:
                for idx, item in enumerate(history):
                    rating_icon = "👍" if item.get('user_rating') == 1 else ("👎" if item.get('user_rating') == 0 else "")
                    
                    with st.expander(f"📊 Score: {item['match_score']}% | Date: {item['created_at'][:10]} {rating_icon}"):
                        
                        matched_list = [s.strip() for s in item['matched_skills'].split(",")] if item['matched_skills'] else []
                        missing_list = [s.strip() for s in item['missing_skills'].split(",")] if item['missing_skills'] else []
                        
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.metric("Overall Match", f"{item['match_score']}%")
                            st.caption(f"Missing {len(missing_list)} skills")
                        with col2:
                            radar_fig = create_radar_chart(len(matched_list), len(missing_list))
                            st.plotly_chart(radar_fig, use_container_width=True, key=f"radar_{item['id']}_{idx}", config={'displayModeBar': False})
                        
                        with st.popover("View All Matched & Missing Skills"):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.success("✅ Matched Skills")
                                for s in matched_list: st.write(f"- {s}")
                            with c2:
                                st.error("⚠️ Missing Skills")
                                for s in missing_list: st.write(f"- {s}")
                        
                        if item.get('report_text'):
                            st.divider()
                            report = item['report_text']
                            
                            tab_gap, tab_market, tab_deliverables = st.tabs([
                                "📈 Gap Analysis & Action Plan", "🌍 Market Strategy", "🎯 Key Deliverables"
                            ])
                            
                            with tab_gap:
                                if "📈 Areas for Improvement" in report:
                                    st.markdown(report.split("📈 Areas for Improvement")[1].split("🎯 Market Targeting Strategy")[0])
                                else: st.info("No gap analysis found.")
                            
                            with tab_market:
                                if "🎯 Market Targeting Strategy" in report:
                                    st.markdown(report.split("🎯 Market Targeting Strategy")[1].split("Key Deliverables to Showcase")[0])
                                else: st.info("No market strategy found.")
                            
                            with tab_deliverables:
                                if "Key Deliverables to Showcase" in report:
                                    st.info(report.split("Key Deliverables to Showcase")[1].split("Strategic Job‑Search Recommendations")[0])
                                else: st.info("No deliverables found.")
                            
                            @st.cache_data(show_spinner=False)
                            def cached_pdf(report_text, score, matched_str, missing_str):
                                return generate_pdf_report(report_text, score, matched_str, missing_str)
                            
                            matched_str = ", ".join(matched_list)
                            missing_str = ", ".join(missing_list)
                            
                            try:
                                pdf_bytes = cached_pdf(report, item['match_score'], matched_str, missing_str)
                                st.download_button(
                                    label="📥 Download Full Report (PDF)", data=pdf_bytes,
                                    file_name=f"Instrumentation_Report_{item['id']}.pdf", mime="application/pdf",
                                    key=f"download_{item['id']}", use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Could not generate PDF: {e}")
                        
                        st.divider()
                        col_feedback, col_delete = st.columns([4, 1])
                        
                        with col_feedback:
                            st.write("**Was this analysis helpful?**")
                            feedback = st.feedback("thumbs", key=f"fb_{item['id']}")
                            if feedback is not None:
                                try:
                                    db_utils.update_feedback(supabase, item['id'], 1 if feedback == 1 else 0)
                                    st.toast("Feedback saved!")
                                except Exception as e:
                                    st.error(f"Failed to save feedback: {e}")
                                
                        with col_delete:
                            if st.button("🗑️ Delete", key=f"delete_{item['id']}", type="secondary"):
                                try:
                                    res = supabase.table("analysis_history").delete().eq("id", item['id']).eq("user_id", str(st.session_state.user.id)).execute()
                                    if len(res.data) > 0:
                                        st.toast("Analysis deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Delete failed: Check Supabase RLS delete policy.")
                                except Exception as e:
                                    st.error(f"Could not delete: {e}")

            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("⬅️ Previous") and st.session_state.page > 1:
                    st.session_state.page -= 1
                    st.rerun()
            with c3:
                if st.button("Next ➡️"):
                    st.session_state.page += 1
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Could not load library: {e}")

    # --- MAIN AREA: MACRO DASHBOARD ---
    elif menu == "📊 Macro Dashboard":
        st.title("📊 Macro-Level Skill Gap Analysis")
        st.markdown("Aggregated data across all users. Perfect for institutional reporting.")
        
        try:
            response = supabase.table("analysis_history").select("missing_skills").execute()
            data = response.data
            
            if not data:
                st.info("Not enough data yet.")
            else:
                all_missing = []
                for row in data:
                    if row['missing_skills']:
                        all_missing.extend([s.strip() for s in row['missing_skills'].split(",")])
                
                counts = Counter(all_missing).most_common(10)
                
                if counts:
                    skills = [c[0] for c in counts]
                    frequencies = [c[1] for c in counts]
                    
                    fig = px.bar(
                        x=frequencies, y=skills, orientation='h',
                        labels={'x': 'Number of Times Missing', 'y': 'Skill'},
                        title="Top 10 Missing Skills Across All Users"
                    )
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True, key="macro_chart", config={'displayModeBar': False})
        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# 4. ROUTER
# ==========================================
if st.session_state.user is None:
    show_auth_screen()
else:
    show_main_app()