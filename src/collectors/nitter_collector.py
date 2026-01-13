"""
Nitter Collector - Scrapes tweets from public Nitter instances.
"""
import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class NitterCollector:
    """Collects tweets from Nitter instances (Twitter/X alternative frontend)."""
    
    def __init__(self, accounts: List[Dict[str, Any]], instances: List[str]):
        """
        Initialize Nitter collector.
        
        Args:
            accounts: List of accounts to monitor with handle, priority_boost, etc.
            instances: List of Nitter instance URLs to use.
        """
        self.accounts = accounts
        self.instances = instances if instances else ["nitter.privacydev.net"]
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_seen: Dict[str, str] = {}  # handle -> last tweet ID
        self._current_instance_idx = 0
        self._failed_instances: set = set()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Cookie": "techaro.lol-anubis-auth=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhY3Rpb24iOiJDSEFMTEVOR0UiLCJjaGFsbGVuZ2UiOiIwMTliYWQ1ZC1lODQ2LTc1NjgtOWQ1My0wNDdhZWQ1ZmI3ZDgiLCJleHAiOjE3Njg3NDQ5NzEsImlhdCI6MTc2ODE0MDE3MSwibWV0aG9kIjoiZmFzdCIsIm5iZiI6MTc2ODE0MDExMSwicG9saWN5UnVsZSI6ImFjOTgwZjQ5YzRkMzVmYWIiLCJyZXN0cmljdGlvbiI6ImNmYWUzZjZlMzgyYTM4ZmUwODU5ZjFiNWVhNjVmYWJhNDE2YWE0NWRkY2QxYTc4Y2IwZDg0YmU2OTc0MGY2NDkifQ.rrvRksUTsf3DEMK_rWhfByfaxgxvnDqYFtwd2EEONIasi5EeuDNxcsDlzuTfiov7JMlOj7SwfJQOpvMJZOpBAQ",
                "DNT": "1",
                "Pragma": "no-cache",
                "Priority": "u=0, i",
                "Sec-Ch-Ua": '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Linux"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-Gpc": "1",
                "Upgrade-Insecure-Requests": "1"
            }
            # Check for Tor proxy in environment
            import os
            from aiohttp_socks import ProxyConnector
            
            # Default to internal docker service name 'tor' on port 9050
            proxy_url = os.getenv("TOR_PROXY_URL", "socks5://tor:9050")
            connector = ProxyConnector.from_url(proxy_url, rdns=True)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout, 
                headers=headers
            )
        return self._session
    
    def _get_next_instance(self) -> Optional[str]:
        """Get next working Nitter instance."""
        available = [i for i in self.instances if i not in self._failed_instances]
        if not available:
            # Reset failed instances and try again
            self._failed_instances.clear()
            available = self.instances
        
        if not available:
            return None
        
        # Rotate through instances
        instance = available[self._current_instance_idx % len(available)]
        self._current_instance_idx += 1
        return instance
    
    async def collect(self) -> List[Dict[str, Any]]:
        """
        Fetch tweets from all monitored accounts.
        
        Returns:
            List of tweet items with content, author, link, etc.
        """
        items = []
        session = await self._get_session()
        
        # Process accounts with some delay to avoid rate limiting
        for account in self.accounts:
            try:
                tweets = await self._fetch_account(session, account)
                items.extend(tweets)
                
                # Small delay between accounts
                await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                logger.warning(f"Failed to fetch @{account['handle']}: {e}")
        
        logger.debug(f"Nitter collector found {len(items)} new items")
        return items
    
    async def _fetch_account(
        self,
        session: aiohttp.ClientSession,
        account: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch tweets from a single account."""
        handle = account["handle"]
        
        # Try different instances if one fails
        for _ in range(len(self.instances)):
            instance = self._get_next_instance()
            if not instance:
                logger.error("No Nitter instances available")
                return []
            
            # Use http for onion addresses (encryption handled by Tor), https for clearnet
            scheme = "http" if instance.endswith(".onion") else "https"
            url = f"{scheme}://{instance}/{handle}"
            
            try:
                async with session.get(url) as response:
                    if response.status == 429:
                        logger.warning(f"Rate limited on {instance}")
                        self._failed_instances.add(instance)
                        continue
                    
                    if response.status != 200:
                        logger.debug(f"Instance {instance} returned {response.status} for @{handle}")
                        self._failed_instances.add(instance)
                        continue
                    
                    html = await response.text()
                    return self._parse_tweets(html, account)
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on {instance}")
                self._failed_instances.add(instance)
                continue
            except Exception as e:
                logger.warning(f"Error fetching from {instance}: {e}")
                self._failed_instances.add(instance)
                continue
        
        return []
    
    def _parse_tweets(
        self,
        html: str,
        account: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse tweets from Nitter HTML response."""
        handle = account["handle"]
        soup = BeautifulSoup(html, "lxml")
        
        items = []
        last_seen_id = self._last_seen.get(handle, "")
        newest_id = last_seen_id
        
        # Find tweet containers - try multiple selectors
        timeline_items = soup.select(".timeline-item")
        
        logger.debug(f"Found {len(timeline_items)} potential timeline items")
        
        for item in timeline_items[:15]:  # Check slightly more items
            try:
                # Get tweet ID from link (which is a child of timeline-item, sibling of tweet-body)
                link_elem = item.select_one(".tweet-link")
                if not link_elem:
                    continue
                    
                tweet_link = link_elem.get("href", "")
                tweet_id = tweet_link.split("/")[-1].replace("#m", "")
                
                if not tweet_id:
                    continue
                
                # ... existing logic ...
                
                # Get tweet content from body
                tweet_body = item.select_one(".tweet-body")
                if not tweet_body:
                    continue
                    
                content_elem = tweet_body.select_one(".tweet-content")
                # Skip if we've already seen this
                if tweet_id == last_seen_id:
                    break
                
                # Track newest
                if not newest_id or tweet_id > newest_id:
                    newest_id = tweet_id
                
                content = content_elem.get_text(strip=True) if content_elem else ""
                
                if not content:
                    continue
                
                # Check keywords if required
                keywords_required = account.get("keywords_required", [])
                if keywords_required:
                    if not any(kw.lower() in content.lower() for kw in keywords_required):
                        continue
                
                # Build full link
                full_link = f"https://twitter.com/{handle}/status/{tweet_id}"
                
                item = {
                    "title": f"@{handle}: {content[:80]}...",
                    "summary": content,
                    "link": full_link,
                    "source": f"@{handle}",
                    "source_type": "nitter",
                    "category": account.get("category", "social"),
                    "priority_boost": account.get("priority_boost", 0),
                    "language": "en",
                    "timestamp": datetime.now(timezone.utc),
                    "tweet_id": tweet_id,
                }
                items.append(item)
                
            except Exception as e:
                logger.debug(f"Error parsing tweet: {e}")
                continue
        
        # Update last seen
        if newest_id:
            self._last_seen[handle] = newest_id
        
        if items:
            logger.info(f"🐦 @{handle}: {len(items)} new tweets")
        
        return items
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
