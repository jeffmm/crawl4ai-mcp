# crawl4ai-mcp

`crawl4ai-mcp` provides a set of web crawling and internet search tools, implemented as a MCP (model context protocol) server. Built using [`crawl4ai`](https://github.com/unclecode/crawl4ai) and `mcp`, this project enables LLMs to perform internet searches and scrape websites for data, extending their capabilities with real-time web access.

## Project Structure

```bash
crawl4ai-mcp/
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── LICENSE
├── README.md
├── pyproject.toml
├── src/
│   └── crawl4ai_mcp/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── server.py
│       └── types.py
├── tests/
└── uv.lock
```

## Features

- **Google Search**: Perform Google searches and retrieve the top 10 results in markdown format.
- **Deep Crawling**:
    -   Perform Breadth-First Search (BFS) deep crawls.
    -   Execute Best-First deep crawls, prioritizing pages based on keywords.
    -   Configurable `max_depth`, `max_pages`, and `include_external` links.
-   **Multi-URL Crawling**: Crawl a list of specified URLs concurrently.
- **Configurable Settings**: Adjust browser type, headless mode, verbose logging, screenshot capture, word count threshold, cache mode, and content return type (HTML or Markdown).
- **Stealth Mode**: Includes settings for random user agents, user simulation, timezone, and geolocation to mimic real user behavior.
- **Flexible Output**: Returns content in either raw HTML for your LLM to parse, or processed into Markdown.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/crawl4ai/crawl4ai-mcp.git
    cd crawl4ai-mcp
    ```


1.  **Install with uv:**
    ```bash
    uv tool install crawl4ai-mcp
    ```

3. **Install playwright browsers** (if not already installed):
    ```bash
    playwright install chromium  # or firefox or webkit
    ```


## Configuration

The application's settings are managed via environment variables, prefixed with `C4AI_`. Key settings include:

-   `C4AI_BROWSER_TYPE`: `chromium`, `firefox`, or `webkit` (default: `chromium`)
-   `C4AI_HEADLESS`: `true` or `false` (default: `true`)
-   `C4AI_VERBOSE`: `true` or `false` (default: `false`)
-   `C4AI_SCREENSHOT`: `true` or `false` (default: `false`)
-   `C4AI_WORD_COUNT_THRESHOLD`: Minimum word count for content to be returned (default: `10`)
-   `C4AI_CACHE_MODE`: `enabled`, `disabled`, `read_only`, `write_only`, `bypass` (default: `bypass`)
-   `C4AI_MAX_DEPTH`: Maximum depth for deep crawling (default: `2`)
-   `C4AI_MAX_PAGES`: Maximum number of pages to crawl in deep strategies (default: `50`)
-   `C4AI_INCLUDE_EXTERNAL`: Whether to include external links in deep crawling (default: `false`)
-   `C4AI_CONTENT_TYPE`: `html` or `markdown` (default: `markdown`)

Example:
```bash
C4AI_BROWSER_TYPE=firefox C4AI_HEADLESS=false python src/crawl4ai_mcp/main.py
```

## Running the Server

The application can be run as a `FastMCP` server, supporting different transport mechanisms.

To run the server as a streamable HTTP server:

```bash
python src/crawl4ai_mcp/main.py --transport http
```

To run the server using standard I/O (default):

```bash
python src/crawl4ai_mcp/main.py
```

## Available Tools (API)

The following asynchronous tools are exposed by the `FastMCP` server for use by LLMs:

### `google_search(query: str) -> MCPCrawlResult`

Performs a Google search and returns a markdown page of the top 10 results.

-   `query`: The search query string.

### `deep_crawl(url: str, keywords: list[str] | None = None) -> list[MCPCrawlResult]`

Crawl a website deeply, optionally using keywords to prioritize pages.

-   `url`: The URL to start crawling from.
-   `keywords`: An optional list of keywords to prioritize pages during the crawl. If `None`, a Breadth-First Search (BFS) strategy is used.

### `crawl(urls: list[str]) -> list[MCPCrawlResult]`

Crawl multiple URLs and return their content.

-   `urls`: A list of URLs to crawl.


## Developer setup

To set up the project locally, follow these steps:

1. **Create and activate a virtual environment** using `uv` (recommended, as indicated by `uv.lock`):
    ```bash
    uv venv
    source .venv/bin/activate # On Windows, use `.venv\Scripts\activate`
    ```

2. **Install dependencies** from `pyproject.toml` and `uv.lock`:
    ```bash
    uv sync
    ```

3. **Install pre-commit hooks**:
    ```bash
    pre-commit install
    ```
