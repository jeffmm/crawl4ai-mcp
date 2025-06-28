from typing import Literal

from pydantic import BaseModel, Field

BrowserType = Literal["chromium", "firefox", "webkit"]

CacheModeType = Literal[
    "enabled",
    "disabled",
    "read_only",
    "write_only",
    "bypass",
]

StatusType = Literal["success", "error"]

TransportType = Literal["stdio", "html"]


class MCPCrawlResult(BaseModel):
    """Model for crawl results"""

    status: StatusType = Field(
        description="The status of the crawl operation, e.g., 'success' or 'error'."
    )
    url: str | None = Field(default=None, description="The URL that was crawled.")
    content: str | None = Field(
        default=None, description="The extracted content in html or markdown format."
    )
    error_message: str | None = Field(default=None, description="Error message if any.")
