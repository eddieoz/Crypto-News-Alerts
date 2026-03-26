"""
ERR News Collector - Scrapes search results from news.err.ee API.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

class ErrCollector:
    """Collects news items from news.err.ee search API."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ERR collector with search configurations.

        Args:
            config: Configuration dictionary for err_search with queries.
        """
        self.config = config
        self.queries = config.get("queries", []) if config.get("enabled", True) else []
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_seen: Dict[str, int] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://news.err.ee",
                "Referer": "https://news.err.ee/search"
            }
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def collect(self) -> List[Dict[str, Any]]:
        """
        Fetch all configured ERR search queries and return new items.

        Returns:
            List of news items with title, summary, link, source, etc.
        """
        if not self.queries:
            return []

        items = []
        session = await self._get_session()

        tasks = [self._fetch_query(session, query) for query in self.queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for query_config, result in zip(self.queries, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch ERR query '{query_config.get('phrase')}': {result}")
                continue
            items.extend(result)

        if items:
            logger.debug(f"ERR collector found {len(items)} new items")
        return items

    async def _fetch_query(
        self,
        session: aiohttp.ClientSession,
        query_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch and parse a single search query."""
        phrase = query_config.get("phrase", "")
        if not phrase:
            return []

        options = {
            "total": 0,
            "page": 1,
            "limit": 50,
            "offset": 0,
            "phrase": phrase,
            "publicStart": "",
            "publicEnd": "",
            "timeFromSchedule": False,
            "types": [],
            "category": 130
        }
        
        url_encoded_options = quote(json.dumps(options, separators=(",", ":")))
        api_url = f"https://news.err.ee/api/search/getContents/?options={url_encoded_options}"

        try:
            async with session.get(api_url) as response:
                if response.status != 200:
                    logger.warning(f"ERR API returned status {response.status} for phrase {phrase}")
                    return []
                
                content = await response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch ERR API for phrase {phrase}: {e}")
            return []

        # Get last seen timestamp for this query
        last_seen = self._last_seen.get(phrase, 0)
        items = []
        newest_timestamp = last_seen
        
        contents_array = content.get("contents", [])

        for entry in contents_array:
            # Entry structure e.g.: {"id": ..., "heading": ..., "lead": ..., "publicStart": ...}
            timestamp_sec = entry.get("publicStart") or entry.get("updated")
            if not timestamp_sec:
                continue

            # Skip old items
            if timestamp_sec <= last_seen:
                continue

            # Track newest string/ID/timestamp
            if timestamp_sec > newest_timestamp:
                newest_timestamp = timestamp_sec
                
            item_id = entry.get("id")
            heading = entry.get("heading", "")
            lead = self._clean_summary(entry.get("lead", ""))
            
            # The URL isn't natively returned with a domain in search json sometimes,
            url_suffix = entry.get("url")
            if url_suffix:
                link = url_suffix if url_suffix.startswith("http") else f"https://news.err.ee/{item_id}/{url_suffix}"
            else:
                link = f"https://news.err.ee/{item_id}"

            item = {
                "title": heading,
                "summary": lead,
                "link": link,
                "source": "ERR News",
                "source_type": "err_search",
                "category": query_config.get("category", "news"),
                "priority_boost": query_config.get("priority_boost", 0),
                "language": "en",
                "timestamp": datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
            }
            items.append(item)

        # Update last seen
        self._last_seen[phrase] = newest_timestamp

        if items:
            logger.info(f"🔎 ERR Search '{phrase}': {len(items)} new items")

        return items

    def _clean_summary(self, summary: str) -> str:
        """Clean HTML from summary."""
        import re
        if not summary:
            return ""
        clean = re.sub(r'<[^>]+>', '', summary)
        clean = clean.strip()
        if len(clean) > 500:
            clean = clean[:497] + "..."
        return clean

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
