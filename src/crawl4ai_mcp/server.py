import io
import sys
from collections.abc import AsyncIterator
from contextlib import redirect_stdout
from urllib.parse import quote

from crawl4ai import (
    AsyncWebCrawler,
    BestFirstCrawlingStrategy,
    BFSDeepCrawlStrategy,
    CacheMode,
    CrawlerRunConfig,
    CrawlResult,
    GeolocationConfig,
    KeywordRelevanceScorer,
)
from crawl4ai.models import CrawlResultContainer
from crawl4ai.types import RunManyReturn
from mcp.server.fastmcp import FastMCP

from .config import settings
from .types import MCPCrawlResult


def handle_crawl_result(result: RunManyReturn) -> MCPCrawlResult:
    if isinstance(result, CrawlResultContainer):
        result = result[0]
    if not isinstance(result, CrawlResult):
        return MCPCrawlResult(
            status="error",
            error_message=f"Unexpected result type from crawler: {type(result)}",
        )

    elif result.success and settings.content_type == "html":
        return MCPCrawlResult(status="success", url=result.url, content=result.html)

    elif result.success and result.markdown:
        # Extract the content from the result
        output_content = result.extracted_content or ""
        if not output_content and result.markdown:
            output_content = (
                result.markdown.fit_markdown or result.markdown.raw_markdown
            )

            # Extract the content from the result
            return MCPCrawlResult(
                status="success", url=result.url, content=output_content
            )
        else:
            return MCPCrawlResult(
                status="error",
                error_message="The crawler failed to extract any valid content.",
            )
    else:
        return MCPCrawlResult(
            status="error",
            error_message=result.error_message or "Unknown crawl error.",
        )


# Specify dependencies for deployment and development and pass lifespan to server
app = FastMCP("crawl4ai-mcp", dependencies=["crawl4ai"])


@app.tool()
async def google_search(query: str) -> MCPCrawlResult:
    """Perform a Google search and return a markdown page of the top 10 results.

    Args:
        query: The search query to perform.

    Returns:
        MCPCrawlResult: The result of the search, containing the status and content.
    """
    crawl_config = CrawlerRunConfig(
        stream=True,
        cache_mode=CacheMode(settings.cache_mode),
        keep_attrs=["id", "class"],
        keep_data_attributes=True,
        delay_before_return_html=2,
        word_count_threshold=settings.word_count_threshold,
        # Stealth mode settings
        user_agent_mode="random",
        simulate_user=True,
        timezone_id="America/Los_Angeles",  # JS Date()/Intl timezone
        geolocation=GeolocationConfig(  # override GPS coords
            latitude=34.0522,
            longitude=-118.2437,
            accuracy=10.0,
        ),
    )
    try:
        async with AsyncWebCrawler(config=settings.browser_config) as crawler:
            with redirect_stdout(
                io.TextIOWrapper(sys.stderr.buffer, encoding=sys.stderr.encoding)
            ):
                result = await crawler.arun(
                    f"https://www.google.com/search?q={quote(query)}&start=0&num=10",
                    config=crawl_config,
                )
            return handle_crawl_result(result)
    except Exception as e:
        # Catch any exceptions that occur during the search
        return MCPCrawlResult(
            status="error",
            error_message=f"An error occurred during Google search: {str(e)}",
        )


@app.tool()
async def deep_crawl(
    url: str, keywords: list[str] | None = None
) -> list[MCPCrawlResult]:
    """Crawl a website deeply, optionally using keywords to prioritize pages.

    Args:
        url: The URL to start crawling from.
        keywords: List of keywords to prioritize pages. If None, uses a breadth-first
            search strategy.
    """
    if keywords:
        # Create a scorer
        scorer = KeywordRelevanceScorer(keywords=keywords, weight=0.7)

        # Configure the strategy
        strategy = BestFirstCrawlingStrategy(
            max_depth=settings.max_depth,
            include_external=False,
            url_scorer=scorer,
            max_pages=settings.max_pages,
        )
    else:
        strategy = BFSDeepCrawlStrategy(
            max_depth=settings.max_depth,
            max_pages=settings.max_pages,
            include_external=settings.include_external,
        )
    crawl_config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        stream=True,  # Handle results as they come in
        cache_mode=CacheMode(settings.cache_mode),
        word_count_threshold=settings.word_count_threshold,  # Only return content with at least 10 words
        # Stealth mode settings
        user_agent_mode="random",
        simulate_user=True,
        timezone_id="America/Los_Angeles",  # JS Date()/Intl timezone
        geolocation=GeolocationConfig(  # override GPS coords
            latitude=34.0522,
            longitude=-118.2437,
            accuracy=10.0,
        ),
    )

    results = []

    # Explicit lifecycle management for the crawler is recommended for long-running tasks
    crawler = AsyncWebCrawler(config=settings.browser_config)
    try:
        with redirect_stdout(
            io.TextIOWrapper(sys.stderr.buffer, encoding=sys.stderr.encoding)
        ):
            pages = await crawler.arun(url, config=crawl_config)
        if not isinstance(pages, AsyncIterator):
            return [
                MCPCrawlResult(
                    status="error",
                    error_message=(
                        f"Expected an AsyncIterator instance from arun, got: {type(pages)}"
                    ),
                )
            ]
        async for page_result in pages:
            result = handle_crawl_result(page_result)
            results.append(result)
    except Exception as e:
        # Handle any exceptions that occur during crawling
        results.append(
            MCPCrawlResult(
                status="error",
                error_message=f"An error occurred during deep crawl: {str(e)}",
            )
        )
    finally:
        await crawler.close()
    return results


@app.tool()
async def crawl(urls: list[str]) -> list[MCPCrawlResult]:
    """Crawl multiple URLs and return their content.

    Args:
        urls: List of URLs to crawl.

    Returns:
        List of crawl results for each URL.
    """

    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode(settings.cache_mode),
        word_count_threshold=settings.word_count_threshold,  # Only return content with at least 10 words
        exclude_external_links=False,
        exclude_social_media_links=True,
        stream=True,
        # Content handling
        process_iframes=True,
        remove_overlay_elements=True,
        magic=True,
        # Stealth mode settings
        user_agent_mode="random",
        simulate_user=True,
        timezone_id="America/Los_Angeles",  # JS Date()/Intl timezone
        geolocation=GeolocationConfig(  # override GPS coords
            latitude=34.0522,
            longitude=-118.2437,
            accuracy=10.0,
        ),
    )

    results: list[MCPCrawlResult] = []
    try:
        async with AsyncWebCrawler(config=settings.browser_config) as crawler:
            with redirect_stdout(
                io.TextIOWrapper(sys.stderr.buffer, encoding=sys.stderr.encoding)
            ):
                pages = await crawler.arun_many(urls=urls, config=run_cfg)
            if not isinstance(pages, AsyncIterator):
                return [
                    MCPCrawlResult(
                        status="error",
                        error_message=(
                            f"Expected an AsyncIterator instance from arun, got: {type(pages)}"
                        ),
                    )
                ]
            async for result in pages:
                results.append(handle_crawl_result(result))

    except Exception as e:
        # Catch any other unexpected errors during the crawl
        results.append(
            MCPCrawlResult(
                status="error",
                error_message=f"An unexpected error occurred during crawl: {str(e)}",
            )
        )
    return results


if __name__ == "__main__":
    # Initialize and run the server
    app.run(transport="stdio")
