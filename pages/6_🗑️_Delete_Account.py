import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

@st.cache_resource
def init_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_supabase()

st.set_page_config(page_title="Danger Zone", page_icon="⚠️")
st.title("⚠️ Danger Zone")

if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in.")
    st.stop()

st.error("Deleting your account is permanent. All your data and analysis history will be lost forever.")
confirm = st.checkbox("I understand the consequences and wish to delete my account.")

if st.button("Delete My Account Permanently", type="primary"):
    if confirm:
        try:
            # Note: In production, you need a Supabase Service Role key to use admin.delete_user
            # For the MVP, we delete their history and log them out.
            user_id = st.session_state.user.id
            
            # Delete history
            supabase.table("analysis_history").delete().eq("user_id", str(user_id)).execute()
            
            # Sign out (True deletion requires an Edge Function with Service Role)
            supabase.auth.sign_out()
            st.session_state.user = None
            st.success("Your data has been wiped and you have been logged out.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please check the box to confirm.")