import streamlit as st
import asyncio
import os
import sys
from pathlib import Path

# --- WINDOWS ASYNCIO FIX ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ---------------------------

from src.client import AuditorClient

# Initialize page config - MUST be the first Streamlit command
st.set_page_config(
    page_title="MCP Auditor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure API Key is present
if not os.getenv("GROQ_API_KEY"):
    st.error("Please set GROQ_API_KEY in your .env file.")
    st.stop()

# Define the reports directory
REPORTS_DIR = Path.cwd() / "audit_reports"
REPORTS_DIR.mkdir(exist_ok=True)

# --- SIDEBAR: Workspace & Downloads ---
with st.sidebar:
    st.title("📂 Workspace")
    st.markdown("Generated audit reports are saved here.")
    st.divider()
    
    # Scan directory for generated reports
    reports = list(REPORTS_DIR.glob("*.md"))
    
    if not reports:
        st.info("No reports generated yet. Ask the auditor to analyze a repo and save a report.")
    else:
        for report in reports:
            # Provide a download button for each report
            with open(report, "r", encoding="utf-8") as f:
                st.download_button(
                    label=f"📄 {report.name}",
                    data=f.read(),
                    file_name=report.name,
                    mime="text/markdown",
                    use_container_width=True
                )
    
    st.divider()
    st.caption("Powered by Model Context Protocol")

# --- MAIN LAYOUT: Title & Chat ---
st.title("Open-Source Auditor")
st.markdown("An AI agent powered by FastMCP. It autonomously explores GitHub repositories and writes comprehensive markdown reports.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new user input
if prompt := st.chat_input("E.g., Audit octocat/Hello-World and save a report..."):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Use native st.status for a clean, expanding process tracker
        with st.status("Executing MCP Protocol...", expanded=True) as status_container:
            log_placeholder = st.empty()
            
            def update_log(msg: str):
                """Callback to push tool execution logs to the UI."""
                # Using a simple info box inside the status container looks much cleaner natively
                log_placeholder.info(msg, icon="⚙️")
            
            try:
                # Initialize client and run the async loop
                client = AuditorClient()
                final_answer = asyncio.run(client.process_query(prompt, log_callback=update_log))
                
                # Success state
                status_container.update(label="Audit Complete", state="complete", expanded=False)
                
                # Display the final answer
                st.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                
                # Rerun to update the sidebar with any newly saved reports
                st.rerun()
                
            except Exception as e:
                # Error state
                status_container.update(label="System Error", state="error", expanded=True)
                st.error(f"Error during execution: {str(e)}")