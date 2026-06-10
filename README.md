# Google Maps Restaurant Leads Finder (India)

This project finds and extracts 100 high-converting restaurant leads in India from Google Maps. It identifies local businesses with:
- Category: Restaurant
- Low reviews (review count < 50, ideally under 20)
- No website OR a website with very low reviews (under 15)
- Proper phone number for contact

These represent prime prospects for marketing agency services (e.g., website development, local SEO, or GBP optimization).

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Playwright browser:
   ```bash
   playwright install chromium
   ```

## Usage

Run the scraper:
```bash
python scrape_leads.py
```

The output will be saved to:
- `restaurant_leads_india.csv` - Structured spreadsheet of the leads.
