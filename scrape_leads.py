import os
import re
import csv
import sys
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

# Configuration
TARGET_LEAD_COUNT = 100
CSV_FILENAME = "restaurant_leads_india.csv"

# List of Indian cities to search
CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", 
    "Pune", "Jaipur", "Surat", "Lucknow", "Nagpur", "Indore", "Thane", "Bhopal", 
    "Visakhapatnam", "Pimpri-Chinchwad", "Patna", "Vadodara", "Ghaziabad", "Ludhiana", 
    "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", "Kalyan-Dombivli", "Vasai-Virar", 
    "Varanasi", "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Navi Mumbai", 
    "Allahabad", "Ranchi", "Howrah", "Coimbatore", "Jabalpur", "Gwalior", "Vijayawada", 
    "Jodhpur", "Madurai", "Raipur", "Kota", "Guwahati", "Chandigarh", "Solapur"
]

def force_english(url):
    if "?" in url:
        return url + "&hl=en"
    else:
        return url + "?hl=en"

def clean_website_url(url):
    if not url:
        return ""
    if "google.com/url" in url:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "q" in qs:
            return qs["q"][0]
    return url

def load_existing_leads():
    leads = []
    if os.path.exists(CSV_FILENAME):
        try:
            with open(CSV_FILENAME, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    leads.append(row)
            print(f"Loaded {len(leads)} existing leads from {CSV_FILENAME}")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")
    return leads

def save_lead_to_csv(lead):
    file_exists = os.path.exists(CSV_FILENAME)
    try:
        with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as f:
            fieldnames = ["Name", "Rating", "Reviews", "Website", "Phone", "Address", "Google Maps URL", "City"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(lead)
    except Exception as e:
        print(f"Error saving lead to CSV: {e}")

def scrape_leads():
    existing_leads = load_existing_leads()
    existing_urls = {lead["Google Maps URL"] for lead in existing_leads}
    leads_count = len(existing_leads)

    if leads_count >= TARGET_LEAD_COUNT:
        print(f"Already have {leads_count} leads. Nothing to do!")
        return

    with sync_playwright() as p:
        print("Launching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        # Create a browser context with mobile/desktop user agent and standard viewport
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for city in CITIES:
            if leads_count >= TARGET_LEAD_COUNT:
                break

            print(f"\n--- Searching for restaurants in {city} ---")
            search_query = f"restaurants in {city}"
            search_url = force_english(f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}/")
            
            try:
                page.goto(search_url, timeout=60000)
                # Wait for either results to load or "no results found" message
                page.wait_for_selector('div[role="feed"]', timeout=20000)
            except Exception as e:
                print(f"Error loading search page for {city}: {e}")
                continue

            # Scroll the feed to load listings
            print("Scrolling search results panel to load more restaurants...")
            feed_selector = 'div[role="feed"]'
            scroll_attempts = 12
            for i in range(scroll_attempts):
                try:
                    # Scroll down the feed
                    page.locator(feed_selector).evaluate("el => el.scrollBy(0, 1500)")
                    page.wait_for_timeout(1500)
                except Exception as e:
                    break

            # Extract restaurant links
            print("Extracting restaurant links...")
            link_elements = page.locator('a[href*="/maps/place/"]').all()
            urls = []
            for el in link_elements:
                try:
                    href = el.get_attribute("href")
                    if href:
                        # Clean to base place URL to avoid duplicate tracking with coordinates
                        base_url = href.split("?")[0].split("/data=")[0]
                        if base_url not in existing_urls and base_url not in urls:
                            urls.append(href)
                except:
                    continue

            print(f"Found {len(urls)} new restaurant URLs in {city}. Processing...")

            # Visit each URL to extract details
            for url in urls:
                if leads_count >= TARGET_LEAD_COUNT:
                    break

                place_url = force_english(url)
                print(f"\nVisiting: {place_url.split('/place/')[1].split('/')[0] if '/place/' in place_url else 'Place Details'}")

                try:
                    page.goto(place_url, timeout=30000)
                    page.wait_for_selector('h1', timeout=10000)
                except Exception as e:
                    print(f"Failed to load details page: {e}")
                    continue

                # Parse details
                try:
                    name = page.locator('h1').first.inner_text().strip()
                except:
                    name = "Unknown"

                # Parse rating and reviews count
                rating_val = 0.0
                reviews_count = 0
                try:
                    # Try to find the rating container
                    rating_container = page.locator('div.F7nice').first
                    if rating_container.count() > 0:
                        text = rating_container.inner_text()
                        # Extract numerical rating (e.g. 4.2)
                        rating_match = re.search(r'([\d.]+)', text)
                        if rating_match:
                            rating_val = float(rating_match.group(1))
                        # Extract review count inside parentheses (e.g. (15) or (1,234))
                        reviews_match = re.search(r'\(([\d,]+)\)', text)
                        if reviews_match:
                            reviews_count = int(reviews_match.group(1).replace(',', ''))
                except Exception as e:
                    print(f"Error parsing rating/reviews: {e}")

                # Parse website
                website = ""
                try:
                    website_el = page.locator('a[data-item-id="authority"]').first
                    if website_el.count() > 0:
                        raw_website = website_el.get_attribute("href")
                        website = clean_website_url(raw_website)
                except Exception as e:
                    pass

                # Parse phone number
                phone = ""
                try:
                    phone_el = page.locator('*[data-item-id*="phone:tel:"]').first
                    if phone_el.count() > 0:
                        item_id = phone_el.get_attribute("data-item-id")
                        phone = item_id.replace("phone:tel:", "").strip()
                except Exception as e:
                    pass

                # Parse address
                address = ""
                try:
                    address_el = page.locator('*[data-item-id="address"]').first
                    if address_el.count() > 0:
                        address = address_el.inner_text().strip()
                except Exception as e:
                    pass

                print(f"Name: {name}")
                print(f"Rating: {rating_val} | Reviews: {reviews_count}")
                print(f"Website: {website if website else 'None'}")
                print(f"Phone: {phone if phone else 'None'}")

                # APPLY FILTERS
                # 1. Must have a phone number
                if not phone:
                    print("Skipping: No contact number.")
                    continue

                # 2. Check website & review criteria
                # - If no website: reviews <= 50 (to capture businesses with low online presence)
                # - If has website: reviews <= 15 (to capture businesses that have a site but lack reviews/SEO success)
                if website:
                    if reviews_count > 15:
                        print(f"Skipping: Has website and reviews count ({reviews_count}) > 15.")
                        continue
                else:
                    if reviews_count > 50:
                        print(f"Skipping: No website but reviews count ({reviews_count}) > 50.")
                        continue

                # Save lead
                lead = {
                    "Name": name,
                    "Rating": rating_val,
                    "Reviews": reviews_count,
                    "Website": website,
                    "Phone": phone,
                    "Address": address,
                    "Google Maps URL": url,
                    "City": city
                }

                save_lead_to_csv(lead)
                existing_urls.add(url.split("?")[0].split("/data=")[0])
                leads_count += 1
                print(f"--> Saved Lead #{leads_count} / {TARGET_LEAD_COUNT} <--")

        browser.close()
        print(f"\nSuccess! Gathered {leads_count} leads in total.")

if __name__ == "__main__":
    scrape_leads()
