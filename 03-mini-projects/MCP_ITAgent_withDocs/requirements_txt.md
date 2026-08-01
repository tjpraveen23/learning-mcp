# IT Service Request Assistant - Installation Guide

## Requirements

### Python Dependencies
Create a `requirements.txt` file with the following dependencies:

```
streamlit>=1.28.0
openai>=1.3.0
anthropic>=0.7.0
asyncio
logging
dataclasses
enum34
json
re
datetime
typing
```

### Installation Steps

1. **Clone or Download the Files**
   ```bash
   # Create project directory
   mkdir it-service-assistant
   cd it-service-assistant
   
   # Save all Python files in this directory:
   # - mcp_server.py
   # - mcp_client.py  
   # - streamlit_app.py
   # - requirements.txt
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration Options

### Option 1: Local LLM (Recommended for Testing)
- Install and run a local LLM server like:
  - **LM Studio** (User-friendly GUI)
  - **Ollama** (Command-line)  
  - **text-generation-webui**
- Default URL: `http://localhost:1234/v1`
- No API key required

### Option 2: OpenAI
- Get API key from: https://platform.openai.com/api-keys
- Recommended models: `gpt-4`, `gpt-3.5-turbo`
- Note: API usage charges apply

### Option 3: Anthropic Claude
- Get API key from: https://console.anthropic.com/
- Recommended models: `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- Note: API usage charges apply

## Running the Application

### Start the Streamlit UI
```bash
streamlit run streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

### Testing the MCP Server Directly
```bash
python mcp_server.py
```

### Testing the MCP Client
```bash
python mcp_client.py
```

## File Structure
```
it-service-assistant/
├── mcp_server.py          # MCP Server with 3 tools
├── mcp_client.py          # MCP Client with LLM integration
├── streamlit_app.py       # Streamlit UI
├── requirements.txt       # Python dependencies
├── system_prompt.md       # System prompt documentation
└── README.md             # This file
```

## Usage Examples

### Through Streamlit UI
1. Configure your LLM provider in the sidebar
2. Type natural language requests like:
   - "Add user john.doe to IT_Support group"
   - "I need RDP access to SERVER001"
   - "Create a database service account for webapp"
   - "What entitlements does user123 have?"
   - "Request Adobe Photoshop installation"

### Direct API Usage
```python
import asyncio
from mcp_client import MCPClient, get_local_config

# Configure client
llm_config = get_local_config()
system_prompt = "..." # Use the system prompt from system_prompt.md
client = MCPClient(llm_config, system_prompt)

# Process request
response = asyncio.run(
    client.get_conversation_response("Add user john.doe to IT_Support group")
)
print(response)
```

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Ensure all files are in the same directory
   - Activate your virtual environment
   - Install all requirements

2. **LLM connection issues**
   - For local LLMs: Ensure the server is running on the correct port
   - For OpenAI/Anthropic: Check API key validity
   - Verify base URL format (include http:// or https://)

3. **Streamlit issues**
   - Try: `streamlit run streamlit_app.py --server.port 8501`
   - Clear cache: `streamlit cache clear`

4. **Async/Event Loop errors**
   - This is common in Jupyter notebooks
   - Run from command line instead

### Local LLM Setup (LM Studio Example)
1. Download and install LM Studio
2. Download a model (e.g., "TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
3. Start local server on port 1234
4. Use "Local LLM" option in the Streamlit app

## Features

### MCP Server (mcp_server.py)
- **ToolA**: AD Group and Entitlement Management
- **ToolB**: Machine Access Management  
- **ToolC**: Service Account and Infrastructure Management
- Mock data storage for testing
- Comprehensive error handling
- Async request processing

### MCP Client (mcp_client.py)
- Configurable LLM providers (OpenAI, Anthropic, Local)
- Intelligent request parsing
- JSON response validation
- Formatted conversation responses

### Streamlit UI (streamlit_app.py)
- Chat interface with message history
- Sidebar configuration for LLM settings
- Quick action buttons
- Tool information and examples
- Real-time response display
- Error handling with user-friendly messages

## Security Considerations

- API keys are handled securely (input type="password")
- No persistent storage of sensitive data
- Local processing of requests
- Configurable LLM endpoints

## Customization

### Adding New Tools
1. Add new tool handler in `MCPServer._handle_tool_x()`
2. Register in `self.tools` dictionary
3. Update `get_available_tools()` method
4. Add to system prompt documentation

### Modifying UI
- Edit `streamlit_app.py` for UI changes
- Customize CSS in the `st.markdown()` sections
- Add new quick action buttons
- Modify the layout structure

### Different LLM Providers
- Extend `LLMProvider` enum in `mcp_client.py`
- Add new configuration functions
- Implement provider-specific API calls
- Update UI dropdown options

## Production Considerations

- Add authentication/authorization
- Implement proper logging
- Use production-grade databases
- Add request rate limiting  
- Deploy with proper HTTPS
- Monitor API usage and costs
- Implement audit trails for service requests