"""
AI Agent CLI with Firecrawl MCP Tools
====================================

This script launches an interactive command-line AI assistant that leverages LangChain, OpenAI, and Firecrawl MCP tools for web scraping, crawling, and web interaction tasks.

Features:
- Uses OpenAI's GPT-4.1 via LangChain for conversation and reasoning.
- Integrates Firecrawl MCP tools for advanced web automation.
- Loads API keys and configuration from environment variables.
- Prints available tools at startup.
- Maintains chat history for context-aware responses.

Requirements:
- Python 3.8+
- Packages: mcp, langchain, langchain_openai, langchain_mcp_adapter_tools, python-dotenv
- Environment variables:
    - OPENAI_API_KEY: Your OpenAI API key
    - FIREBASE_API_KEY: Your Firebase API key (for Firecrawl MCP)

Usage:
- Run: python main.py
- Type your queries at the prompt.
- Type 'exit' or 'quit' to end the session.

"""

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import asyncio
import os
from typing import Any


model = ChatOpenAI(
    model_name="gpt-4.1",
    temperature=0,
    # openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_key=OPENAI_API_KEY
)

server_params = StdioServerParameters(
    command="npx",
    args=["-y", "firecrawl-mcp"],
    env={
        "FIRECRAWL_API_KEY": FIRECRAWL_API_KEY
    }
)

async def main() -> None:
    """
    Launches the interactive AI assistant CLI.
    - Initializes the MCP client and session.
    - Loads available Firecrawl MCP tools.
    - Sets up the chat agent and maintains conversation history.
    - Handles user input and displays AI responses.
    """
    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(
                model=model,
                tools=tools,
            )
            messages: list[dict[str, Any]] = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that can scrape, crawl, and interact with web pages using the Firecrawl MCP tools. think step by step and use the tools provided to accomplish tasks.to help the user",
                }
            ]
            print("Available tools:")
            for tool in tools:
                print(f" - {tool.name}: {tool.description}")

            print("-"*60)

            while True:
                user_input: str = input("\nUser: ")
                if user_input.lower() in ["exit", "quit"]:
                    print("Exiting the chat.")
                    break

                messages.append({
                    "role": "user",
                    "content": user_input[:1750000],
                })
                try:
                    agent_response: dict = await agent.ainvoke(
                        input={"input": user_input},
                    )
                    # Try to access the AI message content robustly
                    ai_message = agent_response.get("message", agent_response.get("messages", []))
                    if isinstance(ai_message, list) and ai_message:
                        print(f"\nAI: {ai_message[-1].content}")
                    elif "content" in agent_response:
                        print(f"\nAI: {agent_response['content']}")
                    else:
                        print(f"\nAI: {agent_response}")
                except Exception as e:
                    print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
