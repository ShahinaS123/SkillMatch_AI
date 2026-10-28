import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

@st.cache_resource
def init_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_supabase()

st.set_page_config(page_title="Admin Panel", page_icon="👑")
st.title("👑 Admin Research Dashboard")

# --- SECURITY CHECK ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in.")
    st.stop()

# REPLACE THIS with your actual admin email address
ADMIN_EMAIL = "shahinashabir123@gmail.com" 

if st.session_state.user.email != ADMIN_EMAIL:
    st.error("Unauthorized access. This page is for the system administrator only.")
    st.stop()

st.success("Welcome, Admin. You have full access to the research data.")

# --- DOWNLOAD DATA ---
st.subheader("Export Thesis Dataset")
st.markdown("Download the entire database of user analyses and feedback for your statistical analysis (SPSS/Python).")

try:
    response = supabase.table("analysis_history").select("*").execute()
    data = response.data
    
    if not data:
        st.info("No data available yet.")
    else:
        df = pd.DataFrame(data)
        
        # Clean up the dates for better CSV formatting
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
        st.dataframe(df.head(10), use_container_width=True)
        st.caption(f"Showing top 10 rows. Total records: {len(df)}")
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Dataset (.csv)",
            data=csv,
            file_name="skillmatch_thesis_data.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
except Exception as e:
    st.error(f"Error fetching data: {e}")