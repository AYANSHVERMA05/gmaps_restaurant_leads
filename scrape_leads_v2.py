import os
import re
import csv
import json
import sys
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

# Reconfigure stdout for UTF-8 to handle Indian names/emojis in Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
TARGET_LEADS_PER_CITY = 15
RAW_JSON_FILENAME = "restaurant_leads_raw.json"
FINAL_CSV_FILENAME = "restaurant_leads_india_top100.csv"

# Target cities list
CITIES = [
    "Hyderabad", "Bengaluru", "Pune", "Ahmedabad", "Jaipur", 
    "Indore", "Surat", "Lucknow", "Nagpur", "Chennai"
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

    # Filter reviews < 100
    if reviews_count >= 100:
        print(f"Skipping '{name}': Too many reviews ({reviews_count}).")
        visited_urls.add(url.split("?")[0].split("/data=")[0])
        return False

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

    # 5. Parse Website
    website = ""
    try:
        website_el = page.locator('a[data-item-id="authority"]').first
        if website_el.count() > 0:
            raw_website = website_el.get_attribute("href")
            website = clean_website_url(raw_website)
    except:
        pass

    # 6. Parse Address
    address = ""
    try:
        address_el = page.locator('*[data-item-id="address"]').first
        if address_el.count() > 0:
            address = address_el.inner_text().strip()
    except:
        pass

    print(f"SUCCESS: Name: '{name}' | Reviews: {reviews_count} | Rating: {rating_val} | Phone: {phone} | Web: {website if website else 'None'}")
    
    # Save Raw Lead
    lead = {
        "Name": name,
        "Category": category,
        "City": city,
        "Google Maps URL": url,
        "Phone": phone,
        "Website": website,
        "Reviews": reviews_count,
        "Rating": rating_val,
        "Address": address
    }
    
    raw_leads.append(lead)
    visited_urls.add(url.split("?")[0].split("/data=")[0])
    city_counts[city] += 1
    save_raw_leads(raw_leads)
    
    print(f"--> Saved Lead #{city_counts[city]} for {city} <--")
    return True

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

        for city in CITIES:
            # Check if we already have enough leads for this city
            if city_counts[city] >= TARGET_LEADS_PER_CITY:
                print(f"Already have {city_counts[city]} leads for {city}. Skipping search.")
                continue

            # Sub-queries targeting low-review small businesses
            queries_to_try = [
                f"cafes in {city}",
                f"bakeries in {city}",
                f"cloud kitchens in {city}",
                f"new restaurants in {city}",
                f"restaurants in {city}"
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
    leads = load_raw_leads()
    if not leads:
        print("No leads found to process.")
        return
        
    enriched_leads = []
    for lead in leads:
        name = lead["Name"]
        reviews = lead["Reviews"]
        rating = lead["Rating"]
        website = lead["Website"]
        phone = lead["Phone"]
        category = lead["Category"]
        city = lead["City"]
        
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

        # 2. Google Profile Optimization Score (1-10)
        # Start at 8. Subtract for flaws.
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
        # Top local average is assumed to be 500 reviews
        comp_reviews_avg = 500
        review_gap = max(10, comp_reviews_avg - reviews)

        # 4. Decision Maker Accessibility Score (1-10)
        # Mobile number = 9 (starts with 6,7,8,9 or matches 10 digits). Landline = 4
        clean_phone = re.sub(r'\D', '', phone)
        # Indian mobile numbers start with 6, 7, 8, or 9 and have 10 digits (excluding leading 0 or 91)
        is_mobile = False
        if len(clean_phone) >= 10:
            last_10 = clean_phone[-10:]
            if last_10[0] in ['6', '7', '8', '9']:
                is_mobile = True
        
        accessibility_score = 9 if is_mobile else 4

        # 5. Social Media Activity Heuristics
        # Check if website is a facebook or instagram page, or default to True if they are cafes/bakeries/restaurants (active)
        is_active_social = False
        if website and ("facebook.com" in website.lower() or "instagram.com" in website.lower()):
            is_active_social = True
        elif not website and (category.lower() in ["cafe", "bakery", "café", "cloud kitchen"]):
            is_active_social = True # High likelihood they use Instagram
        else:
            # Let's say a general restaurant has a 50% chance if they have a mobile number
            is_active_social = is_mobile

        # 6. Estimated Monthly Revenue Potential
        # Base on category: Cafe/Bakery: ₹200k, Cloud Kitchen: ₹250k, Restaurant: ₹400k
        base_revenue = 400000
        cat_lower = category.lower()
        if "cafe" in cat_lower or "bakery" in cat_lower or "café" in cat_lower:
            base_revenue = 200000
        elif "kitchen" in cat_lower or "cloud" in cat_lower:
            base_revenue = 250000
        elif "fast food" in cat_lower or "sweet" in cat_lower or "snack" in cat_lower:
            base_revenue = 300000
            
        # Add proxy transaction volume
        volume_revenue = reviews * rating * 250
        est_revenue = base_revenue + volume_revenue
        # Round to nearest thousand
        est_revenue = int(round(est_revenue / 1000) * 1000)

        # 7. Priority Score (1-100)
        priority_score = 0
        if reviews < 50:
            priority_score += 30
        if not website:
            priority_score += 20
        if is_weak_website and website:
            priority_score += 15
        # Since reviews are < 100 and top competitor is 500 reviews, competitor reviews (500) is always >= 2x reviews (max 99 * 2 = 198)
        # So this is always True
        if review_gap >= 2 * reviews:
            priority_score += 15
        if is_mobile:
            priority_score += 10
        if is_active_social:
            priority_score += 10
            
        # Guarantee range and format
        priority_score = min(100, max(0, priority_score))

        # 8. Purchase Probability
        if priority_score >= 85:
            purchase_prob = "High"
        elif priority_score >= 65:
            purchase_prob = "Medium"
        else:
            purchase_prob = "Low"

        # 9. Why they are a good prospect & Biggest problem
        if not website:
            biggest_problem = "No website / losing all local search and delivery referral traffic"
            why_good = f"Zero web presence. Standard competitor in {city} has over 500 reviews and a website. Easy visual upgrade pitch."
        elif is_weak_website:
            biggest_problem = f"Weak web footprint ({urlparse(website).netloc})"
            why_good = "Has website but on a weak/outdated landing page with negligible SEO signals."
        else:
            biggest_problem = f"Stuck at only {reviews} reviews while competitor average is 500+"
            why_good = "Active business with custom website but lacks reviews volume to rank high in Maps packs."

        # 10. Personalized Pitch Angle
        if reviews == 0:
            pitch_angle = f"Competitors in {city} have 500+ reviews. We'll set up your Review System and automate getting reviews from every table dine-in to rank in top 3 maps."
        elif not website:
            pitch_angle = f"Missing website and losing local {city} traffic. We will build an SEO-optimized landing page and double your Google reviews."
        elif is_weak_website:
            pitch_angle = f"Upgrade your weak link ({urlparse(website).netloc}) to an online-ordering ready SEO site and launch our automatic review growth tool."
        else:
            pitch_angle = f"Excellent {rating} rating, but you only have {reviews} reviews. Competitors in {city} have 5x reviews. We'll close that gap in 60 days."

        enriched_leads.append({
            "Business Name": name,
            "Category": category,
            "City": city,
            "Google Maps URL": lead["Google Maps URL"],
            "Phone": phone,
            "Website": website if website else "None",
            "Google Reviews": reviews,
            "Rating": rating,
            "Address": lead["Address"],
            "Estimated Monthly Revenue Potential": f"₹{est_revenue:,}",
            "Website Score": web_score,
            "Google Profile Optimization Score": g_opt_score,
            "Review Gap": review_gap,
            "Decision Maker Accessibility Score": accessibility_score,
            "Priority Score": priority_score,
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
        with open(FINAL_CSV_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "Business Name", "Category", "City", "Phone", "Website", 
                "Google Reviews", "Rating", "Website Score", "Review Gap", 
                "Priority Score", "Purchase Probability", "Personalized Pitch Angle"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(top_100)
        print(f"Successfully wrote top {len(top_100)} leads to {FINAL_CSV_FILENAME}")
        
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
