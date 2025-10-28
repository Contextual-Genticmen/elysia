# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Elysia is a decision tree agentic framework built with Python 3.10+ that uses LLM-powered decision agents to dynamically select and execute tools. The system maintains a persistent environment across decision cycles and supports custom tools, built-in Weaviate tools, and Model Context Protocol (MCP) integration. The backend uses FastAPI with a Next.js frontend.

## Development Commands

### Python Development

**Setup:**
```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Unix/macOS
# .venv\Scripts\activate  # Windows

# Install dependencies
uv sync
```

**Running the Application:**
```bash
# Start Elysia app (backend + frontend)
elysia start

# Alternative: Use entry point directly
python -m elysia.api.cli
```

**Testing:**
```bash
# Run all tests
pytest tests/

# Run tests without external requirements (no LLM/Weaviate needed)
pytest tests/no_reqs/

# Run tests requiring environment setup (needs API keys)
pytest tests/requires_env/

# Run with coverage
pytest tests/ --cov=elysia --cov-report=html

# Run a single test file
pytest tests/no_reqs/test_tree.py

# Run a specific test
pytest tests/no_reqs/test_tree.py::test_tree_initialization -v
```

### Frontend Development

**Setup and Build:**
```bash
cd frontend

# Install dependencies
npm install

# Development mode (Next.js dev server)
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Production build and export to backend
npm run build  # Builds and copies to elysia/api/static_custom/
```

### Docker Development

**Quick Start:**
```bash
# Initial setup (creates .env from .env.example)
make setup

# Build and start everything (Elysia + Weaviate)
make run

# View logs
make logs

# Check service health
make health

# Stop services
make down
```

**Common Docker Commands:**
```bash
# Start with Ollama for local LLM
make up-ollama

# Shell into Elysia container
make shell

# Run tests in container
make test
make test-no-reqs
make test-requires-env

# Rebuild application
make rebuild

# View all services status
make ps

# Clean everything (including volumes/data)
make clean-volumes
```

**Ollama Management:**
```bash
# Pull a model
make ollama-pull MODEL=llama2

# List installed models
make ollama-list
```

### Documentation

```bash
# Serve docs locally (requires mkdocs-material)
mkdocs serve

# Build docs
mkdocs build
```

## Architecture

### Core Components

**Decision Tree System (`elysia/tree/`):**
- `tree.py`: Main Tree orchestrator that manages decision nodes and tool execution
- `util.py`: DecisionNode, Decision classes
- `objects.py`: TreeData (maintains Environment, Atlas, conversation history)
- Decision flow: Tree starts at root node → Decision Agent selects tool → Tool executes → Environment updates → Repeat until complete

**Tools System (`elysia/tools/`, `elysia/api/custom_tools.py`):**
- Built-in tools: Query, Aggregate, Visualise, SummariseItems, CitedSummarizer
- Custom tools: User-defined in `custom_tools.py` (see TellAJoke example)
- MCP tools: Auto-loaded from `elysia/mcp.json` configuration
- All tools are async generators that yield Result/Error/Text/Update objects

**API Layer (`elysia/api/`):**
- FastAPI server with WebSocket support for streaming results
- `services/user.py`: UserManager handles multiple users
- `services/tree.py`: TreeManager manages conversations per user
- `routes/query.py`: Main WebSocket endpoint for tree execution
- `routes/processor.py`: Tree processing pipeline
- Frontend served from `api/static_custom/`

**MCP Integration (`elysia/tools/mcp/`):**
- `mcp_loader.py`: Loads servers from `mcp.json` and creates Tool classes dynamically
- `mcp_tool.py`: Wrapper for stdio/SSE transport
- Auto-discovery adds MCP tools to tree root branch on initialization
- No code changes needed to add new MCP servers - just update `mcp.json`

**Configuration (`elysia/config/`):**
- Settings loaded from `.env` file or environment variables
- User-specific configs in `elysia/api/user_configs/`
- `ElysiaKeyManager`: Context manager for API key management
- Key settings: `BASE_MODEL`, `COMPLEX_MODEL`, `WCD_URL`, `WCD_API_KEY`

### Data Flow

1. User query arrives via WebSocket (`/ws/query`)
2. UserManager retrieves/creates TreeManager for user
3. TreeManager creates/retrieves conversation Tree
4. Tree.async_run() executes:
   - Initialize TreeData with query and environment
   - Decision Agent evaluates context and selects tool
   - Tool executes, yields results
   - Environment updates with tool outputs
   - Process repeats until completion or recursion limit
5. Results stream back to frontend as JSON
6. Tree saved for potential feedback/learning

**Environment Persistence:**
- Environment object stores all retrieved data hierarchically
- Each object assigned unique `_REF_ID` for tracking
- Persists across recursive tree calls (up to recursion limit)
- Structure: `environment[tool_type][collection_name][...]`

### LLM Integration

- Uses DSPy for structured LLM prompting
- Two models: `base_lm` (fast decisions) and `complex_lm` (complex reasoning)
- ElysiaChainOfThought: Custom DSPy signature with reasoning and feedback
- Feedback loop: CopiedModule includes failed attempts for in-context learning
- Token usage tracked via Tracker object

## Common Development Patterns

### Adding a Custom Tool

1. Add class to `elysia/api/custom_tools.py`:
```python
from elysia.tools.tool_base import Tool
from elysia.objects import Result, Text

class MyCustomTool(Tool):
    def __init__(self, **kwargs):
        super().__init__(
            name="my_custom_tool",
            description="What this tool does",
            inputs={
                "param": {
                    "description": "Description of param",
                    "type": str,
                    "required": True,
                }
            },
            end=False,  # Can this tool end the decision tree?
        )

    async def __call__(self, tree_data, inputs, base_lm, complex_lm,
                       client_manager, **kwargs):
        # Tool logic here
        result = # ... process inputs ...
        yield Result(objects=[result], name="my_result")
        yield Text("User-facing response")
```

2. Tool auto-discovered and available in UI/API

### Adding an MCP Server

1. Update `elysia/mcp.json`:
```json
{
  "servers": [
    {
      "name": "my-server",
      "enabled": true,
      "type": "stdio",
      "server_script_path": "/path/to/server.py",
      "args": ["arg1", "arg2"]
    }
  ]
}
```

2. Restart application - tool auto-loaded

### Creating Custom Tree Structure

```python
from elysia import Tree
from elysia.tools.query import Query

# Create tree with specific branch initialization
tree = Tree(branch_initialisation="multi_branch")

# Add custom branch and tools
tree.add_branch(
    branch_id="custom_search",
    instruction="Select search method",
    description="Different ways to search data"
)
tree.add_tool(Query, branch_id="custom_search")

# Execute query
response, objects = tree(
    "What are the most expensive items?",
    collection_names=["Ecommerce"]
)
```

### Debugging Tools

```python
# Visualize tree structure
tree.view()

# Check errors from execution
print(tree_data.errors)

# View conversation history
print(tree_data.conversation_history)

# Enable debug logging
tree.settings.LOGGING_LEVEL = "DEBUG"
```

## Configuration

### Environment Variables (.env)

Required for Weaviate connection:
```
WCD_URL=http://localhost:8080  # or cloud URL
WCD_API_KEY=...  # if using Weaviate Cloud
WEAVIATE_IS_LOCAL=True  # or False for cloud
```

Required for LLM (choose one or more):
```
OPENAI_API_KEY=...
OPENROUTER_API_KEY=...
ANTHROPIC_API_KEY=...
COHERE_API_KEY=...
```

Optional:
```
BASE_MODEL=gpt-4o-mini  # Fast model for decisions
COMPLEX_MODEL=gpt-4o  # Powerful model for reasoning
LOGGING_LEVEL=INFO
USE_FEEDBACK=False
```

### Model Configuration

Models specified via provider/model format:
- OpenAI: `openai/gpt-4o`, `openai/gpt-4o-mini`
- OpenRouter: `openrouter/anthropic/claude-3.5-sonnet`
- Ollama: `ollama_chat/llama3.1`
- Anthropic: `anthropic/claude-3-5-sonnet-20241022`

### Weaviate Collections

Collections need preprocessing before use:
```python
from elysia.preprocessing.collection import preprocess

preprocess(collection_names=["MyCollection"])
```

Or use "Analyze" button in the web UI under Data tab.

## Testing Conventions

- Tests in `tests/` directory
- `no_reqs/`: No external dependencies (fast, unit tests)
- `requires_env/`: Needs API keys and Weaviate (integration tests)
- Use pytest fixtures for tree/client setup
- Test collections auto-created and deleted in teardown

## Important File Locations

- **Custom Tools:** `elysia/api/custom_tools.py`
- **MCP Config:** `elysia/mcp.json` (with example at `elysia/mcp.example.json`)
- **User Configs:** `elysia/api/user_configs/`
- **Frontend Static:** `elysia/api/static_custom/` (built from `frontend/`)
- **Tree Branches:** Configured in `elysia/tree/tree.py` or via Tree API
- **Preprocessing:** `elysia/preprocessing/collection.py`

## Key Naming Conventions

- Tool names: snake_case (e.g., `query`, `aggregate`, `my_custom_tool`)
- Branch IDs: snake_case, dot-separated for hierarchy (e.g., `search.filters`)
- Collection names: Typically PascalCase (e.g., `Ecommerce`, `Articles`)
- Environment keys: Uppercase with underscores (e.g., `OPENAI_API_KEY`)
- Python modules/packages: snake_case

## Performance Notes

- Set `tree.low_memory=True` to disable LM caching
- Default recursion limit: 5 iterations (prevents infinite loops)
- Token usage tracked per decision node and tool
- Client pooling for Weaviate connections via ClientManager
- Async/await throughout for non-blocking execution
- WebSocket streaming prevents frontend blocking

## Troubleshooting

**Local models timing out:**
- Use smaller context models or increase timeout
- Check model compatibility with DSPy
- See docs/Advanced/local_models.md for details

**Collections not appearing:**
- Ensure collections are preprocessed (click Analyze or run preprocess())
- Check Weaviate connection settings
- Verify API keys for vectorizer

**Frontend not updating after code changes:**
- Rebuild frontend: `cd frontend && npm run build`
- Output copies to `elysia/api/static_custom/`

**MCP tools not loading:**
- Check `mcp.json` syntax and paths
- Verify `enabled: true` for server
- Check server script has correct transport type
- Look at logs for loading errors

## Project Structure Overview

```
elysia/
├── elysia/
│   ├── api/                 # FastAPI server, routes, services
│   │   ├── custom_tools.py  # User-defined tools (add yours here)
│   │   ├── routes/          # API endpoints
│   │   ├── services/        # UserManager, TreeManager
│   │   └── user_configs/    # Per-user configuration files
│   ├── config/              # Settings and configuration management
│   ├── preprocessing/       # Collection analysis for Weaviate
│   ├── tools/               # Built-in tools (Query, Aggregate, etc.)
│   │   └── mcp/             # MCP integration
│   ├── tree/                # Core decision tree logic
│   └── util/                # Client management, parsing, utilities
├── frontend/                # Next.js web interface
│   ├── app/                 # Next.js app router pages
│   └── src/lib/             # API client, utilities
├── tests/                   # Test suites
│   ├── no_reqs/             # Fast tests, no external deps
│   └── requires_env/        # Integration tests with LLM/Weaviate
├── docs/                    # MkDocs documentation
├── docker-compose.yml       # Docker setup with Weaviate
├── Makefile                 # Docker convenience commands
└── pyproject.toml           # Python dependencies and build config
```
