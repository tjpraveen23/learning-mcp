import asyncio
from pydantic import Field, create_model
from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from mcp import ClientSession
from mcp.client.sse import sse_client
import os


async def main():
    # Connect to MCP server via HTTP SSE
    async with sse_client("http://127.0.0.1:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get MCP tools
            tools_list = await session.list_tools()
            print("🧰 Available MCP Tools:")
            for tool in tools_list.tools:
                print(f"  - {tool.name}")
            
            # Convert MCP tools to LangChain tools
            lc_tools = []
            
            for mcp_tool in tools_list.tools:
                # Extract schema and create Pydantic model
                schema = mcp_tool.inputSchema.get('properties', {})
                fields = {
                    name: (str, Field(description=info.get('description', '')))
                    for name, info in schema.items()
                }
                args_model = create_model(f"{mcp_tool.name}_args", **fields)
                
                # Create tool function
                def make_tool_func(tool_name: str):
                    async def tool_func(**kwargs) -> str:
                        result = await session.call_tool(tool_name, arguments=kwargs)
                        if result.content:
                            content = result.content[0]
                            if hasattr(content, 'text'):
                                return content.text
                            elif isinstance(content, dict):
                                return str(content)
                            else:
                                return str(content)
                        return "No response"
                    return tool_func
                
                # Create StructuredTool
                lc_tool = StructuredTool.from_function(
                    coroutine=make_tool_func(mcp_tool.name),
                    name=mcp_tool.name,
                    description=mcp_tool.description or mcp_tool.name,
                    args_schema=args_model
                )
                lc_tools.append(lc_tool)
            
            # Create agent
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Use tools to complete tasks."),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            
            agent = create_tool_calling_agent(llm, lc_tools, prompt)
            executor = AgentExecutor(agent=agent, tools=lc_tools, verbose=True)
            
            # Run task
            print("\n🧑 Task: Read page 12345 and create a new page\n")
            result = await executor.ainvoke({
                "input": "Read confluence page '12345', then create page titled 'Demo Page' with content 'Sample content'"
            })
            
            print(f"\n✅ Result: {result['output']}")


if __name__ == "__main__":
    asyncio.run(main())