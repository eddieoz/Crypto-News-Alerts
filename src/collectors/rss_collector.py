"""
RSS Feed Collector - Fetches and parses RSS feeds from configured sources.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
import feedparser
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class RSSCollector:
    """Collects news items from RSS feeds."""
    
    def __init__(self, feeds: List[Dict[str, Any]]):
        """
        Initialize RSS collector with feed configurations.
        
        Args:
            feeds: List of feed configurations with url, name, priority_boost, etc.
        """
        self.feeds = feeds
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_seen: Dict[str, datetime] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            # Use browser-like headers to avoid 403 errors
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session
    
    async def collect(self) -> List[Dict[str, Any]]:
        """
        Fetch all configured RSS feeds and return new items.
        
        Returns:
            List of news items with title, summary, link, source, etc.
        """
        items = []
        session = await self._get_session()
        
        # Fetch all feeds concurrently
        tasks = [self._fetch_feed(session, feed) for feed in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for feed_config, result in zip(self.feeds, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {feed_config['name']}: {result}")
                continue
            items.extend(result)
        
        logger.debug(f"RSS collector found {len(items)} new items")
        return items
    
    async def _fetch_feed(
        self,
        session: aiohttp.ClientSession,
        feed_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed."""
        url = feed_config["url"]
        name = feed_config["name"]
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Feed {name} returned status {response.status}")
                    return []
                
                content = await response.text()
        except Exception as e:
            logger.warning(f"Failed to fetch feed {name}: {e}")
            return []
        
        # Parse feed
        try:
            parsed = feedparser.parse(content)
        except Exception as e:
            logger.warning(f"Failed to parse feed {name}: {e}")
            return []
        
        # Get last seen timestamp for this feed
        last_seen = self._last_seen.get(url, datetime.min.replace(tzinfo=timezone.utc))
        
        items = []
        newest_timestamp = last_seen
        
        for entry in parsed.entries:
            # Parse timestamp
            timestamp = self._parse_timestamp(entry)
            
            # Skip old items
            if timestamp and timestamp <= last_seen:
                continue
            
            # Track newest item
            if timestamp and timestamp > newest_timestamp:
                newest_timestamp = timestamp
            
            # Check keywords if required
            keywords_required = feed_config.get("keywords_required", [])
            if keywords_required:
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if not any(kw.lower() in text for kw in keywords_required):
                    continue
            
            # Build item
            item = {
                "title": entry.get("title", ""),
                "summary": self._clean_summary(entry.get("summary", "")),
                "link": entry.get("link", ""),
                "source": name,
                "source_type": "rss",
                "category": feed_config.get("category", "news"),
                "priority_boost": feed_config.get("priority_boost", 0),
                "language": feed_config.get("language", "en"),
                "timestamp": timestamp or datetime.now(timezone.utc),
            }
            items.append(item)
        
        # Update last seen
        self._last_seen[url] = newest_timestamp
        
        if items:
            logger.info(f"📰 {name}: {len(items)} new items")
        
        return items
    
    def _parse_timestamp(self, entry: Any) -> Optional[datetime]:
        """Parse timestamp from feed entry."""
        for field in ["published", "updated", "created"]:
            if field in entry:
                try:
                    dt = date_parser.parse(entry[field])
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    continue
        return None
    
    def _clean_summary(self, summary: str) -> str:
        """Clean HTML and truncate summary."""
        # Basic HTML removal
        import re
        clean = re.sub(r'<[^>]+>', '', summary)
        clean = clean.strip()
        
        # Truncate
        if len(clean) > 500:
            clean = clean[:497] + "..."
        
        return clean
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
