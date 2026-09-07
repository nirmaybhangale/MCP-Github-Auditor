import os
import json
import asyncio
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv

# Groq and MCP Imports
from groq import AsyncGroq
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

class AuditorClient:
    def __init__(self):
        self.groq = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        # Groq's fast Llama 3 model is excellent for tool calling
        self.model = "openai/gpt-oss-20b" 

        env_vars = os.environ.copy()
        env_vars["PYTHONPATH"] = os.getcwd()
        
        # Define the subprocess parameters to launch our server
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=["-W", "ignore","-m", "src.server"],
            env={**os.environ} # Pass environment variables (like GITHUB_TOKEN) to the server
        )

    def _mcp_tool_to_groq_format(self, mcp_tool) -> Dict[str, Any]:
        """Convert an MCP Tool definition into Groq's expected JSON Schema format."""
        return {
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description,
                "parameters": mcp_tool.input_schema
            }
        }

    async def process_query(self, query: str, log_callback=None) -> str:
        """
        Main orchestration loop:
        1. Connects to the MCP Server
        2. Gets available tools
        3. Queries Groq
        4. Executes tools locally if requested
        5. Returns the final analysis
        """
        if log_callback:
            log_callback("Starting MCP server connection...")
            
        async with stdio_client(self.server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # 1. Fetch available tools from the MCP server
                tools_response = await session.list_tools()
                groq_tools = [self._mcp_tool_to_groq_format(t) for t in tools_response.tools]
                
                if log_callback:
                    log_callback(f"Server exposed {len(groq_tools)} tools: {[t['function']['name'] for t in groq_tools]}")

                messages = [
                    {"role": "system", "content": "You are a Senior AI Software Engineer auditing GitHub repositories. Use the provided tools to explore the codebase and answer the user's questions comprehensively."},
                    {"role": "user", "content": query}
                ]

                # 2. Tool Execution Loop
                while True:
                    if log_callback:
                        log_callback("Querying Groq LLM...")
                        
                    response = await self.groq.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=groq_tools,
                        tool_choice="auto"
                    )

                    response_message = response.choices[0].message
                    messages.append(response_message) # Append the LLM's response to history

                    # 3. Check if the LLM wants to call a tool
                    if not response_message.tool_calls:
                        if log_callback:
                            log_callback("Final answer generated.")
                        return response_message.content

                    # 4. Execute requested tools
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        if log_callback:
                            log_callback(f"Executing tool: {tool_name} with args: {tool_args}")
                        
                        # Call the tool on our local MCP server
                        try:
                            mcp_result = await session.call_tool(tool_name, tool_args)
                            # Handle MCP >= 2.x return format (list of Content objects)
                            result_text = "\n".join([c.text for c in mcp_result.content if c.type == "text"])
                        except Exception as e:
                            result_text = f"Tool execution failed: {str(e)}"
                            
                        if log_callback:
                            log_callback(f"Tool {tool_name} returned {len(result_text)} characters.")

                        # Append the tool result back to the LLM
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": result_text
                        })