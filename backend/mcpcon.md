Yash-Kavaiya
data-gov-in-mcp
Public
Go to file
t
T
Yash-Kavaiya
Yash-Kavaiya
docs: Add MCP client configuration for multiple platforms
886769a
 · 
10 months ago
Name		
docs
feat: Create production-ready MCP server for data.gov.in
11 months ago
src/data_gov_in
feat: Create production-ready MCP server for data.gov.in
11 months ago
tests
feat: Create production-ready MCP server for data.gov.in
11 months ago
.dockerignore
feat: Create production-ready MCP server for data.gov.in
11 months ago
.env.example
feat: Create production-ready MCP server for data.gov.in
11 months ago
.gitignore
feat: Create production-ready MCP server for data.gov.in
11 months ago
.python-version
Initial commit
11 months ago
CHANGELOG.md
feat: Create production-ready MCP server for data.gov.in
11 months ago
CONTRIBUTING.md
feat: Create production-ready MCP server for data.gov.in
11 months ago
Dockerfile
feat: Create production-ready MCP server for data.gov.in
11 months ago
LICENSE
feat: Create production-ready MCP server for data.gov.in
11 months ago
README.md
docs: Add MCP client configuration for multiple platforms
10 months ago
docker-compose.yml
feat: Create production-ready MCP server for data.gov.in
11 months ago
main.py
feat: Create production-ready MCP server for data.gov.in
11 months ago
pyproject.toml
feat: Create production-ready MCP server for data.gov.in
11 months ago
smithery.yaml
feat: Create production-ready MCP server for data.gov.in
11 months ago
uv.lock
Initial commit
11 months ago
Repository files navigation
README
Contributing
MIT license
data.gov.in MCP Server
Python MCP License Docker

A production-ready Model Context Protocol (MCP) server for accessing Indian government open data from data.gov.in. This server enables AI agents and applications to seamlessly query, filter, and retrieve datasets from India's national data portal.

Test Results
MCP Server Test Results

All 8 MCP tools tested and working successfully with live data from data.gov.in API.

Features
Feature	Description	Status
Dataset Retrieval	Access datasets using resource IDs	✅ Ready
Pagination	Navigate large datasets efficiently	✅ Ready
Filtering	Filter data by field values	✅ Ready
Field Schema	Get dataset structure and field types	✅ Ready
Response Caching	LRU cache with TTL for performance	✅ Ready
Rate Limiting	Automatic rate limiting with backoff	✅ Ready
Error Handling	Comprehensive error handling and retries	✅ Ready
Logging	Structured logging for monitoring	✅ Ready
Type Safety	Full type hints throughout	✅ Ready
Test Coverage	Comprehensive test suite	✅ Ready
Docker Support	Production-ready containerization	✅ Ready
Table of Contents
Installation
Quick Start
How to Use ← New! Step-by-step guide with screenshots
Configuration
MCP Client Configuration
Available Tools
Usage Examples
Development
Testing
Docker Deployment
API Documentation
Architecture
Contributing
License
Installation
Prerequisites
Python 3.12 or higher
uv package manager (recommended) or pip
data.gov.in API key (Get one here)
Using uv (Recommended)
# Clone the repository
git clone https://github.com/Yash-Kavaiya/data-gov-in-mcp.git
cd data-gov-in-mcp

# Install dependencies
uv sync

# Set up your API key
export DATA_GOV_IN_API_KEY="your-api-key-here"
Using pip
# Clone the repository
git clone https://github.com/Yash-Kavaiya/data-gov-in-mcp.git
cd data-gov-in-mcp

# Install dependencies
pip install -e .

# Set up your API key
export DATA_GOV_IN_API_KEY="your-api-key-here"
Using Docker
docker build -t data-gov-in-mcp .
docker run -e DATA_GOV_IN_API_KEY="your-api-key" data-gov-in-mcp
Quick Start
Running the Server
# Set your API key
export DATA_GOV_IN_API_KEY="your-api-key-here"

# Run the server
python main.py
Testing with MCP Inspector
npx @modelcontextprotocol/inspector python main.py
Configuration
The server can be configured using environment variables:

Variable	Description	Default	Required
DATA_GOV_IN_API_KEY	Your data.gov.in API key	None	✅ Yes
DATA_GOV_IN_BASE_URL	API base URL	https://api.data.gov.in	No
DATA_GOV_IN_TIMEOUT	Request timeout in seconds	30	No
DATA_GOV_IN_CACHE_ENABLED	Enable response caching	true	No
DATA_GOV_IN_CACHE_TTL	Cache TTL in seconds	3600	No
DATA_GOV_IN_CACHE_MAX_SIZE	Maximum cache entries	1000	No
DATA_GOV_IN_RATE_LIMIT_CALLS	Max calls per period	100	No
DATA_GOV_IN_RATE_LIMIT_PERIOD	Rate limit period in seconds	60	No
DATA_GOV_IN_MAX_RETRIES	Maximum retry attempts	3	No
DATA_GOV_IN_RETRY_DELAY	Initial retry delay in seconds	1.0	No
DATA_GOV_IN_LOG_LEVEL	Logging level	INFO	No
DATA_GOV_IN_DEFAULT_LIMIT	Default records per request	10	No
DATA_GOV_IN_MAX_LIMIT	Maximum records per request	100	No
Example .env file
Create a .env file in the project root:

DATA_GOV_IN_API_KEY=your-api-key-here
DATA_GOV_IN_CACHE_ENABLED=true
DATA_GOV_IN_LOG_LEVEL=INFO
DATA_GOV_IN_TIMEOUT=30
MCP Client Configuration
Configure this MCP server in your preferred AI client/platform:

Claude Desktop
Add to your Claude Desktop configuration file:

macOS: ~/Library/Application Support/Claude/claude_desktop_config.json Windows: %APPDATA%\Claude\claude_desktop_config.json

{
  "mcpServers": {
    "data-gov-in": {
      "command": "python",
      "args": ["/path/to/data-gov-in-mcp/main.py"],
      "env": {
        "DATA_GOV_IN_API_KEY": "your-api-key-here"
      }
    }
  }
}
Kiro
Add to .kiro/settings/mcp.json in your workspace or ~/.kiro/settings/mcp.json for global config:

{
  "mcpServers": {
    "data-gov-in": {
      "command": "python",
      "args": ["C:/path/to/data-gov-in-mcp/main.py"],
      "env": {
        "DATA_GOV_IN_API_KEY": "your-api-key-here"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
Cursor
Add to your Cursor MCP settings (.cursor/mcp.json):

{
  "mcpServers": {
    "data-gov-in": {
      "command": "python",
      "args": ["/path/to/data-gov-in-mcp/main.py"],
      "env": {
        "DATA_GOV_IN_API_KEY": "your-api-key-here"
      }
    }
  }
}
Windsurf
Add to your Windsurf MCP configuration:

{
  "mcpServers": {
    "data-gov-in": {
      "command": "python",
      "args": ["/path/to/data-gov-in-mcp/main.py"],
      "env": {
        "DATA_GOV_IN_API_KEY": "your-api-key-here"
      }
    }
  }
}
Cline (VS Code Extension)
Add to your Cline MCP settings file (cline_mcp_settings.json):

{
  "mcpServers": {
    "data-gov-in": {
      "command": "python",
      "args": ["/path/to/data-gov-in-mcp/main.py"],
      "env": {
        "DATA_GOV_IN_API_KEY": "your-api-key-here"
      }
    }
  }
}
Using uvx (Alternative)
If you prefer using uvx to run the server without cloning:

{
  "mcpServers": {
    "data-gov-in": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Yash-Kavaiya/data-gov-in-mcp", "python", "main.py"],
      "env": {
        "DATA_GOV_IN_API_KEY": "your-api-key-here"
      }
    }
  }
}
Using Docker
{
  "mcpServers": {
    "data-gov-in": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "DATA_GOV_IN_API_KEY=your-api-key-here", "data-gov-in-mcp"]
    }
  }
}
Note: Replace /path/to/data-gov-in-mcp/ with the actual path where you cloned the repository, and your-api-key-here with your data.gov.in API key.

Available Tools
The server provides the following MCP tools:

1. get_dataset
Retrieve data from a specific dataset/resource.

{
  "resource_id": "9ef84268-d588-465a-a308-a864a43d0070",
  "limit": 10,
  "offset": 0,
  "filters": "{\"state\": \"Maharashtra\"}"
}
2. get_dataset_fields
Get field information and schema for a dataset.

{
  "resource_id": "9ef84268-d588-465a-a308-a864a43d0070"
}
3. paginate_dataset
Retrieve a specific page of data from a dataset.

{
  "resource_id": "9ef84268-d588-465a-a308-a864a43d0070",
  "page": 2,
  "page_size": 20
}
4. get_dataset_summary
Get a summary of a dataset including record count and field information.

{
  "resource_id": "9ef84268-d588-465a-a308-a864a43d0070"
}
5. filter_dataset
Filter dataset records by a specific field value.

{
  "resource_id": "9ef84268-d588-465a-a308-a864a43d0070",
  "field": "state",
  "value": "Maharashtra",
  "limit": 10
}
6. get_cache_statistics
Get statistics about the API response cache.

{}
7. clear_cache
Clear all cached API responses.

{}
8. get_server_info
Get information about the MCP server and its configuration.

{}
Usage Examples
Example 1: Retrieve Dataset Records
# Get first 5 records from a dataset
get_dataset(
    resource_id="9ef84268-d588-465a-a308-a864a43d0070",
    limit=5
)
Example 2: Paginate Through Data
# Get page 2 with 20 records per page
paginate_dataset(
    resource_id="9ef84268-d588-465a-a308-a864a43d0070",
    page=2,
    page_size=20
)
Example 3: Filter Data
# Get records where state is Maharashtra
filter_dataset(
    resource_id="9ef84268-d588-465a-a308-a864a43d0070",
    field="state",
    value="Maharashtra",
    limit=10
)
Example 4: Inspect Dataset Schema
# Get field definitions
get_dataset_fields(
    resource_id="9ef84268-d588-465a-a308-a864a43d0070"
)
Development
Project Structure
data-gov-in-mcp/
├── src/
│   └── data_gov_in/
│       ├── __init__.py          # Package initialization
│       ├── api_client.py        # API client implementation
│       ├── cache.py             # Caching layer
│       ├── config.py            # Configuration management
│       ├── exceptions.py        # Custom exceptions
│       └── server.py            # MCP server implementation
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py       # API client tests
│   ├── test_cache.py            # Cache tests
│   └── test_config.py           # Configuration tests
├── docs/                        # Documentation
├── main.py                      # Entry point
├── pyproject.toml              # Project configuration
├── Dockerfile                  # Docker configuration
└── README.md                   # This file
Setting Up Development Environment
# Clone the repository
git clone https://github.com/Yash-Kavaiya/data-gov-in-mcp.git
cd data-gov-in-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
uv sync

# Install development dependencies
pip install pytest pytest-cov pytest-asyncio httpx
Testing
The project includes comprehensive tests for all components.

Running Tests
# Run all tests
pytest

# Run with coverage
pytest --cov=src/data_gov_in --cov-report=html

# Run specific test file
pytest tests/test_api_client.py

# Run with verbose output
pytest -v
Test Coverage
The test suite covers:

API client functionality
Caching layer
Configuration management
Error handling
Rate limiting
Retry logic
Docker Deployment
Building the Image
docker build -t data-gov-in-mcp:latest .
Running the Container
docker run -e DATA_GOV_IN_API_KEY="your-api-key" data-gov-in-mcp:latest
Using Docker Compose
Create a docker-compose.yml:

version: '3.8'
services:
  data-gov-in-mcp:
    build: .
    environment:
      - DATA_GOV_IN_API_KEY=${DATA_GOV_IN_API_KEY}
      - DATA_GOV_IN_CACHE_ENABLED=true
      - DATA_GOV_IN_LOG_LEVEL=INFO
    restart: unless-stopped
Run with:

docker-compose up -d
API Documentation
Data.gov.in API
This server interfaces with the data.gov.in API. Key information:

Base URL: https://api.data.gov.in
Authentication: API key required
Format: JSON
Rate Limits: Varies by API key tier
Getting an API Key
Visit data.gov.in
Register for an account
Navigate to "My Account"
Generate your API key
Finding Resource IDs
Resource IDs can be found on the data.gov.in website:

Browse datasets at https://data.gov.in/catalogs
Click on a dataset
Look for "API" or "Resource ID" in the dataset details
Architecture
System Architecture
┌─────────────────┐
│   AI Agent      │
└────────┬────────┘
         │ MCP Protocol
┌────────▼────────┐
│  FastMCP Server │
└────────┬────────┘
         │
┌────────▼────────┐
│  API Client     │
│  - Rate Limit   │
│  - Retry Logic  │
│  - Caching      │
└────────┬────────┘
         │ HTTPS
┌────────▼────────┐
│  data.gov.in    │
│      API        │
└─────────────────┘
Key Components
FastMCP Server: Exposes MCP tools for dataset operations
API Client: Handles HTTP requests to data.gov.in
Cache Layer: LRU cache with TTL for performance
Rate Limiter: Prevents API rate limit violations
Error Handler: Comprehensive error handling and retries
Contributing
Contributions are welcome! Please follow these guidelines:

Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
Code Style
Follow PEP 8 guidelines
Use type hints throughout
Write docstrings for all public functions
Add tests for new features
Troubleshooting
Common Issues
Issue: APIKeyMissingError

Solution: Set the DATA_GOV_IN_API_KEY environment variable
export DATA_GOV_IN_API_KEY="your-api-key"
Issue: RateLimitError

Solution: The server automatically handles rate limiting. Wait for the cooldown period or adjust rate limit settings.
Issue: ResourceNotFoundError

Solution: Verify the resource ID is correct by checking data.gov.in
Support
Issues: GitHub Issues
Email: yash.kavaiya3@gmail.com
Documentation: Wiki
License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
Anthropic for the Model Context Protocol
FastMCP for the excellent Python framework
data.gov.in for providing open government data
All contributors and users of this project
Links
Resource	URL
data.gov.in Portal	https://data.gov.in
MCP Documentation	https://modelcontextprotocol.io
FastMCP	https://github.com/jlowin/fastmcp
Project Repository	https://github.com/Yash-Kavaiya/data-gov-in-mcp
Built with ❤️ for the open data community