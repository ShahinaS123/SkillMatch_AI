import os

def fix_pages():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pages_dir = os.path.join(base_dir, "pages")

    # 1. Delete the pages folder if it exists to start fresh
    if os.path.exists(pages_dir):
        import shutil
        shutil.rmtree(pages_dir)
        print(f"🗑️ Deleted old 'pages' folder to remove duplicates.")
    
    # 2. Recreate the folder
    os.makedirs(pages_dir)
    print(f"✅ Created clean 'pages' folder.")

    # 3. Create the Sample Size Calculator
    file_1_name = "1_📊_Sample_Size_Calculator.py"
    sample_size_code = """import streamlit as st
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
"""
    with open(os.path.join(pages_dir, file_1_name), "w", encoding="utf-8") as f:
        f.write(sample_size_code)
    print(f"✅ Created: {file_1_name}")

    # 4. Create the Research Assistant
    file_3_name = "3_📝_Research_Assistant.py"
    research_code = """import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

st.set_page_config(page_title="Research Assistant", page_icon="📝")
st.title("📝 Research Assistant")

st.subheader("Automated Thematic Analysis")
transcript = st.text_area("Paste Transcript here:", height=300)
if st.button("Run Thematic Coding"):
    if transcript:
        with st.spinner("Coding transcript..."):
            prompt = ChatPromptTemplate.from_template(
                "Perform inductive thematic analysis on this transcript. Provide Initial Codes and Candidate Themes:\\n\\n{text}"
            )
            chain = prompt | llm
            result = chain.invoke({"text": transcript})
            st.markdown(result.content)
    else:
        st.warning("Please paste a transcript.")
"""
    with open(os.path.join(pages_dir, file_3_name), "w", encoding="utf-8") as f:
        f.write(research_code)
    print(f"✅ Created: {file_3_name}")

    print("\n🎉 All clean! You can now run 'streamlit run app.py'")

if __name__ == "__main__":
    fix_pages()