
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.collectors.nitter_collector import NitterCollector
from src.utils.logger import setup_logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_nitter_access():
    """Test accessing a Nitter list on the configured instances."""
    
    # Test configuration
    instances = ["nitter.catsarchywsyuss6jdxlypsw5dc7owd5u5tr6bujxb7o6xw2hipqehyd.onion"]
    
    # Use the user-provided list
    test_account = {
        "handle": "i/lists/2010711521144271183",
        "category": "test", 
        "priority_boost": 0
    }
    
    logger.info(f"Testing Nitter access for instances: {instances}")
    logger.info(f"Targeting list: {test_account['handle']}")

    # Patch the collector's _get_session to use the Tor proxy directly for testing if needed
    # But since we updated the class, it should just work if we run it in the container
    
    collector = NitterCollector(
        accounts=[test_account],
        instances=instances
    )
    
    try:
        # The collect method will try instances in rotation
        # We want to see WHICH one works
        
        # Manually trigger a fetch for the single account to see detailed results
        session = await collector._get_session()
        
        logger.info("-" * 50)
        
        for instance in instances:
            logger.info(f"Testing instance: {instance}...")
            # For onion addresses, we don't need https, but Nitter instances usually handle it or http
            # The .onion itself provides end-to-end encryption so http is fine, but check what the instance expects
            # Nitter onion services usually work on port 80 (http)
            
            scheme = "http" if instance.endswith(".onion") else "https"
            url = f"{scheme}://{instance}/{test_account['handle']}"
            
            try:
                # Increased timeout for Tor
                async with session.get(url, timeout=45) as response:
                    status = response.status
                    logger.info(f"Response from {instance}: {status}")
                    
                    if status == 200:
                        content = await response.text()
                        logger.info(f"Success! Content length: {len(content)}")
                        
                        # Try parsing
                        items = collector._parse_tweets(content, test_account)
                        logger.info(f"Parsed {len(items)} items from {instance}")
                        
                        if items:
                            logger.info(f"First item title: {items[0]['title']}")
                        else:
                            logger.warning("No items parsed! HTML preview:")
                            logger.warning(content[:500])
                            # Write full HTML to file for inspection
                            with open("/app/logs/nitter_debug.html", "w") as f:
                                f.write(content)
                            logger.info("Saved full HTML to /app/logs/nitter_debug.html")
                    else:
                        logger.warning(f"Failed to fetch from {instance} (Status: {status})")
                        
            except Exception as e:
                logger.error(f"Error connecting to {instance}: {e}")
            
            logger.info("-" * 50)
            
    finally:
        await collector.close()

if __name__ == "__main__":
    asyncio.run(test_nitter_access())
