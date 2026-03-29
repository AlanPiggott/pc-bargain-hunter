"""
config.py - Parts wishlist and search configuration.
Edit PARTS_WISHLIST to add/remove parts or adjust price targets.
"""

PARTS_WISHLIST = [
    {
        "category": "GPU",
        "search_terms": ["RTX 3060", "RTX 3060 Ti", "RX 6700 XT", "RX 6750 XT"],
        "max_price_aud": 300,
        "target_price_aud": 200,
        "hot_deal_price_aud": 150,
    },
    {
        "category": "CPU",
        "search_terms": ["Ryzen 5 5600", "Ryzen 5 5600X", "i5-12400", "i5-12400F"],
        "max_price_aud": 150,
        "target_price_aud": 100,
        "hot_deal_price_aud": 70,
    },
    {
        "category": "RAM",
        "search_terms": ["16GB DDR4", "16GB DDR4 3200", "2x8GB DDR4"],
        "max_price_aud": 50,
        "target_price_aud": 35,
        "hot_deal_price_aud": 25,
    },
    {
        "category": "Motherboard",
        "search_terms": ["B550 motherboard", "B660 motherboard", "B550M", "B660M"],
        "max_price_aud": 120,
        "target_price_aud": 80,
        "hot_deal_price_aud": 50,
    },
    {
        "category": "PSU",
        "search_terms": ["550W PSU", "650W PSU", "550W power supply", "650W power supply"],
        "max_price_aud": 80,
        "target_price_aud": 50,
        "hot_deal_price_aud": 35,
    },
    {
        "category": "SSD",
        "search_terms": ["1TB NVMe SSD", "1TB M.2 SSD", "500GB NVMe"],
        "max_price_aud": 80,
        "target_price_aud": 50,
        "hot_deal_price_aud": 35,
    },
    {
        "category": "Case",
        "search_terms": ["ATX case", "micro ATX case", "PC case"],
        "max_price_aud": 60,
        "target_price_aud": 30,
        "hot_deal_price_aud": 15,
    },
    {
        "category": "CPU Cooler",
        "search_terms": ["CPU cooler", "tower cooler", "Hyper 212"],
        "max_price_aud": 40,
        "target_price_aud": 20,
        "hot_deal_price_aud": 10,
    },
]

# Google Sheets configuration
SPREADSHEET_NAME = "PC Bargain Hunter"
LISTINGS_TAB = "Listings"
SUMMARY_TAB = "Summary"
TRENDS_TAB = "Price Trends"

# Dedup configuration
SEEN_LISTINGS_FILE = "seen_listings.json"
SEEN_LISTINGS_MAX_AGE_DAYS = 30

# eBay search configuration
EBAY_RESULTS_PER_TERM = 25

# Reddit subreddits to search
REDDIT_SUBREDDITS = [
    "hardwareswapaustralia",
    "bapcsalesaustralia",
]

# WhatsApp alert configuration
MAX_HOT_DEAL_ALERTS = 5
CALLMEBOT_DELAY_SECONDS = 3
