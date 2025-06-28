from crawl4ai import BrowserConfig
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .types import BrowserType, CacheModeType


class Settings(BaseSettings):
    model_config = SettingsConfigDict(validate_default=False, env_prefix="C4AI_")
    browser_type: BrowserType = Field(
        default="chromium",
        description="Browser type to use, one of: chromium, firefox, webkit",
    )
    headless: bool = Field(default=True, description="Run browser in headless mode")
    verbose: bool = Field(
        default=False, description="Enable verbose logging for development"
    )
    screenshot: bool = Field(
        default=False,
        description="Take screenshots of crawled pages, useful for debugging",
    )
    word_count_threshold: int = Field(
        default=10,
        description="Minimum word count for content to be returned",
    )
    cache_mode: CacheModeType = Field(
        default="bypass",  # Ensures fresh content by default
        description=(
            "Cache mode for web crawler, one of: enabled, disabled, read_only, write_only, bypass"
        ),
    )
    max_depth: int = Field(
        default=2,
        description="Maximum depth for deep crawling strategies",
    )
    max_pages: int = Field(
        default=50,
        description="Maximum number of pages to crawl in deep crawling strategies",
    )
    include_external: bool = Field(
        default=False,
        description="Whether to include content from external links in deep crawling strategies",
    )
    content_type: str = Field(
        default="markdown",
        description=(
            "Content type to return, one of: html, markdown. "
            "html returns the raw scrape results to be handled by the LLM directly."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def browser_config(self) -> BrowserConfig:
        """Generate BrowserConfig based on the current settings."""
        return BrowserConfig(
            browser_type=self.browser_type,
            headless=self.headless,
            verbose=self.verbose,
        )


settings = Settings()
