import os
import re
from bs4 import BeautifulSoup

dir_path = "audits_other_cities"
files = [f for f in os.listdir(dir_path) if f.endswith(".html")]

delhi_leads = []
other_leads = []

for file in files:
    file_path = os.path.join(dir_path, file)
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        
        # Extract name, city, phone, etc from text
        header = soup.find("header")
        if header:
            h1 = header.find("h1")
            p = header.find("p")
            if p:
                text = p.get_text()
                # format: Business Name • City
                parts = text.split("•")
                if len(parts) == 2:
                    name = parts[0].strip()
                    city = parts[1].strip()
                    
                    # Extract phone and reviews
                    phone = ""
                    reviews = 0
                    info_rows = soup.find_all("div", class_="info-row")
                    for row in info_rows:
                        spans = row.find_all("span")
                        if len(spans) == 2:
                            label = spans[0].get_text().strip().lower()
                            val = spans[1].get_text().strip()
                            if "phone" in label:
                                phone = val
                            elif "reviews" in label or "reviews count" in label:
                                try:
                                    reviews = int(val.replace("Reviews", "").strip())
                                except:
                                    pass
                    
                    lead_data = {
                        "Name": name,
                        "City": city,
                        "Phone": phone,
                        "Reviews": reviews,
                        "File": file
                    }
                    if "delhi" in city.lower():
                        delhi_leads.append(lead_data)
                    else:
                        other_leads.append(lead_data)

print(f"Total files: {len(files)}")
print(f"Delhi leads found: {len(delhi_leads)}")
for l in delhi_leads:
    print(f"  - {l['Name']} ({l['Phone']}) | Reviews: {l['Reviews']}")
print(f"Other leads count: {len(other_leads)}")
