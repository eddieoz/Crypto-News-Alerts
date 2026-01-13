"""
Priority Scorer - Calculates priority score for news items based on keywords.
"""
import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class PriorityScorer:
    """Scores news items based on keyword matches and source priority."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize priority scorer with filter configuration.
        
        Args:
            config: Filter configuration with keyword lists and scores.
        """
        self.config = config
        self.keywords = config.get("keywords", {})
        
        # Build keyword lookup for fast matching
        self._keyword_patterns = self._build_patterns()
    
    def _build_patterns(self) -> Dict[str, List[Tuple[re.Pattern, int]]]:
        """Build regex patterns for keyword matching."""
        patterns = {}
        
        for category, settings in self.keywords.items():
            score = settings.get("score", 0)
            words = settings.get("words", [])
            
            # Create case-insensitive patterns
            category_patterns = []
            for word in words:
                # Escape special chars and create word boundary pattern
                escaped = re.escape(word)
                pattern = re.compile(rf'\b{escaped}\b', re.IGNORECASE)
                category_patterns.append((pattern, score))
            
            patterns[category] = category_patterns
        
        return patterns
    
    def score(self, item: Dict[str, Any]) -> Tuple[int, str]:
        """
        Calculate priority score for an item.
        
        Args:
            item: News item with title, summary, source info, etc.
            
        Returns:
            Tuple of (score, category) where category is the highest scoring match.
        """
        # Combine text fields for matching
        title = item.get("title", "")
        summary = item.get("summary", "")
        text = f"{title} {summary}"
        
        # Start with source's priority boost
        base_score = item.get("priority_boost", 0)
        
        # Track best category match
        best_category = item.get("category", "news")
        best_category_score = 0
        
        # Match keywords
        total_keyword_score = 0
        matched_keywords = []
        
        for category, patterns in self._keyword_patterns.items():
            category_score = 0
            
            for pattern, score in patterns:
                if pattern.search(text):
                    category_score += score
                    matched_keywords.append(pattern.pattern)
            
            if category_score != 0:
                total_keyword_score += category_score
                
                # Track highest-scoring category
                if category_score > best_category_score:
                    best_category_score = category_score
                    # Map keyword category to item category
                    best_category = self._map_category(category)
        
        final_score = base_score + total_keyword_score
        
        if matched_keywords:
            logger.debug(f"Score {final_score} for '{title[:50]}' - matched: {matched_keywords[:3]}")
        
        return final_score, best_category
    
    def _map_category(self, keyword_category: str) -> str:
        """Map keyword category to notification category."""
        mapping = {
            "critical_en": "security",
            "critical_pt": "security",
            "regulatory_en": "regulatory",
            "regulatory_pt": "regulatory",
            "protocol": "protocol",
            "market": "market",
        }
        return mapping.get(keyword_category, "news")
