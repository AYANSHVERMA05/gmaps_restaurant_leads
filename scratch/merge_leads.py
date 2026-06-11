import subprocess
import json

raw_file = "restaurant_leads_raw.json"

# Load current raw leads
try:
    with open(raw_file, "r", encoding="utf-8") as f:
        current_leads = json.load(f)
except Exception as e:
    print(f"Error reading {raw_file}: {e}")
    current_leads = []

# Normalization helper
def normalize_url(url):
    if not url:
        return ""
    return url.split("?")[0].split("/data=")[0]

seen_urls = {normalize_url(l.get("Google Maps URL")) for l in current_leads}
print(f"Current unique URLs in raw database: {len(seen_urls)}")

# Fetch historical leads
try:
    output = subprocess.check_output(['git', 'show', '9aa0623e5313883f0835235529d7b1ab24aae7f2:restaurant_leads_india_top100.json']).decode('utf-8')
    hist_leads = json.loads(output)
except Exception as e:
    print(f"Error fetching historical leads: {e}")
    hist_leads = []

merged_count = 0
for l in hist_leads:
    reviews = l.get("Google Reviews", 0)
    url = l.get("Google Maps URL", "")
    norm_url = normalize_url(url)
    
    if reviews <= 700:
        if norm_url not in seen_urls:
            # Map keys to raw lead format
            raw_lead = {
                "Name": l.get("Business Name"),
                "Category": l.get("Category"),
                "City": l.get("City"),
                "Google Maps URL": url,
                "Phone": l.get("Phone"),
                "Website": l.get("Website"),
                "Instagram URL": l.get("Instagram URL", ""),
                "Reviews": reviews,
                "Rating": l.get("Rating"),
                "Address": l.get("Address")
            }
            current_leads.append(raw_lead)
            seen_urls.add(norm_url)
            merged_count += 1

print(f"Merged {merged_count} historical leads under 700 reviews.")
print(f"Total leads in raw database: {len(current_leads)}")

with open(raw_file, "w", encoding="utf-8") as f:
    json.dump(current_leads, f, indent=4, ensure_ascii=False)

print("Saved merged database.")
