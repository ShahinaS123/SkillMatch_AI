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

st.set_page_config(page_title="My Profile", page_icon="👤")
st.title("👤 My Profile")

# Check if user is logged in
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in to view your profile.")
    st.stop()

user = st.session_state.user
meta = user.user_metadata

# --- UPDATE NAME ---
st.subheader("Update Personal Information")
first_name = st.text_input("First Name", value=meta.get("first_name", ""))
last_name = st.text_input("Last Name", value=meta.get("last_name", ""))

if st.button("Update Name"):
    try:
        # Update in Supabase Auth
        res = supabase.auth.update_user({
            "data": {
                "first_name": first_name,
                "last_name": last_name,
                "main_role": meta.get("main_role", "Student"),
                "sub_role": meta.get("sub_role", "General")
            }
        })
        st.session_state.user = res.user
        st.success("Name updated successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Error updating name: {e}")

st.divider()

# --- UPDATE PASSWORD ---
st.subheader("Change Password")
new_password = st.text_input("New Password", type="password")
confirm_password = st.text_input("Confirm New Password", type="password")

if st.button("Update Password"):
    if new_password != confirm_password:
        st.error("Passwords do not match.")
    elif len(new_password) < 6:
        st.error("Password must be at least 6 characters.")
    else:
        try:
            supabase.auth.update_user({"password": new_password})
            st.success("Password updated successfully!")
        except Exception as e:
            st.error(f"Error updating password: {e}")
