"""
ntfy Client - Sends push notifications via ntfy server.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class NtfyClient:
    """Client for sending push notifications via ntfy."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ntfy client with configuration.
        
        Args:
            config: ntfy configuration with server URL, topics, etc.
        """
        self.config = config
        
        # Get server settings
        server_config = config.get("server", {})
        self.base_url = os.environ.get("NTFY_URL") or server_config.get("url", "http://localhost:8080")
        self.token = os.environ.get("NTFY_TOKEN") or server_config.get("token", "")
        
        # Get topic names from env or config
        topics_config = config.get("topics", {})
        self.topics = {
            "critical": os.environ.get("NTFY_TOPIC_CRITICAL") or topics_config.get("critical", "crypto-critical"),
            "regulatory": os.environ.get("NTFY_TOPIC_REGULATORY") or topics_config.get("regulatory", "crypto-regulatory"),
            "protocol": os.environ.get("NTFY_TOPIC_PROTOCOL") or topics_config.get("protocol", "crypto-protocol"),
            "social": os.environ.get("NTFY_TOPIC_SOCIAL") or topics_config.get("social", "crypto-social"),
        }
        
        # Get priority settings
        self.priorities = config.get("priorities", {})
        
        # Formatting settings
        formatting = config.get("formatting", {})
        self.max_title_length = formatting.get("max_title_length", 100)
        self.max_body_length = formatting.get("max_body_length", 500)
        self.include_link_action = formatting.get("include_link_action", True)
        self.include_timestamp = formatting.get("include_timestamp", True)
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"ntfy client configured for {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.AsyncClient(headers=headers, timeout=10.0)
        return self._client
    
    async def send(
        self,
        topic: str,
        title: str,
        message: str,
        url: str = "",
        priority: int = 3,
        tags: Optional[List[str]] = None
    ):
        """
        Send a notification via ntfy.
        
        Args:
            topic: Notification topic (channel).
            title: Notification title.
            message: Notification message body.
            url: Optional URL to include as action.
            priority: Priority level 1-5.
            tags: Optional list of emoji tags.
        """
        client = await self._get_client()
        
        # Truncate title and message
        title = self._truncate(title, self.max_title_length)
        message = self._truncate(message, self.max_body_length)
        
        # Add timestamp if configured
        if self.include_timestamp:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            message = f"[{timestamp}] {message}"
        
        # Build request headers (encode unicode for HTTP headers)
        headers = {
            "Title": self._encode_header(title),
            "Priority": str(priority),
        }
        
        # Add tags
        if tags:
            headers["Tags"] = ",".join(tags)
        
        # Add action button for URL
        if url and self.include_link_action:
            headers["Actions"] = f"view, Open, {url}"
        
        # Construct full URL
        endpoint = f"{self.base_url.rstrip('/')}/{topic}"
        
        try:
            response = await client.post(
                endpoint,
                content=message.encode("utf-8"),
                headers=headers
            )
            
            if response.status_code == 200:
                logger.debug(f"Notification sent to {topic}: {title[:40]}")
            else:
                logger.warning(f"ntfy returned {response.status_code}: {response.text}")
                
        except httpx.TimeoutException:
            logger.error(f"Timeout sending notification to {topic}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _encode_header(self, text: str) -> str:
        """
        Encode text for HTTP headers.
        Removes newlines, control chars, and replaces problematic unicode.
        """
        # First, remove newlines and control characters (they break HTTP headers)
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ''.join(char if ord(char) >= 32 else ' ' for char in text)
        
        # Common unicode replacements
        replacements = {
            '\u2019': "'",   # Right single quotation mark
            '\u2018': "'",   # Left single quotation mark
            '\u201c': '"',   # Left double quotation mark
            '\u201d': '"',   # Right double quotation mark
            '\u2013': '-',   # En dash
            '\u2014': '-',   # Em dash
            '\u2026': '...', # Ellipsis
            '\u00a0': ' ',   # Non-breaking space
        }
        
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)
        
        # Fallback: encode to ASCII, replacing unknown chars (including emojis)
        return text.encode('ascii', 'replace').decode('ascii')
    
    def get_topic_name(self, category: str) -> str:
        """Get topic name for a category."""
        # Map categories to topics
        category_map = {
            "security": "critical",
            "regulatory": "regulatory",
            "protocol": "protocol",
            "social": "social",
            "news": "regulatory",
            "market": "social",
        }
        topic_key = category_map.get(category, "social")
        return self.topics.get(topic_key, "crypto-social")
    
    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def send_test(self, topic: str = "crypto-critical"):
        """Send a test notification."""
        await self.send(
            topic=topic,
            title="🧪 Test Notification",
            message="This is a test notification from Crypto News Alerts. If you see this, your setup is working!",
            priority=3,
            tags=["white_check_mark", "test"]
        )
        logger.info(f"Test notification sent to {topic}")
