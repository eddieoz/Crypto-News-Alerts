"""
Alert Scheduler - Orchestrates all collectors and dispatches notifications.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from .collectors.rss_collector import RSSCollector
from .collectors.nitter_collector import NitterCollector
from .filters.priority_scorer import PriorityScorer
from .filters.deduplicator import Deduplicator
from .notifiers.ntfy_client import NtfyClient

logger = logging.getLogger(__name__)


class AlertScheduler:
    """Orchestrates data collection, filtering, and notification dispatch."""
    
    def __init__(
        self,
        sources_config: Dict[str, Any],
        filters_config: Dict[str, Any],
        ntfy_config: Dict[str, Any]
    ):
        self.sources_config = sources_config
        self.filters_config = filters_config
        self.ntfy_config = ntfy_config
        
        # Initialize components
        self.rss_collector = RSSCollector(sources_config.get("rss_feeds", []))
        self.nitter_collector = NitterCollector(
            accounts=sources_config.get("nitter_accounts", []),
            instances=sources_config.get("nitter", {}).get("instances", [])
        )
        self.priority_scorer = PriorityScorer(filters_config)
        self.deduplicator = Deduplicator(filters_config.get("deduplication", {}))
        self.ntfy_client = NtfyClient(ntfy_config)
        
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def run(self):
        """Start all collectors and run the main loop."""
        self._running = True
        
        logger.info("Starting collectors...")
        
        # Start collector tasks
        self._tasks = [
            asyncio.create_task(self._run_rss_collector()),
        ]
        
        # Only start Nitter collector if enabled
        nitter_config = self.sources_config.get("nitter", {})
        if nitter_config.get("enabled", True):
            self._tasks.append(asyncio.create_task(self._run_nitter_collector()))
            logger.info("Nitter collector enabled")
        else:
            logger.info("Nitter collector disabled in configuration")
        
        # Wait for all tasks
        await asyncio.gather(*self._tasks, return_exceptions=True)
    
    async def shutdown(self):
        """Gracefully shutdown all tasks."""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.deduplicator.close()
        logger.info("All collectors stopped")
    
    async def _run_rss_collector(self):
        """Run RSS collector loop."""
        interval = self.sources_config.get("rss_feeds", [{}])[0].get("check_interval", 60)
        
        while self._running:
            try:
                logger.debug("Checking RSS feeds...")
                items = await self.rss_collector.collect()
                await self._process_items(items)
            except Exception as e:
                logger.error(f"RSS collector error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _run_nitter_collector(self):
        """Run Nitter collector loop."""
        nitter_config = self.sources_config.get("nitter", {})
        interval = nitter_config.get("check_interval", 120)
        
        while self._running:
            try:
                logger.debug("Checking Nitter feeds...")
                items = await self.nitter_collector.collect()
                await self._process_items(items)
            except Exception as e:
                logger.error(f"Nitter collector error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _process_items(self, items: List[Dict[str, Any]]):
        """Process collected items through filter and notification pipeline."""
        for item in items:
            try:
                # Check for duplicates
                if await self.deduplicator.is_duplicate(item):
                    logger.debug(f"Skipping duplicate: {item.get('title', '')[:50]}")
                    continue
                
                # Calculate priority score
                score, category = self.priority_scorer.score(item)
                
                # Check minimum score threshold
                min_score = self.filters_config.get("minimum_score", 40)
                if score < min_score:
                    logger.debug(f"Score {score} below threshold: {item.get('title', '')[:50]}")
                    continue
                
                # Determine notification topic
                topic = self._get_topic_for_category(category)
                
                # Send notification
                await self.ntfy_client.send(
                    topic=topic,
                    title=item.get("title", "Crypto Alert"),
                    message=item.get("summary", ""),
                    url=item.get("link", ""),
                    priority=self._get_priority_for_score(score),
                    tags=self._get_tags_for_category(category)
                )
                
                # Mark as seen
                await self.deduplicator.mark_seen(item)
                
                logger.info(f"📢 Alert sent [{category}] (score={score}): {item.get('title', '')[:60]}")
                
            except Exception as e:
                logger.error(f"Error processing item: {e}")
    
    def _get_topic_for_category(self, category: str) -> str:
        """Get ntfy topic for a given category."""
        category_topics = self.filters_config.get("category_topics", {})
        return category_topics.get(category, "crypto-social")
    
    def _get_priority_for_score(self, score: int) -> int:
        """Convert score to ntfy priority (1-5)."""
        if score >= 90:
            return 5  # Urgent
        elif score >= 70:
            return 4  # High
        elif score >= 50:
            return 3  # Default
        else:
            return 2  # Low
    
    def _get_tags_for_category(self, category: str) -> List[str]:
        """Get emoji tags for notification."""
        tag_map = {
            "security": ["rotating_light", "lock"],
            "regulatory": ["scales", "page_facing_up"],
            "protocol": ["gear", "bitcoin"],
            "news": ["newspaper"],
            "social": ["speech_balloon"],
            "market": ["chart_with_upwards_trend"]
        }
        return tag_map.get(category, ["bell"])
