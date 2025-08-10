"""Web scraping service for extracting additional provider data from OpenRouter web interface."""

import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote

import httpx

from .cache import CacheManager
from .config import Config
from .exceptions import WebScrapingError, PageNotFoundError, ParseError, WebTimeoutError
from .models import WebScrapedData
from .web_parser import OpenRouterWebParser

logger = logging.getLogger(__name__)


class WebScrapingService:
    """Service for scraping additional provider data from OpenRouter web interface."""

    def __init__(self, config: Config, cache_manager: Optional[CacheManager] = None):
        """
        Initialize the web scraping service.
        
        Args:
            config: Configuration object containing timeout and other settings
            cache_manager: Optional cache manager for storing scraped data
        """
        self.config = config
        self.cache = cache_manager
        self.timeout = getattr(config, 'web_timeout', 10)  # Default 10 seconds
        
        # Create HTTP client with appropriate headers and timeout
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "User-Agent": getattr(config, 'web_user_agent', "openrouter-inspector/0.1.0 (Web Enhancement)"),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            },
            follow_redirects=True
        )

    async def get_model_web_data(self, model_id: str) -> Optional[WebScrapedData]:
        """
        Scrape additional provider data for a model from the web interface.
        
        Args:
            model_id: The model identifier (e.g., "qwen/qwen-2.5-coder-32b-instruct")
            
        Returns:
            WebScrapedData object containing scraped provider information, or None if scraping fails
            
        Raises:
            WebScrapingError: For various web scraping failures (network, parsing, etc.)
        """
        if not model_id or not model_id.strip():
            raise ValueError("Model ID cannot be empty")

        # Check cache first
        if self.cache:
            cache_key = f"web_data:{model_id}"
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.debug(f"Using cached web data for model {model_id}")
                return cached_data

        try:
            # Convert model ID to web page URL
            url = self._model_id_to_web_url(model_id)
            logger.debug(f"Fetching web data from: {url}")

            # Fetch HTML content
            html_content = await self._fetch_html(url)
            
            # Parse provider data from HTML
            providers = OpenRouterWebParser.parse_model_page(html_content, model_id)
            
            # Create WebScrapedData object
            web_data: WebScrapedData = WebScrapedData(
                model_id=model_id,
                providers=providers,
                source_url=url
            )
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, web_data)
                logger.debug(f"Cached web data for model {model_id}")
            
            logger.info(f"Successfully scraped data for {model_id}: {len(providers)} providers found")
            return web_data

        except WebScrapingError:
            # Re-raise web scraping errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error(f"Unexpected error scraping data for {model_id}: {e}")
            raise WebScrapingError(f"Failed to scrape web data for {model_id}: {e}")

    async def _fetch_html(self, url: str) -> str:
        """
        Fetch HTML content from the given URL with proper error handling.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string
            
        Raises:
            WebTimeoutError: If request times out
            PageNotFoundError: If page returns 404
            WebScrapingError: For other HTTP errors
        """
        try:
            response = await self.session.get(url)
            
            if response.status_code == 404:
                raise PageNotFoundError(f"Model page not found: {url}")
            elif response.status_code == 429:
                # Rate limiting - wait and retry once
                logger.warning(f"Rate limited, waiting 2 seconds before retry: {url}")
                await asyncio.sleep(2)
                response = await self.session.get(url)
                if response.status_code == 429:
                    raise WebScrapingError(f"Rate limited after retry: {url}")
            elif response.status_code >= 400:
                raise WebScrapingError(f"HTTP {response.status_code} error fetching {url}")
            
            response.raise_for_status()
            return response.text

        except httpx.TimeoutException:
            raise WebTimeoutError(f"Request timed out after {self.timeout} seconds: {url}")
        except httpx.NetworkError as e:
            raise WebScrapingError(f"Network error fetching {url}: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise PageNotFoundError(f"Model page not found: {url}")
            else:
                raise WebScrapingError(f"HTTP error {e.response.status_code} fetching {url}")

    def _model_id_to_web_url(self, model_id: str) -> str:
        """
        Convert model ID to OpenRouter web page URL.
        
        Args:
            model_id: Model identifier (e.g., "qwen/qwen-2.5-coder-32b-instruct")
            
        Returns:
            Full URL to the model's web page
            
        Raises:
            ValueError: If model ID format is invalid
        """
        if not model_id or "/" not in model_id:
            raise ValueError(f"Invalid model ID format: {model_id}. Expected format: 'author/model-name'")
        
        try:
            # Split into author and model name
            author, model_name = model_id.split("/", 1)
            
            # URL encode components to handle special characters
            author_encoded = quote(author.strip(), safe='')
            model_encoded = quote(model_name.strip(), safe='-._~')
            
            # Construct the URL
            url = f"https://openrouter.ai/{author_encoded}/{model_encoded}"
            
            logger.debug(f"Mapped model ID '{model_id}' to URL: {url}")
            return url
            
        except Exception as e:
            raise ValueError(f"Failed to convert model ID '{model_id}' to URL: {e}")

    async def close(self) -> None:
        """Close the HTTP session and clean up resources."""
        if self.session:
            await self.session.aclose()
            logger.debug("Web scraping service HTTP session closed")

    async def __aenter__(self) -> "WebScrapingService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


class URLMapper:
    """Utility class for URL mapping operations."""
    
    @staticmethod
    def model_id_to_web_url(model_id: str) -> str:
        """
        Convert model ID to OpenRouter web page URL.
        
        This is a static utility method that can be used independently
        of the WebScrapingService class.
        
        Args:
            model_id: Model identifier (e.g., "qwen/qwen-2.5-coder-32b-instruct")
            
        Returns:
            Full URL to the model's web page
            
        Raises:
            ValueError: If model ID format is invalid
        """
        if not model_id or "/" not in model_id:
            raise ValueError(f"Invalid model ID format: {model_id}. Expected format: 'author/model-name'")
        
        try:
            # Split into author and model name
            author, model_name = model_id.split("/", 1)
            
            # Normalize components - convert to lowercase and strip whitespace
            author_normalized = author.strip().lower()
            model_normalized = model_name.strip().lower()
            
            # URL encode components to handle special characters
            author_encoded = quote(author_normalized, safe='')
            model_encoded = quote(model_normalized, safe='-._~')
            
            # Construct the URL
            return f"https://openrouter.ai/{author_encoded}/{model_encoded}"
            
        except Exception as e:
            raise ValueError(f"Failed to convert model ID '{model_id}' to URL: {e}")

    @staticmethod
    def normalize_model_slug(model_id: str) -> str:
        """
        Normalize model ID for URL construction.
        
        Args:
            model_id: Raw model identifier
            
        Returns:
            Normalized model identifier suitable for URL construction
        """
        if not model_id:
            return model_id
            
        # Basic normalization - remove extra whitespace, convert to lowercase
        normalized = model_id.strip().lower()
        
        # Handle common variations and special characters
        # Replace multiple spaces with single space first
        import re
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Then replace spaces and underscores with hyphens
        replacements = {
            ' ': '-',  # Spaces to hyphens
            '_': '-',  # Underscores to hyphens (if needed)
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized