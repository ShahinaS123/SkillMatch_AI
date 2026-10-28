import streamlit as st
import math

st.set_page_config(page_title="Sample Size Calculator", page_icon="📊")
st.title("📊 Statistical Sample Size Calculator")

tab1, tab2 = st.tabs(["Yamane (Proportions)", "Cochran (Surveys)"])

with tab1:
    st.subheader("Yamane's Formula")
    N = st.number_input("Population Size (N)", min_value=1, value=1000, step=50)
    e = st.slider("Margin of Error (e)", min_value=0.01, max_value=0.10, value=0.05, step=0.01)
    if st.button("Calculate Yamane Sample Size"):
        n = N / (1 + N * (e ** 2))
        st.success(f"Required Sample Size: **{math.ceil(n)}**")

with tab2:
    st.subheader("Cochran's Formula")
    z = st.selectbox("Z-score", [1.645, 1.96, 2.576], format_func=lambda x: f"{x}")
    p = st.slider("Estimated Proportion (p)", min_value=0.1, max_value=0.9, value=0.5)
    e = st.slider("Margin of Error (e)", min_value=0.01, max_value=0.10, value=0.05, key="e2")
    if st.button("Calculate Cochran Sample Size"):
        n0 = (z**2 * p * (1-p)) / (e**2)
        st.success(f"Required Sample Size: **{math.ceil(n0)}**")
