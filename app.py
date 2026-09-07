import streamlit as st
import asyncio
from src.client import AuditorClient
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from src.client import AuditorClient

# Ensure API Key is present
if not os.getenv("GROQ_API_KEY"):
    st.error("Please set GROQ_API_KEY in your .env file.")
    st.stop()

st.set_page_config(page_title="Open-Source Auditor", page_icon="🔍")
st.title("🔍 MCP Open-Source Auditor")
st.markdown("Ask questions about any public GitHub repository. The LLM will autonomously navigate the code to answer.")

# Initialize chat history and client
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new user input
if prompt := st.chat_input("E.g., Analyze the structure of octocat/Hello-World"):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Use st.status to show the "thought process" and tool logs
        with st.status("Thinking and exploring...", expanded=True) as status_container:
            log_placeholder = st.empty()
            
            def update_log(msg: str):
                """Callback to push tool execution logs to the UI."""
                log_placeholder.markdown(f"*{msg}*")
            
            try:
                # Initialize client and run the async loop
                client = AuditorClient()
                final_answer = asyncio.run(client.process_query(prompt, log_callback=update_log))
                status_container.update(label="Analysis complete!", state="complete", expanded=False)
                
                # Display the final answer
                st.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                
            except Exception as e:
                status_container.update(label="Error occurred", state="error")
                st.error(f"An error occurred: {str(e)}")