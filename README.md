# 🔍 MCP Open-Source Auditor

An AI-powered open-source codebase auditor built using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). It autonomously navigates public GitHub repositories, reads codebase structures, analyzes issues, and securely writes markdown audit reports to a local file store.

![Demo Preview](demo.gif) *(Note: Add a screen recording or screenshot of your Streamlit UI here)*

---

## 🛡️ Assessment Criteria & Security

This project was built to demonstrate production-grade MCP implementation, focusing heavily on safety and state management.

- **Genuine Side Effects:** Features a local File Store capability (`save_audit_report`) allowing the AI to persist its findings to disk.
- **Typed Inputs:** All MCP tools utilize strict Pydantic `Field` models to enforce schema validation before execution.
- **State Protection & Refusal Boundaries:** The server implements strict path-traversal protection (`is_relative_to`) and extension allowlisting. It explicitly **refuses** attempts to write non-markdown files or write outside the sandboxed `audit_reports/` directory, guaranteeing the host system cannot be corrupted by malformed AI arguments.
- **Resilient Transport:** Utilizes standard I/O (`stdio`) with stream sanitization to ensure pure JSON-RPC communication between the client and server.

---

## 🏗 Architecture

The application bridges a Streamlit frontend with a local MCP server, using Groq's high-speed open-weight models for tool orchestration.

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit App
    participant Client as MCP Client
    participant LLM as Groq LLM (gpt-oss-20b)
    participant Server as MCP Server
    participant API as GitHub API
    participant Disk as Local File Store

    User->>UI: "Audit octocat/Hello-World"
    UI->>Client: Send prompt
    Client->>LLM: Query with available tools
    LLM-->>Client: Tool Call (get_repo_structure)
    Client->>Server: Execute over stdio
    Server->>API: GET /repos/octocat/Hello-World/git/trees/main
    API-->>Server: JSON Tree
    Server-->>Client: Tool Result
    Client->>LLM: Send tool result
    LLM-->>Client: Tool Call (save_audit_report)
    Client->>Server: Execute over stdio
    Server->>Disk: Validate path & Write .md file
    Server-->>Client: Success Message
    Client->>LLM: Send tool result
    LLM-->>UI: Final synthesized analysis