import io
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote

import pytest
from crawl4ai import (
    AsyncWebCrawler,
    BestFirstCrawlingStrategy,
    BFSDeepCrawlStrategy,
    CrawlerRunConfig,
    CrawlResult,
)
from crawl4ai.models import CrawlResultContainer

# Import the actual module components to test
from crawl4ai_mcp.config import Settings, settings
from crawl4ai_mcp.server import (
    crawl,
    deep_crawl,
    google_search,
    handle_crawl_result,
)
from crawl4ai_mcp.types import MCPCrawlResult


# Helper for creating mock CrawlResult objects
def create_mock_crawl_result(
    success: bool,
    url: str,
    html: str | None = None,
    markdown_fit: str | None = None,
    markdown_raw: str | None = None,
    error_message: str | None = None,
) -> CrawlResult:
    mock_result = MagicMock(spec=CrawlResult)
    mock_result.success = success
    mock_result.url = url
    mock_result.html = html
    mock_result.error_message = error_message
    if markdown_fit or markdown_raw:
        mock_result.markdown = MagicMock()
        mock_result.markdown.fit_markdown = markdown_fit
        mock_result.markdown.raw_markdown = markdown_raw
    else:
        mock_result.markdown = None
    return mock_result


class TestSettings:
    """Unit tests for the Settings class in config.py."""

    def test_settings_defaults(self):
        s = Settings()
        assert s.browser_type == "chromium"
        assert s.headless is True
        assert s.verbose is False
        assert s.screenshot is False
        assert s.word_count_threshold == 10
        assert s.cache_mode == "bypass"
        assert s.max_depth == 2
        assert s.max_pages == 50
        assert s.include_external is False
        assert s.content_type == "markdown"

    def test_browser_config_property(self):
        s = Settings(browser_type="firefox", headless=False, verbose=True)
        browser_cfg = s.browser_config
        assert isinstance(browser_cfg, settings.browser_config.__class__)
        assert browser_cfg.browser_type == "firefox"
        assert browser_cfg.headless is False
        assert browser_cfg.verbose is True


class TestMCPCrawlResult:
    """Unit tests for the MCPCrawlResult model in types.py."""

    def test_mcpcrawlresult_instantiation_success(self):
        result = MCPCrawlResult(
            status="success", url="http://example.com", content="Hello world"
        )
        assert result.status == "success"
        assert result.url == "http://example.com"
        assert result.content == "Hello world"
        assert result.error_message is None

    def test_mcpcrawlresult_instantiation_error(self):
        result = MCPCrawlResult(
            status="error", error_message="Failed to crawl", url="http://example.com"
        )
        assert result.status == "error"
        assert result.url == "http://example.com"
        assert result.content is None
        assert result.error_message == "Failed to crawl"


class TestHandleCrawlResult:
    """Unit tests for the handle_crawl_result function in server.py."""

    def test_success_markdown_crawlresult(self):
        mock_crawl_res = create_mock_crawl_result(
            success=True, url="http://test.com", markdown_fit="Fit markdown content"
        )
        with patch.object(settings, "content_type", "markdown"):
            mcp_result = handle_crawl_result(mock_crawl_res)
            assert mcp_result.status == "success"
            assert mcp_result.url == "http://test.com"
            assert mcp_result.content == "Fit markdown content"

    def test_success_raw_markdown_crawlresult(self):
        mock_crawl_res = create_mock_crawl_result(
            success=True,
            url="http://test.com",
            markdown_fit=None,
            markdown_raw="Raw markdown content",
        )
        with patch.object(settings, "content_type", "markdown"):
            mcp_result = handle_crawl_result(mock_crawl_res)
            assert mcp_result.status == "success"
            assert mcp_result.url == "http://test.com"
            assert mcp_result.content == "Raw markdown content"

    def test_success_html_crawlresult(self):
        mock_crawl_res = create_mock_crawl_result(
            success=True, url="http://test.com", html="<html>Html content</html>"
        )
        with patch.object(settings, "content_type", "html"):
            mcp_result = handle_crawl_result(mock_crawl_res)
            assert mcp_result.status == "success"
            assert mcp_result.url == "http://test.com"
            assert mcp_result.content == "<html>Html content</html>"

    def test_failed_crawlresult_with_message(self):
        mock_crawl_res = create_mock_crawl_result(
            success=False, url="http://test.com", error_message="Page not found"
        )
        mcp_result = handle_crawl_result(mock_crawl_res)
        assert mcp_result.status == "error"
        assert mcp_result.url is None
        assert mcp_result.content is None
        assert mcp_result.error_message == "Page not found"

    def test_failed_crawlresult_no_message(self):
        mock_crawl_res = create_mock_crawl_result(success=False, url="http://test.com")
        mcp_result = handle_crawl_result(mock_crawl_res)
        assert mcp_result.status == "error"
        assert mcp_result.url is None
        assert mcp_result.content is None
        assert mcp_result.error_message == "Unknown crawl error."

    def test_crawlresultcontainer_success_markdown(self):
        mock_crawl_res = create_mock_crawl_result(
            success=True,
            url="http://container.com",
            markdown_fit="Content from container",
        )
        mock_container = CrawlResultContainer(results=[mock_crawl_res])
        with patch.object(settings, "content_type", "markdown"):
            mcp_result = handle_crawl_result(mock_container)
            assert mcp_result.status == "success"
            assert mcp_result.url == "http://container.com"
            assert mcp_result.content == "Content from container"

    def test_unexpected_result_type(self):
        mcp_result = handle_crawl_result("unexpected string")
        assert mcp_result.status == "error"
        assert (
            mcp_result.error_message
            == "Unexpected result type from crawler: <class 'str'>"
        )


# Fixtures for patching AsyncWebCrawler and redirect_stdout for integration tests
@pytest.fixture
def mock_async_web_crawler_instance():
    """
    Patches AsyncWebCrawler to return a mock instance
    for its async context manager methods.
    """
    mock_instance = AsyncMock(spec=AsyncWebCrawler)
    mock_instance.__aenter__.return_value = mock_instance
    mock_instance.__aexit__.return_value = None
    with patch("crawl4ai_mcp.server.AsyncWebCrawler", return_value=mock_instance):
        yield mock_instance


@pytest.fixture(autouse=True)
def mock_redirect_stdout():
    """
    Patches redirect_stdout to avoid actual stdout redirection during tests.
    """
    with patch("crawl4ai_mcp.server.redirect_stdout"):
        yield


@pytest.fixture(autouse=True)
def mock_text_io():
    """
    Patches io.TextIOWrapper to return a mock instance
    """

    mock_instance = MagicMock(spec=io.TextIOWrapper)
    with patch("crawl4ai_mcp.server.io.TextIOWrapper", return_value=mock_instance):
        yield mock_instance


class TestServerTools:
    """Integration tests for the tool functions in server.py, mocking AsyncWebCrawler."""

    @pytest.mark.asyncio
    async def test_google_search_success(self, mock_async_web_crawler_instance):
        mock_arun = AsyncMock()
        mock_async_web_crawler_instance.arun = mock_arun

        mock_arun.return_value = create_mock_crawl_result(
            success=True,
            url="http://google.com/search?q=test",
            markdown_fit="Google search results",
        )

        with patch.object(settings, "content_type", "markdown"):
            result = await google_search("test query")

            assert result.status == "success"
            assert result.url == "http://google.com/search?q=test"
            assert result.content == "Google search results"
            mock_arun.assert_called_once()
            assert (
                f"google.com/search?q={quote('test query')}"
                in mock_arun.call_args[0][0]
            )

            passed_config = mock_arun.call_args[1]["config"]
            assert isinstance(passed_config, CrawlerRunConfig)
            assert passed_config.stream is True
            assert passed_config.cache_mode.value == settings.cache_mode

    @pytest.mark.asyncio
    async def test_google_search_exception(self, mock_async_web_crawler_instance):
        mock_arun = AsyncMock()
        mock_async_web_crawler_instance.arun = mock_arun
        mock_arun.side_effect = Exception("Network error")

        result = await google_search("error query")

        assert result.status == "error"
        assert (
            "An error occurred during Google search: Network error"
            in result.error_message
        )

    @pytest.mark.asyncio
    async def test_deep_crawl_keywords_success(self, mock_async_web_crawler_instance):
        mock_arun = AsyncMock()
        mock_async_web_crawler_instance.arun = mock_arun

        async def async_iter_results():
            yield create_mock_crawl_result(
                success=True, url="http://site.com/page1", markdown_fit="Page 1 content"
            )
            yield create_mock_crawl_result(
                success=True, url="http://site.com/page2", markdown_fit="Page 2 content"
            )

        mock_arun.return_value = async_iter_results()

        with patch.object(settings, "content_type", "markdown"):
            results = await deep_crawl(
                "http://testsite.com", keywords=["keyword1", "keyword2"]
            )

            assert len(results) == 2
            assert results[0].status == "success"
            assert results[0].url == "http://site.com/page1"
            assert results[0].content == "Page 1 content"
            assert results[1].status == "success"
            assert results[1].url == "http://site.com/page2"
            assert results[1].content == "Page 2 content"

            call_args, call_kwargs = mock_arun.call_args
            assert isinstance(
                call_kwargs["config"].deep_crawl_strategy, BestFirstCrawlingStrategy
            )
            mock_async_web_crawler_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_crawl_no_keywords_success(
        self, mock_async_web_crawler_instance
    ):
        mock_arun = AsyncMock()
        mock_async_web_crawler_instance.arun = mock_arun

        async def async_iter_results():
            yield create_mock_crawl_result(
                success=True, url="http://site.com/pageA", markdown_fit="Page A content"
            )

        mock_arun.return_value = async_iter_results()

        with patch.object(settings, "content_type", "markdown"):
            results = await deep_crawl("http://testsite.com")

            assert len(results) == 1
            assert results[0].status == "success"
            assert results[0].url == "http://site.com/pageA"
            assert results[0].content == "Page A content"

            call_args, call_kwargs = mock_arun.call_args
            assert isinstance(
                call_kwargs["config"].deep_crawl_strategy, BFSDeepCrawlStrategy
            )
            mock_async_web_crawler_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_crawl_arun_not_async_iterator(
        self, mock_async_web_crawler_instance
    ):
        mock_arun = AsyncMock()
        mock_async_web_crawler_instance.arun = mock_arun
        mock_arun.return_value = "not an async iterator"

        results = await deep_crawl("http://testsite.com")

        assert len(results) == 1
        assert results[0].status == "error"
        assert (
            "Expected an AsyncIterator instance from arun, got: <class 'str'>"
            in results[0].error_message
        )
        mock_async_web_crawler_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_crawl_exception(self, mock_async_web_crawler_instance):
        mock_arun = AsyncMock()
        mock_async_web_crawler_instance.arun = mock_arun
        mock_arun.side_effect = Exception("Deep crawl error")

        results = await deep_crawl("http://error.com")

        assert len(results) == 1
        assert results[0].status == "error"
        assert (
            "An error occurred during deep crawl: Deep crawl error"
            in results[0].error_message
        )
        mock_async_web_crawler_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_multiple_urls_success(self, mock_async_web_crawler_instance):
        mock_arun_many = AsyncMock()
        mock_async_web_crawler_instance.arun_many = mock_arun_many

        async def async_iter_results():
            yield create_mock_crawl_result(
                success=True, url="http://url1.com", markdown_fit="Content 1"
            )
            yield create_mock_crawl_result(
                success=True, url="http://url2.com", markdown_fit="Content 2"
            )

        mock_arun_many.return_value = async_iter_results()
        with patch.object(settings, "content_type", "markdown"):
            urls_to_crawl = ["http://url1.com", "http://url2.com"]
            results = await crawl(urls_to_crawl)

            assert len(results) == 2
            assert results[0].status == "success"
            assert results[0].url == "http://url1.com"
            assert results[0].content == "Content 1"
            assert results[1].status == "success"
            assert results[1].url == "http://url2.com"
            assert results[1].content == "Content 2"
            mock_arun_many.assert_called_once()

            call_args, call_kwargs = mock_arun_many.call_args
            assert call_kwargs["urls"] == urls_to_crawl
            passed_config = call_kwargs["config"]
            assert isinstance(passed_config, CrawlerRunConfig)
            assert passed_config.stream is True
            assert passed_config.cache_mode.value == settings.cache_mode
            assert passed_config.word_count_threshold == settings.word_count_threshold

    @pytest.mark.asyncio
    async def test_crawl_arun_many_not_async_iterator(
        self, mock_async_web_crawler_instance
    ):
        mock_arun_many = AsyncMock()
        mock_async_web_crawler_instance.arun_many = mock_arun_many
        mock_arun_many.return_value = "not an async iterator"

        results = await crawl(["http://url.com"])

        assert len(results) == 1
        assert results[0].status == "error"
        assert (
            "Expected an AsyncIterator instance from arun, got: <class 'str'>"
            in results[0].error_message
        )

    @pytest.mark.asyncio
    async def test_crawl_exception(self, mock_async_web_crawler_instance):
        mock_arun_many = AsyncMock()
        mock_async_web_crawler_instance.arun_many = mock_arun_many
        mock_arun_many.side_effect = Exception("Crawl many error")

        results = await crawl(["http://error.com"])

        assert len(results) == 1
        assert results[0].status == "error"
        assert (
            "An unexpected error occurred during crawl: Crawl many error"
            in results[0].error_message
        )
