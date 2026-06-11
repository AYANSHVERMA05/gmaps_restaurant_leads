import os
import re
import csv
import json
import sys
import requests
from urllib.parse import urlparse, parse_qs, quote
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def check_instagram_on_website(url):
    if not url:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "instagram.com" in href.lower():
                    clean_href = href.split('?')[0].rstrip('/')
                    path = urlparse(clean_href).path.strip('/')
                    if path and path not in ['developer', 'about', 'legal', 'directory', 'explore', 'p', 'tv', 'reel', 'stories', 'accounts', 'reels']:
                        return clean_href
    except Exception as e:
        print(f"Error checking website {url} for Instagram: {e}")
    return None

def search_instagram_for_business(business_name, city):
    query = f"{business_name} {city} instagram"
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            valid_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "uddg=" in href:
                    parsed = urlparse(href)
                    qs = parse_qs(parsed.query)
                    if "uddg" in qs:
                        href = qs["uddg"][0]
                
                if "instagram.com" in href:
                    clean_href = href.split('?')[0].rstrip('/')
                    path = urlparse(clean_href).path.strip('/')
                    if path and path not in ['developer', 'about', 'legal', 'directory', 'explore', 'p', 'tv', 'reel', 'stories', 'accounts', 'reels']:
                        valid_links.append(clean_href)
            if valid_links:
                return valid_links[0]
    except Exception as e:
        print(f"Error searching DuckDuckGo for {business_name}: {e}")
    return None

# Reconfigure stdout for UTF-8 to handle Indian names/emojis in Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
TARGET_LEADS_PER_CITY = 120
RAW_JSON_FILENAME = "restaurant_leads_raw.json"
FINAL_CSV_FILENAME = "restaurant_leads_india_top100.csv"

CITIES = [
    "Delhi"
]

# Chains to exclude
EXCLUDED_CHAINS = [
    "mcdonald", "kfc", "domino", "pizza hut", "subway", "starbucks", "burger king", 
    "haldiram", "barbeque nation", "dunkin", "baskin robbins", "chili's", "taco bell", 
    "nando's", "moti mahal", "saravana bhavan", "sagar ratna", "cream stone", 
    "pizza express", "wow! momo", "pizzahut", "subway", "the thickshake factory"
]

def force_english(url):
    return url + "&hl=en" if "?" in url else url + "?hl=en"

def clean_website_url(url):
    if not url:
        return ""
    if "google.com/url" in url:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "q" in qs:
            return qs["q"][0]
    return url

def load_raw_leads():
    if os.path.exists(RAW_JSON_FILENAME):
        try:
            with open(RAW_JSON_FILENAME, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading raw leads: {e}")
    return []

def save_raw_leads(leads):
    try:
        with open(RAW_JSON_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving raw leads: {e}")

def scrape_leads():
    raw_leads = load_raw_leads()
    visited_urls = {lead["Google Maps URL"] for lead in raw_leads}
    
    # Calculate counts per city
    city_counts = {}
    for city in CITIES:
        city_counts[city] = sum(1 for lead in raw_leads if lead.get("City") == city)
    
    print("Current Scraped Lead Counts per City:")
    for city, count in city_counts.items():
        print(f"  - {city}: {count} / {TARGET_LEADS_PER_CITY}")

    with sync_playwright() as p:
        print("\nLaunching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        # Set viewport and user-agent to mock a real desktop browser
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Performance Optimization: block images, fonts, and media
        def block_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                route.abort()
            else:
                route.continue_()
        
        context.route("**/*", block_resources)
        page = context.new_page()

def process_place_details(page, url, city, visited_urls, city_counts, raw_leads):
    place_url = force_english(url)
    print(f"\nLoading details: {place_url.split('/place/')[1].split('/')[0] if '/place/' in place_url else 'Details'}...")
    
    try:
        page.goto(place_url, timeout=25000)
        page.wait_for_selector('h1.DUwDvf', state='attached', timeout=10000)
    except Exception as e:
        print(f"Timeout/Error loading page: {e}")
        return False

    # Extra delay to let dynamic JS finish rendering phone/website
    page.wait_for_timeout(1500)

    # 1. Parse Name
    name = "Unknown"
    try:
        name = page.locator('h1.DUwDvf').first.inner_text().strip()
    except:
        pass

    # Exclude chains early using Name matching
    name_lower = name.lower()
    is_chain = any(chain in name_lower for chain in EXCLUDED_CHAINS)
    if is_chain:
        print(f"Skipping '{name}': Excluded chain.")
        visited_urls.add(url.split("?")[0].split("/data=")[0])
        return False

    # 2. Parse Rating and Reviews
    rating_val = 0.0
    reviews_count = 0
    try:
        rating_container = page.locator('div.F7nice').first
        if rating_container.count() > 0:
            text = rating_container.inner_text()
            rating_match = re.search(r'([\d.]+)', text)
            if rating_match:
                rating_val = float(rating_match.group(1))
            reviews_match = re.search(r'\(([\d,]+)\)', text)
            if reviews_match:
                reviews_count = int(reviews_match.group(1).replace(',', ''))
    except:
        pass

    # (Review and website validation will be done after parsing the website)

    # 3. Parse Phone Number (Mandatory)
    phone = ""
    try:
        phone_el = page.locator('*[data-item-id*="phone:tel:"]').first
        if phone_el.count() > 0:
            item_id = phone_el.get_attribute("data-item-id")
            phone = item_id.replace("phone:tel:", "").strip()
    except:
        pass

    if not phone:
        print(f"Skipping '{name}': No contact number available.")
        visited_urls.add(url.split("?")[0].split("/data=")[0])
        return False

    # 4. Parse Category
    category = "Food Business"
    try:
        category_el = page.locator('button.DkEaL').first
        if category_el.count() > 0:
            category = category_el.inner_text().strip()
        else:
            category_el = page.locator('button[jsaction*="category"]').first
            if category_el.count() > 0:
                category = category_el.inner_text().strip()
    except:
        pass

    # Exclude cloud kitchens
    category_lower = category.lower()
    if "cloud kitchen" in name_lower or "cloud kitchen" in category_lower:
        print(f"Skipping '{name}': Excluded cloud kitchen.")
        visited_urls.add(url.split("?")[0].split("/data=")[0])
        return False

    # 5. Parse Website
    website = ""
    try:
        website_el = page.locator('a[data-item-id="authority"]').first
        if website_el.count() > 0:
            raw_website = website_el.get_attribute("href")
            website = clean_website_url(raw_website)
    except:
        pass

    # Review & Website qualification criteria matching user lead types:
    # 1. Check review count FIRST to avoid unnecessary calls and rate-limiting
    if reviews_count > 700:
        print(f"Skipping '{name}': Too many reviews ({reviews_count} reviews, max 700).")
        visited_urls.add(url.split("?")[0].split("/data=")[0])
        return False

    # Warm Lead Type A: Has custom website, <= 700 reviews
    # Warm Lead Type B: No custom website, <= 700 reviews
    instagram_url = ""
    
    # 1. Check if the Maps website is directly an Instagram link
    if website and "instagram.com" in website.lower():
        instagram_url = website
        website = ""
        
    # 2. Check custom website if available
    if website and not instagram_url:
        domain = urlparse(website).netloc.lower()
        weak_platforms = ["wixsite.com", "blogspot.com", "business.site", "facebook.com", "tumblr.com"]
        if not any(platform in domain for platform in weak_platforms):
            instagram_url = check_instagram_on_website(website)

    # 6. Parse Address
    address = ""
    try:
        address_el = page.locator('*[data-item-id="address"]').first
        if address_el.count() > 0:
            address = address_el.inner_text().strip()
    except:
        pass

    print(f"SUCCESS: Name: '{name}' | Reviews: {reviews_count} | Rating: {rating_val} | Phone: {phone} | Web: {website if website else 'None'} | Insta: {instagram_url}")
    
    # Save Raw Lead
    lead = {
        "Name": name,
        "Category": category,
        "City": city,
        "Google Maps URL": url,
        "Phone": phone,
        "Website": website,
        "Instagram URL": instagram_url,
        "Reviews": reviews_count,
        "Rating": rating_val,
        "Address": address
    }
    
    # Reload from disk to prevent overwriting user edits
    current_disk_leads = load_raw_leads()
    if not any(x.get("Google Maps URL") == lead["Google Maps URL"] for x in current_disk_leads):
        current_disk_leads.append(lead)
        save_raw_leads(current_disk_leads)
        
    raw_leads.append(lead)
    visited_urls.add(url.split("?")[0].split("/data=")[0])
    city_counts[city] += 1
    
    print(f"--> Saved Lead #{city_counts[city]} for {city} <--")
    return True

def scrape_leads():
    raw_leads = load_raw_leads()
    visited_urls = {lead["Google Maps URL"] for lead in raw_leads}
    
    # Calculate counts per city (only counting valid leads under the criteria)
    city_counts = {}
    for city in CITIES:
        city_counts[city] = 0
        for lead in raw_leads:
            if lead.get("City") == city:
                reviews = lead.get("Reviews", 0)
                if reviews <= 700:
                    city_counts[city] += 1
    
    print("Current Scraped Lead Counts per City:")
    for city, count in city_counts.items():
        print(f"  - {city}: {count} / {TARGET_LEADS_PER_CITY}")

    with sync_playwright() as p:
        print("\nLaunching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        # Set viewport and user-agent to mock a real desktop browser
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Performance Optimization: block images, fonts, and media
        def block_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                route.abort()
            else:
                route.continue_()
        
        context.route("**/*", block_resources)
        page = context.new_page()

        for city in CITIES:
            # Check if we already have enough leads for this city
            if city_counts[city] >= TARGET_LEADS_PER_CITY:
                print(f"Already have {city_counts[city]} leads for {city}. Skipping search.")
                continue

            # Sub-queries targeting low-review small businesses
            queries_to_try = [
                f"new cafes in {city}",
                f"new restaurants in {city}",
                f"home bakers in {city}",
                f"waffle shops in {city}",
                f"boutique cafes in {city}",
                f"bakeries in {city}",
                f"pizza in {city}",
                f"burger in {city}",
                f"biryani in {city}",
                f"dhaba in {city}",
                f"sweet shops in {city}",
                f"fast food in {city}",
                f"chinese restaurant in {city}",
                f"family restaurant in {city}",
                f"south indian food in {city}",
                f"street food in {city}",
                f"momos in {city}",
                f"cafes in {city}",
                f"fine dining in {city}"
            ]

            for query_term in queries_to_try:
                if city_counts[city] >= TARGET_LEADS_PER_CITY:
                    break

                print(f"\n================ SEARCHING FOR '{query_term.upper()}' IN {city.upper()} ================")
                search_url = force_english(f"https://www.google.com/maps/search/{query_term.replace(' ', '+')}/")
                
                try:
                    page.goto(search_url, timeout=45000)
                    page.wait_for_selector('div[role="feed"]', timeout=20000)
                except Exception as e:
                    print(f"Error loading search results page for '{query_term}': {e}")
                    continue

                # Scroll search results panel to load a reasonable number of listings
                print("Scrolling search feed...")
                feed_selector = 'div[role="feed"]'
                for _ in range(8):
                    try:
                        page.locator(feed_selector).evaluate("el => el.scrollBy(0, 1200)")
                        page.wait_for_timeout(1000)
                    except:
                        break

                # Extract URLs
                link_elements = page.locator('a[href*="/maps/place/"]').all()
                place_urls = []
                for el in link_elements:
                    try:
                        href = el.get_attribute("href")
                        if href:
                            base_url = href.split("?")[0].split("/data=")[0]
                            if base_url not in visited_urls and base_url not in place_urls:
                                place_urls.append(href)
                    except:
                        continue

                print(f"Found {len(place_urls)} new place links for query '{query_term}'. Processing...")

                # Visit details pages
                for url in place_urls:
                    if city_counts[city] >= TARGET_LEADS_PER_CITY:
                        print(f"Reached target lead count for {city}!")
                        break

                    process_place_details(page, url, city, visited_urls, city_counts, raw_leads)

        browser.close()
        print("\nScraping phase finished successfully!")

def enrich_and_score_leads():
    print("\nProcessing, scoring, and enriching leads...")
    raw_leads = load_raw_leads()
    if not raw_leads:
        print("No leads found to process.")
        return
        
    # Deduplicate leads based on normalized Google Maps URLs
    seen_urls = set()
    leads = []
    for lead in raw_leads:
        url = lead.get("Google Maps URL", "")
        clean_url = url.split("?")[0].split("/data=")[0] if url else ""
        if clean_url not in seen_urls:
            seen_urls.add(clean_url)
            leads.append(lead)
        
    enriched_leads = []
    for lead in leads:
        name = lead["Name"]
        reviews = lead["Reviews"]
        rating = lead["Rating"]
        website = lead["Website"]
        phone = lead["Phone"]
        category = lead["Category"]
        city = lead["City"]
        instagram_url = lead.get("Instagram URL", "")
        
        # Enforce user criteria: Reviews <= 700
        if reviews > 700:
            continue

        # 1. Website Quality Score (1-10)
        # If missing: 1. If weak/basic platform (wix, blogspot, business.site, facebook): 3. Otherwise (custom site): 6
        web_score = 1
        is_weak_website = False
        if website:
            domain = urlparse(website).netloc.lower()
            weak_platforms = ["wixsite.com", "blogspot.com", "business.site", "facebook.com", "instagram.com", "tumblr.com"]
            if any(platform in domain for platform in weak_platforms):
                web_score = 3
                is_weak_website = True
            else:
                web_score = 6 # Functional but standard local site
        else:
            is_weak_website = True

        # Check if it has a custom website (not Wix/Blogspot/etc. and not empty)
        is_custom_web = False
        if website:
            domain = urlparse(website).netloc.lower()
            weak_platforms = ["wixsite.com", "blogspot.com", "business.site", "facebook.com", "instagram.com", "tumblr.com"]
            if not any(platform in domain for platform in weak_platforms):
                is_custom_web = True

        # 2. Google Profile Optimization Score (1-10)
        g_opt_score = 8
        if reviews < 30:
            g_opt_score -= 3
        elif reviews < 70:
            g_opt_score -= 2
        elif reviews < 100:
            g_opt_score -= 1
            
        if not website:
            g_opt_score -= 1
        if rating < 4.0:
            g_opt_score -= 1
        if rating < 3.5:
            g_opt_score -= 1
        g_opt_score = max(1, min(10, g_opt_score))

        # 3. Competitor Review Gap
        comp_reviews_avg = 1000
        review_gap = max(10, comp_reviews_avg - reviews)

        # 4. Decision Maker Accessibility Score (1-10)
        clean_phone = re.sub(r'\D', '', phone)
        is_mobile = False
        if len(clean_phone) >= 10:
            last_10 = clean_phone[-10:]
            if last_10[0] in ['6', '7', '8', '9']:
                is_mobile = True
        
        accessibility_score = 9 if is_mobile else 4

        # 5. Social Media Activity Heuristics (Best effort if Instagram is present)
        is_active_social = bool(instagram_url)

        # 6. Estimated Monthly Revenue Potential
        base_revenue = 400000
        cat_lower = category.lower()
        if "cafe" in cat_lower or "bakery" in cat_lower or "café" in cat_lower:
            base_revenue = 200000
        elif "kitchen" in cat_lower or "cloud" in cat_lower:
            base_revenue = 250000
        elif "fast food" in cat_lower or "sweet" in cat_lower or "snack" in cat_lower:
            base_revenue = 300000
            
        volume_revenue = reviews * rating * 250
        est_revenue = base_revenue + volume_revenue
        est_revenue = int(round(est_revenue / 1000) * 1000)

        # 7. Priority Score (1-100)
        priority_score = 0
        if reviews < 100:
            priority_score += 30
        elif reviews < 300:
            priority_score += 20
        else:
            priority_score += 10
            
        if not is_custom_web:
            priority_score += 30 # Type B has no website, great for pitching landing page
        else:
            priority_score += 20 # Type A has website, great for pitching SEO/reviews
            
        if review_gap >= 2 * reviews:
            priority_score += 15
        if is_mobile:
            priority_score += 15
        if instagram_url:
            priority_score += 10
            
        priority_score = min(100, max(0, priority_score))

        # 8. Classify Lead Type & Purchase Probability
        if is_custom_web:
            lead_type = "Type A (With Website)"
        else:
            lead_type = "Type B (No Website)"
        purchase_prob = "High"

        # 9. Why they are a good prospect & Biggest problem
        if not is_custom_web:
            biggest_problem = "Lacks a custom website for Google Search and Maps conversion"
            why_good = f"Active local business in {city}, but completely missing out on high-intent search traffic due to lack of a custom landing page. Standard competitors have 1000+ reviews and websites."
        else:
            biggest_problem = f"Stuck at only {reviews} reviews despite having a custom website"
            why_good = f"Active local business in {city} with a custom website, but currently lags behind competitor review volume (average 1000+ reviews), keeping them lower on Google Maps packs."

        # 10. Personalized Pitch Angle
        if not is_custom_web:
            pitch_angle = f"Turn your {city} local searches and Google Maps presence into direct dine-in customers. We will build a custom mobile-friendly website and help automate review generation."
        else:
            pitch_angle = f"You have a website, but only {reviews} reviews. Let's help you double your reviews to match {city}'s top competitors."

        enriched_leads.append({
            "Business Name": name,
            "Category": category,
            "City": city,
            "Google Maps URL": lead["Google Maps URL"],
            "Phone": phone,
            "Website": website if website else "None",
            "Instagram URL": instagram_url,
            "Google Reviews": reviews,
            "Rating": rating,
            "Address": lead["Address"],
            "Estimated Monthly Revenue Potential": f"₹{est_revenue:,}",
            "Website Score": web_score,
            "Google Profile Optimization Score": g_opt_score,
            "Review Gap": review_gap,
            "Decision Maker Accessibility Score": accessibility_score,
            "Priority Score": priority_score,
            "Lead Type": lead_type,
            "Purchase Probability": purchase_prob,
            "Biggest Problem": biggest_problem,
            "Why Good Prospect": why_good,
            "Personalized Pitch Angle": pitch_angle
        })

    # Sort leads by Priority Score descending
    enriched_leads.sort(key=lambda x: x["Priority Score"], reverse=True)
    
    # Check that we have enough leads
    print(f"Scored {len(enriched_leads)} leads in total.")
    
    # Save the TOP 100 to CSV
    top_100 = enriched_leads[:100]
    
    # If we have less than 100, save all
    if len(top_100) < 100:
        print(f"Warning: Only have {len(top_100)} leads. Will output what we have.")
        
    try:
        for filename in [FINAL_CSV_FILENAME, "restaurant_leads_india.csv"]:
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    "Business Name", "Category", "City", "Phone", "Website", "Instagram URL",
                    "Google Reviews", "Rating", "Website Score", "Review Gap", 
                    "Priority Score", "Lead Type", "Purchase Probability", "Personalized Pitch Angle"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(top_100)
            print(f"Successfully wrote top {len(top_100)} leads to {filename}")
        
        # Also write details of all leads (including scores, etc) to a rich JSON file
        with open("restaurant_leads_india_top100.json", 'w', encoding='utf-8') as f:
            json.dump(top_100, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error writing CSV file: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--score-only":
        enrich_and_score_leads()
    else:
        scrape_leads()
        enrich_and_score_leads()
