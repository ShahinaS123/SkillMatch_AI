import streamlit as st
import os
import time
import zipfile
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import pycountry

from graph import create_graph
from file_processor import extract_text_from_file
from media_processor import transcribe_media
from nodes import analyze_media_transcript, generate_cover_letter_node, generate_interview_questions_node
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

hide_default_nav = """
<style>
    [data-testid="stSidebarNav"] { display: none; }
</style>
"""
st.markdown(hide_default_nav, unsafe_allow_html=True)

# ==========================================
# LANGUAGE DICTIONARY
# ==========================================
LANGUAGES = {
    "🇬🇧 English": {
        "title": "SkillMatch AI", "nav_analysis": "🔬 New Analysis", "nav_media": "🎥 Video/Audio Analysis",
        "nav_library": "📚 My Library", "nav_macro": "📊 Macro Dashboard", "logout": "Log Out",
        "role_label": "Role", "go_to": "Go to:", "nav_header": "Navigation", "research_tools": "🧰 Research Tools",
        "tool_sample_size": "📊 Sample Size Calculator", "tool_research_assistant": "📝 Research Assistant (Coding)",
        "dashboard_title": "General Career Alignment", "configuration": "Configuration",
        "select_analysis_type": "Select Analysis Output Type:", "standard_report": "Comprehensive AI Report (Standard)",
        "spss_data": "SPSS Statistical Data (Research)", "jd_title": "1. Industry Requirements (Job Description)",
        "cv_title": "2. Your CV / Resume", "paste_text": "Paste text here:", "paste_cv": "Paste your CV here...",
        "upload_file": "Upload File", "run_standard": "Run Standard Matching Algorithm", "run_spss": "Run & Export for SPSS",
        "recent_analyses": "🕒 Your Recent Analyses", "welcome_title": "Welcome to SkillMatch AI",
        "welcome_sub": "Bridging the gap between Engineering Education and Industry 4.0.", "tab_login": "Login",
        "tab_signup": "Sign Up", "tab_reset": "Reset Password", "email": "Email", "password": "Password",
        "login_btn": "Log In", "first_name": "First Name", "last_name": "Last Name", "select_country": "Select Country",
        "confirm_password": "Confirm Password", "main_category": "Select your main category:", "specific_level": "Select your specific level:",
        "create_account": "Create Account", "send_reset": "Send Reset Link", "personal_info": "Personal Information",
        "account_security": "Account Security", "professional_role": "Professional Role",
        "progress_title": "📈 Your Progress Over Time",
        "cover_letter": "📄 Generate Tailored Cover Letter",
        "interview_qs": "❓ Generate Interview Questions",
        "feedback_title": "💬 Provide Detailed Feedback",
        "feedback_placeholder": "What did you like? What could be improved?",
        "submit_feedback": "Submit Feedback",
        "Student": "Student", "Teacher / Professor": "Teacher / Professor", "Organization (HR)": "Organization (HR)",
        "Industry Level": "Industry Level", "Institutional Level": "Institutional Level", "Recruitment Level": "Recruitment Level",
        "Researcher": "Researcher", "General": "General", "Bachelor's Student (Instrumentation)": "Bachelor's Student (Instrumentation)",
        "Master's Student": "Master's Student", "PhD Student": "PhD Student", "Lecturer": "Lecturer",
        "Assistant Professor": "Assistant Professor", "Associate Professor": "Associate Professor", "Full Professor": "Full Professor",
        "HR Recruiter": "HR Recruiter", "Talent Acquisition": "Talent Acquisition", "HR Manager": "HR Manager",
        "R&D Scientist": "R&D Scientist", "Engineering Manager": "Engineering Manager", "Director of Innovation": "Director of Innovation",
        "University Admin": "University Admin", "Program Director": "Program Director", "Policy Maker": "Policy Maker",
        "Agency Recruiter": "Agency Recruiter", "Headhunter": "Headhunter", "Staffing Specialist": "Staffing Specialist",
        "Postdoctoral Fellow": "Postdoctoral Fellow", "Principal Investigator": "Principal Investigator", "Research Scientist": "Research Scientist",
    },
    "🇨🇳 Chinese": {
        "title": "SkillMatch AI (技能匹配)", "nav_analysis": "🔬 新分析", "nav_media": "🎥 视频/音频分析",
        "nav_library": "📚 我的库", "nav_macro": "📊 宏观仪表板", "logout": "登出",
        "role_label": "角色", "go_to": "前往：", "nav_header": "导航", "research_tools": "🧰 研究工具",
        "tool_sample_size": "📊 样本量计算器", "tool_research_assistant": "📝 研究助理 (编码)",
        "dashboard_title": "通用职业对齐", "configuration": "配置",
        "select_analysis_type": "选择分析输出类型：", "standard_report": "综合 AI 报告 (标准)",
        "spss_data": "SPSS 统计数据 (研究)", "jd_title": "1. 行业要求 (职位描述)",
        "cv_title": "2. 您的简历", "paste_text": "在此粘贴文本：", "paste_cv": "在此粘贴您的简历...",
        "upload_file": "上传文件", "run_standard": "运行标准匹配算法", "run_spss": "运行并导出至 SPSS",
        "recent_analyses": "🕒 您的最近分析", "welcome_title": "欢迎来到 SkillMatch AI",
        "welcome_sub": "弥合工程教育与工业 4.0 之间的差距。", "tab_login": "登录",
        "tab_signup": "注册", "tab_reset": "重置密码", "email": "电子邮件", "password": "密码",
        "login_btn": "登录", "first_name": "名字", "last_name": "姓氏", "select_country": "选择国家",
        "confirm_password": "确认密码", "main_category": "选择您的主要类别：", "specific_level": "选择您的具体级别：",
        "create_account": "创建账户", "send_reset": "发送重置链接", "personal_info": "个人信息",
        "account_security": "账户安全", "professional_role": "专业角色",
        "progress_title": "📈 您的进度跟踪",
        "cover_letter": "📄 生成定制求职信",
        "interview_qs": "❓ 生成面试问题",
        "feedback_title": "💬 提供详细反馈",
        "feedback_placeholder": "您喜欢什么？有什么可以改进的？",
        "submit_feedback": "提交反馈",
        "Student": "学生", "Teacher / Professor": "教师/教授", "Organization (HR)": "组织 (人力资源)",
        "Industry Level": "行业级别", "Institutional Level": "机构级别", "Recruitment Level": "招聘级别",
        "Researcher": "研究员", "General": "通用", "Bachelor's Student (Instrumentation)": "本科生 (仪器)",
        "Master's Student": "硕士生", "PhD Student": "博士生", "Lecturer": "讲师",
        "Assistant Professor": "助理教授", "Associate Professor": "副教授", "Full Professor": "正教授",
        "HR Recruiter": "人力资源招聘人员", "Talent Acquisition": "人才招聘", "HR Manager": "人力资源经理",
        "R&D Scientist": "研发科学家", "Engineering Manager": "工程经理", "Director of Innovation": "创新总监",
        "University Admin": "大学管理员", "Program Director": "项目主任", "Policy Maker": "政策制定者",
        "Agency Recruiter": "中介招聘人员", "Headhunter": "猎头", "Staffing Specialist": "人员配置专家",
        "Postdoctoral Fellow": "博士后研究员", "Principal Investigator": "首席研究员", "Research Scientist": "研究科学家",
    }
}

if "language" not in st.session_state:
    st.session_state.language = "🇬🇧 English"

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

@st.cache_data
def get_country_list():
    countries = [country.name for country in pycountry.countries]
    if "Israel" in countries:
        countries.remove("Israel")
    return sorted(countries)

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
    t = LANGUAGES[st.session_state.language]
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(logo_path):
            st.image(logo_path, width="stretch")
            
        st.title(t["welcome_title"])
        st.markdown(t["welcome_sub"])
        
        tab1, tab2, tab3 = st.tabs([t["tab_login"], t["tab_signup"], t["tab_reset"]])
        
        with tab1:
            email = st.text_input(t["email"], key="login_email")
            password = st.text_input(t["password"], type="password", key="login_pass")
            if st.button(t["login_btn"], type="primary", use_container_width=True):
                try:
                    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = response.user
                    st.session_state.chat_messages = [] 
                    st.rerun() 
                except Exception as e:
                    st.error(f"Login failed: {e}")
                    
        with tab2:
            st.markdown(f"**{t['personal_info']}**")
            col_first, col_last = st.columns(2)
            with col_first:
                first_name = st.text_input(t["first_name"], key="signup_first")
            with col_last:
                last_name = st.text_input(t["last_name"], key="signup_last")
            
            new_email = st.text_input(t["email"], key="signup_email")
            
            country_list = get_country_list()
            default_idx = country_list.index("Pakistan") if "Pakistan" in country_list else 0
            selected_country = st.selectbox(t["select_country"], country_list, index=default_idx)
            
            st.markdown(f"**{t['account_security']}**")
            new_password = st.text_input(t["password"], type="password", key="signup_pass")
            confirm_password = st.text_input(t["confirm_password"], type="password", key="signup_pass_confirm")
            
            st.markdown(f"**{t['professional_role']}**")
            translated_main_roles = [t.get(k, k) for k in ROLES.keys()]
            selected_main_role_trans = st.selectbox(t["main_category"], translated_main_roles, key="signup_main_role")
            main_role = list(ROLES.keys())[translated_main_roles.index(selected_main_role_trans)]
            
            translated_sub_roles = [t.get(sr, sr) for sr in ROLES[main_role]]
            selected_sub_role_trans = st.selectbox(t["specific_level"], translated_sub_roles, key="signup_sub_role")
            sub_role = ROLES[main_role][translated_sub_roles.index(selected_sub_role_trans)]
            
            if st.button(t["create_account"], use_container_width=True):
                if not first_name or not last_name or not new_email or not new_password:
                    st.error("Please fill in all required fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        response = supabase.auth.sign_up({
                            "email": new_email, 
                            "password": new_password,
                            "options": {"data": {
                                "first_name": first_name,
                                "last_name": last_name,
                                "country": selected_country,
                                "main_role": main_role, 
                                "sub_role": sub_role
                            }}
                        })
                        st.success(f"Account created for {first_name} {last_name}! Please check your email to verify.")
                    except Exception as e:
                        st.error(f"Signup failed: {e}")
                    
        with tab3:
            reset_email = st.text_input(t["email"], key="reset_email")
            if st.button(t["send_reset"], use_container_width=True):
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
    first_name = user_meta.get("first_name", "User")
    last_name = user_meta.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip()
    
    t = LANGUAGES[st.session_state.language]
    translated_main_role = t.get(main_role, main_role)
    translated_sub_role = t.get(sub_role, sub_role)

    with st.sidebar:
        if os.path.exists(logo_path):
            st.image(logo_path, width="stretch")
            
        st.header(t["nav_header"])
        st.page_link("pages/4_👤_My_Profile.py", label=f"👤 **{full_name}**")
        st.info(f"{t['role_label']}: {translated_sub_role} ({translated_main_role})")
        
        menu_options = [t["nav_analysis"], t["nav_media"], t["nav_library"]]
        if main_role in ["Researcher", "Institutional Level"]:
            menu_options.append(t["nav_macro"])
            
        menu = st.radio(t["go_to"], menu_options)
        
        st.divider()
        st.header(t["research_tools"])
        st.page_link("pages/1_📊_Sample_Size_Calculator.py", label=t["tool_sample_size"])
        st.page_link("pages/3_📝_Research_Assistant.py", label=t["tool_research_assistant"])
        
        # ADMIN LINK
        if st.session_state.user.email == "shahinashabir123@gmail.com": # REPLACE WITH YOUR EMAIL
            st.page_link("pages/5_👑_Admin_Panel.py", label="👑 Admin Dashboard")
        
        st.divider()
        if st.button(t["logout"], type="primary", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.chat_messages = [] 
            st.rerun()

    # --- MAIN AREA: NEW ANALYSIS (TEXT/PDF) ---
    if menu == t["nav_analysis"]:
        st.title(f"🎓 {translated_sub_role} {t['dashboard_title']}")

        st.markdown(f"### ⚙️ {t['configuration']}")
        analysis_type = st.radio(t["select_analysis_type"], [t["standard_report"], t["spss_data"]], horizontal=True)

        st.divider()
        st.subheader(t["jd_title"])
        jd_tab1, jd_tab2 = st.tabs([f"📝 {t['paste_text']}", f"📄 {t['upload_file']}"])
        with jd_tab1:
            jd_text = st.text_area(t["paste_text"], height=150)
        with jd_tab2:
            jd_file = st.file_uploader(f"Upload (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])

        st.divider()
        st.subheader(t["cv_title"])
        
        # --- ZIP UPLOAD FOR HR ---
        if main_role in ["Organization (HR)", "Recruitment Level"]:
            upload_type = st.radio("Upload Type", ["Individual Files", "ZIP Archive"], horizontal=True)
            cv_files = []
            cv_text = ""
            
            if upload_type == "ZIP Archive":
                zip_file = st.file_uploader("Upload ZIP file containing multiple resumes", type=["zip"])
                if zip_file:
                    with zipfile.ZipFile(zip_file, 'r') as z:
                        for filename in z.namelist():
                            if filename.endswith(('.pdf', '.txt')):
                                with z.open(filename) as f:
                                    file_obj = io.BytesIO(f.read())
                                    file_obj.name = filename
                                    cv_files.append(file_obj)
            else:
                cv_files = st.file_uploader("Upload Multiple Resumes (PDF/TXT)", type=["pdf", "txt"], accept_multiple_files=True)
        else:
            cv_tab1, cv_tab2 = st.tabs([f"📝 {t['paste_text']}", f"📄 {t['upload_file']}"])
            with cv_tab1:
                cv_text = st.text_area(t["paste_cv"], height=150)
            with cv_tab2:
                cv_file = st.file_uploader(f"Upload (PDF/TXT)", type=["pdf", "txt"])
            cv_files = [cv_file] if cv_file else []

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            run_ai = st.button(t["run_standard"], type="primary", use_container_width=True)
        with col_btn2:
            run_spss = st.button(t["run_spss"], type="secondary", use_container_width=True)

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
                            
                            top_missing = result['gap_analysis']['missing'][0] if result['gap_analysis']['missing'] else "None"
                            
                            leaderboard.append({
                                "Candidate Name": cv_file.name,
                                "Match Score (%)": result['matching_score'],
                                "Top Missing Skill": top_missing,
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
                        
                        if run_spss:
                            st.subheader("📊 SPSS Statistical Data Export")
                            spss_data = pd.DataFrame({
                                "Candidate_ID": [str(st.session_state.user.id)[:8]],
                                "Match_Score": [result['matching_score']],
                                "Matched_Count": [len(result['gap_analysis']['matched'])],
                                "Missing_Count": [len(result['gap_analysis']['missing'])],
                                "Matched_Skills": [", ".join(result['gap_analysis']['matched'])],
                                "Missing_Skills": [", ".join(result['gap_analysis']['missing'])]
                            })
                            st.dataframe(spss_data, use_container_width=True)
                            c1, c2 = st.columns(2)
                            with c1:
                                csv = spss_data.to_csv(index=False).encode('utf-8')
                                st.download_button("📥 Download Data for SPSS (.csv)", data=csv, file_name="spss_data_export.csv", mime="text/csv", use_container_width=True)
                            with c2:
                                with st.spinner("Generating SPSS Syntax..."):
                                    syntax = generate_spss_syntax(result['matching_score'], result['gap_analysis']['matched'], result['gap_analysis']['missing'])
                                    st.download_button("📥 Download SPSS Syntax (.sps)", data=syntax, file_name="analysis_syntax.sps", mime="text/plain", use_container_width=True)
                            st.code(syntax, language="text")
                            
                        else:
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
                            
                            # --- COVER LETTER & INTERVIEW QUESTIONS ---
                            st.divider()
                            st.subheader("✨ AI Career Tools")
                            col_tool1, col_tool2 = st.columns(2)
                            
                            with col_tool1:
                                if st.button(t["cover_letter"], use_container_width=True):
                                    with st.spinner("Drafting Cover Letter..."):
                                        cl = generate_cover_letter_node(final_cv, final_jd, result['gap_analysis']['matched'])
                                        st.text_area("Your Cover Letter", cl, height=300)
                            
                            with col_tool2:
                                if st.button(t["interview_qs"], use_container_width=True):
                                    with st.spinner("Generating Interview Questions..."):
                                        qs = generate_interview_questions_node(final_cv, final_jd, result['gap_analysis']['missing'])
                                        st.text_area("Interview Prep", qs, height=300)

                            st.divider()
                            st.subheader("📊 AI Career & Market Strategy")
                            report_text = result["evidence"][0]
                            st.markdown(report_text)
                            
                            matched_str = ", ".join(result['gap_analysis']['matched'])
                            missing_str = ", ".join(result['gap_analysis']['missing'])
                            
                            try:
                                pdf_bytes = generate_pdf_report(report_text=report_text, score=result['matching_score'], matched_skills=matched_str, missing_skills=missing_str)
                                st.download_button("📥 Download Full Report (PDF)", data=pdf_bytes, file_name="Instrumentation_Analysis.pdf", mime="application/pdf", use_container_width=True)
                            except Exception as e:
                                st.error(f"Could not generate PDF: {e}")
                            
                            # --- DETAILED FEEDBACK ---
                            st.divider()
                            st.subheader(t["feedback_title"])
                            feedback_text = st.text_area(t["feedback_placeholder"])
                            if st.button(t["submit_feedback"]):
                                if inserted_id:
                                    try:
                                        supabase.table("analysis_history").update({"feedback_text": feedback_text}).eq("id", inserted_id).execute()
                                        st.toast("✅ Feedback submitted successfully! Thank you.")
                                    except Exception as e:
                                        st.error(f"Could not submit feedback: {e}")

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

    # --- MAIN AREA: VIDEO/AUDIO ANALYSIS ---
    elif menu == t["nav_media"]:
        st.title("🎥 Interview & Presentation Analysis")
        st.markdown("Upload a short video or audio recording of yourself presenting a project or answering a technical question. The AI will analyze your communication clarity, technical explanation, and confidence.")

        uploaded_media = st.file_uploader("Upload Video (MP4) or Audio (MP3/WAV)", type=["mp4", "mov", "mp3", "wav", "m4a"])

        if uploaded_media is not None:
            st.video(uploaded_media) if uploaded_media.type.startswith("video/") else st.audio(uploaded_media)

            if st.button("Analyze Communication Skills", type="primary", use_container_width=True):
                with st.status("Processing Media...", expanded=True) as status:
                    st.write("Extracting audio and transcribing speech...")
                    
                    transcript = transcribe_media(uploaded_media)
                    
                    if transcript.startswith("Error"):
                        st.error(transcript)
                        status.update(label="Transcription Failed", state="error")
                    else:
                        st.write("Transcript generated. Running AI analysis...")
                        
                        analysis_report = analyze_media_transcript(transcript)
                        
                        status.update(label="Analysis Complete!", state="complete", expanded=False)
                        
                        st.divider()
                        st.subheader("📝 Transcription")
                        with st.expander("View Raw Transcript"):
                            st.write(transcript)
                            
                        st.subheader("📊 Communication Analysis")
                        st.markdown(analysis_report)
                        
                        try:
                            db_utils.save_analysis_record(
                                supabase_client=supabase, user_id=st.session_state.user.id, 
                                jd_text="Video/Audio Interview Analysis", cv_text=transcript[:500], score=100.0, 
                                matched_skills=["Communication"], missing_skills=["N/A"], 
                                report_text=analysis_report
                            )
                            st.toast("✅ Media Analysis saved to your Library!")
                        except Exception as db_err:
                            st.error(f"⚠️ Failed to save to database: {db_err}")

    # --- MAIN AREA: MY LIBRARY ---
    elif menu == t["nav_library"]:
        st.title("📚 My Saved Analyses")
        
        # --- NEW: PROGRESS CHART ---
        st.subheader(t["progress_title"])
        try:
            # Fetch data for chart
            chart_response = supabase.table("analysis_history")\
                .select("created_at, match_score")\
                .eq("user_id", str(st.session_state.user.id))\
                .order("created_at").execute()
                
            chart_data = chart_response.data
            if chart_data and len(chart_data) > 1:
                df_chart = pd.DataFrame(chart_data)
                df_chart['created_at'] = pd.to_datetime(df_chart['created_at']).dt.date
                fig_line = px.line(df_chart, x='created_at', y='match_score', markers=True, 
                                   labels={'created_at': 'Date', 'match_score': 'Match Score (%)'},
                                   title="Skill Match Score Trend")
                fig_line.update_layout(yaxis_range=[0,100])
                st.plotly_chart(fig_line, use_container_width=True)
            elif chart_data and len(chart_data) == 1:
                st.info("Run at least 2 analyses to see your progress chart.")
            else:
                st.info("No data for progress chart yet.")
        except Exception as e:
            st.warning(f"Could not load progress chart: {e}")

        st.divider()
        
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
    elif menu == t["nav_macro"]:
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
# 4. ROUTER (GLOBAL LAYOUT WITH LANGUAGE SELECTOR)
# ==========================================
# Place the language selector at the very top of the page, before anything else
col_spacer, col_lang = st.columns([8, 2])
with col_lang:
    st.session_state.language = st.selectbox(
        "🌐 Language", 
        list(LANGUAGES.keys()), 
        index=list(LANGUAGES.keys()).index(st.session_state.language),
        label_visibility="collapsed"
    )

# Now check auth and route
if st.session_state.user is None:
    show_auth_screen()
else:
    show_main_app()