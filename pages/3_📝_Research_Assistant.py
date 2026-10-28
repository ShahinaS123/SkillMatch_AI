import streamlit as st
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
                "Perform inductive thematic analysis on this transcript. Provide Initial Codes and Candidate Themes:\n\n{text}"
            )
            chain = prompt | llm
            result = chain.invoke({"text": transcript})
            st.markdown(result.content)
    else:
        st.warning("Please paste a transcript.")
