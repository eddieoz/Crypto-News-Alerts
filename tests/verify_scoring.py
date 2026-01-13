import sys
import os
import yaml
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from filters.priority_scorer import PriorityScorer

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load the filters configuration."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'filters.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def run_tests():
    config = load_config()
    scorer = PriorityScorer(config)
    min_score = config.get('minimum_score', 55)

    print(f"Loaded config. Minimum score: {min_score}")
    print("-" * 60)

    test_cases = [
        # --- DESIRED ALERTS (Security) ---
        {
            "title": "Major Exchange Binance Hacked for $500M",
            "summary": "Attackers exploited a vulnerability in the hot wallet.",
            "expected": True,
            "type": "Critical Security"
        },
        {
            "title": "Critical Zero-Day Vulnerability Found in Linux Kernel",
            "summary": "CVE-2024-1234 allows remote code execution.",
            "expected": True,
            "type": "Critical Security"
        },
        {
            "title": "Ledger Connect Kit malicious code infection identified",
            "summary": "Supply chain attack compromised the library.",
            "expected": True,
            "type": "Supply Chain Attack"
        },
        {
            "title": "Trezor Phishing Campaign Targets Users via Email",
            "summary": "Fake data breach notifications sent to users.",
            "expected": True,
            "type": "Phishing"
        },

        # --- UNWANTED NOISE (Investment/Market) ---
        {
            "title": "Bitcoin Hits New All-Time High above $100k",
            "summary": "Market sentiment is extremely bullish as ETF inflows surge.",
            "expected": False,
            "type": "Market Price"
        },
        {
            "title": "BlackRock Spot Bitcoin ETF Approved by SEC",
            "summary": "The regulatory approval marks a new era for crypto.",
            "expected": False, # Regulatory approval, but mostly market noise
            "type": "ETF/Regulatory"
        },
        {
            "title": "Solana Price Prediction: Can SOL reach $500?",
            "summary": "Technical analysis suggests a breakout if resistance breaks.",
            "expected": False,
            "type": "Price Prediction"
        },
        {
            "title": "Top 5 Altcoins with 100x Potential in 2026",
            "summary": "Our analysis of the best investment opportunities.",
            "expected": False,
            "type": "Investment Advice"
        },

        # --- UNWANTED NOISE (Spam/Promo) ---
        {
            "title": "Claim your $JOY airdrop now!",
            "summary": "Exclusive giveaway for early adopters.",
            "expected": False,
            "type": "Airdrop/Spam"
        },
        {
            "title": "New Token LISTING on Binance: MEME",
            "summary": "Deposits are now open for MEME coin.",
            "expected": False,
            "type": "Exchange Listing"
        },
         {
            "title": "Binance Will Perform Scheduled System Upgrade",
            "summary": "The upgrade will take approximately 3 hours.",
            "expected": False,
            "type": "Routine Maintenace"
        }
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        # Simulate an item with a generic source boost (e.g., generic news source = 10)
        # Security sources usually have higher boosts (20-25), but noise shouldn't pass even with that.
        # Let's be conservative and give them a 'High' source boost (20) to see if filters work hard enough.
        item = {
            "title": case["title"],
            "summary": case["summary"],
            "priority_boost": 20, # Simulating a decent source
            "category": "news"
        }
        
        score, cat = scorer.score(item)
        is_alert = score >= min_score
        
        result_str = "PASS" if is_alert == case["expected"] else "FAIL"
        if result_str == "PASS":
            passed += 1
        else:
            failed += 1
            
        print(f"[{result_str}] {case['type']:<20} | Score: {score:>3} | Alert: {str(is_alert):<5} | Title: {case['title'][:40]}...")

    print("-" * 60)
    print(f"Results: {passed} Passed, {failed} Failed")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
