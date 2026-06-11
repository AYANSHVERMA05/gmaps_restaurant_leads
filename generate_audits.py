import os
import re
import json
import sys

# Setup stdout for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

JSON_FILENAME = "restaurant_leads_india_top100.json"
OUTPUT_DIR = "audits"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Growth Audit: {business_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0b0f19;
            --bg-card: #161f30;
            --accent-purple: #8b5cf6;
            --accent-blue: #3b82f6;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --score-high: #10b981;
            --score-medium: #f59e0b;
            --score-low: #ef4444;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        h1, h2, h3 {{
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
        }}

        header h1 {{
            font-size: 2.8rem;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        header p {{
            color: var(--text-muted);
            font-size: 1.1rem;
        }}

        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .card {{
            background: var(--bg-card);
            border-radius: 1rem;
            padding: 1.8rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s ease;
        }}

        .card:hover {{
            transform: translateY(-4px);
        }}

        .score-card {{
            text-align: center;
        }}

        .gauge-container {{
            position: relative;
            width: 150px;
            height: 150px;
            margin: 1rem auto;
        }}

        .gauge {{
            width: 100%;
            height: 100%;
            transform: rotate(-90deg);
        }}

        .gauge-circle {{
            fill: none;
            stroke-width: 8;
        }}

        .gauge-bg {{
            stroke: rgba(255, 255, 255, 0.05);
        }}

        .gauge-val {{
            stroke: var(--accent-purple);
            stroke-linecap: round;
            transition: stroke-dasharray 0.5s ease;
        }}

        .gauge-text {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-family: 'Outfit', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
        }}

        .score-label {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-top: 0.5rem;
        }}

        .score-desc {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}

        .badge {{
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 2rem;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 1rem;
        }}

        .badge-hot {{ background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge-warm {{ background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-medium {{ background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}

        .info-panel {{
            margin-bottom: 3rem;
        }}

        .info-panel h2 {{
            font-size: 1.8rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.85rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .info-row span:first-child {{
            color: var(--text-muted);
        }}

        .info-row span:last-child {{
            font-weight: 500;
        }}

        .graph-card {{
            margin-bottom: 3rem;
        }}

        .bar-container {{
            margin-top: 1.5rem;
        }}

        .bar-row {{
            margin-bottom: 1.5rem;
        }}

        .bar-labels {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.95rem;
        }}

        .bar-outer {{
            width: 100%;
            height: 20px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            overflow: hidden;
        }}

        .bar-inner {{
            height: 100%;
            border-radius: 10px;
        }}

        .bar-own {{
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
        }}

        .bar-comp {{
            background: linear-gradient(90deg, #8b5cf6, #a78bfa);
        }}

        .finding-box {{
            background-color: rgba(239, 68, 68, 0.08);
            border-left: 4px solid var(--score-low);
            padding: 1.25rem;
            border-radius: 0 0.5rem 0.5rem 0;
            margin-bottom: 1.5rem;
        }}

        .finding-box h4 {{
            color: #f87171;
            font-size: 1.1rem;
            margin-bottom: 0.25rem;
            font-family: 'Outfit', sans-serif;
        }}

        .recommendation-list {{
            list-style: none;
        }}

        .recommendation-item {{
            position: relative;
            padding-left: 2rem;
            margin-bottom: 1.25rem;
        }}

        .recommendation-item::before {{
            content: "✓";
            position: absolute;
            left: 0;
            top: 0;
            color: var(--score-high);
            font-weight: bold;
            font-size: 1.2rem;
            line-height: 1.2;
        }}

        .recommendation-title {{
            font-weight: 700;
            margin-bottom: 0.2rem;
        }}

        .recommendation-desc {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .cta-btn {{
            display: block;
            width: 100%;
            text-align: center;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            color: white;
            text-decoration: none;
            padding: 1.2rem;
            border-radius: 0.75rem;
            font-family: 'Outfit', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
            transition: all 0.2s ease;
            margin-top: 2rem;
        }}

        .cta-btn:hover {{
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6);
        }}

        @media (max-width: 600px) {{
            header h1 {{
                font-size: 2.2rem;
            }}
            body {{
                padding: 1rem 0.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="badge {badge_class}">{lead_type}</div>
            <h1>Local Visibility Audit</h1>
            <p>{business_name} • {city}</p>
        </header>

        <section class="grid-3">
            <div class="card score-card">
                <div class="gauge-container">
                    <svg class="gauge" viewBox="0 0 100 100">
                        <circle class="gauge-circle gauge-bg" cx="50" cy="50" r="45"></circle>
                        <circle class="gauge-circle gauge-val" cx="50" cy="50" r="45" stroke-dasharray="{g_opt_dash} 283" stroke="#8b5cf6"></circle>
                    </svg>
                    <div class="gauge-text">{g_opt_pct}%</div>
                </div>
                <div class="score-label">Google Profile Health</div>
                <div class="score-desc">Based on review count, ratings & details.</div>
            </div>

            <div class="card score-card">
                <div class="gauge-container">
                    <svg class="gauge" viewBox="0 0 100 100">
                        <circle class="gauge-circle gauge-bg" cx="50" cy="50" r="45"></circle>
                        <circle class="gauge-circle gauge-val" cx="50" cy="50" r="45" stroke-dasharray="{web_dash} 283" stroke="#3b82f6"></circle>
                    </svg>
                    <div class="gauge-text">{web_pct}%</div>
                </div>
                <div class="score-label">Website Performance</div>
                <div class="score-desc">Based on platforms and landing page structure.</div>
            </div>

            <div class="card score-card">
                <div class="gauge-container">
                    <svg class="gauge" viewBox="0 0 100 100">
                        <circle class="gauge-circle gauge-bg" cx="50" cy="50" r="45"></circle>
                        <circle class="gauge-circle gauge-val" cx="50" cy="50" r="45" stroke-dasharray="{priority_dash} 283" stroke="#10b981"></circle>
                    </svg>
                    <div class="gauge-text">{priority_score}%</div>
                </div>
                <div class="score-label">Priority Optimization Value</div>
                <div class="score-desc">Potential ROI from GBP and SEO optimization.</div>
            </div>
        </section>

        <section class="card info-panel">
            <h2>Business Summary</h2>
            <div class="info-row">
                <span>Category</span>
                <span>{category}</span>
            </div>
            <div class="info-row">
                <span>Phone Number</span>
                <span>{phone}</span>
            </div>
            <div class="info-row">
                <span>Website</span>
                <span>{website_link}</span>
            </div>
            <div class="info-row">
                <span>Address</span>
                <span>{address}</span>
            </div>
            <div class="info-row">
                <span>Estimated Monthly Revenue Potential</span>
                <span>{est_revenue}</span>
            </div>
        </section>

        <section class="card graph-card">
            <h2>Competitor Analysis</h2>
            <p style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 1rem;">
                Comparison of review volume against the local average competitor baseline (500 reviews) in {city}.
            </p>
            <div class="bar-container">
                <div class="bar-row">
                    <div class="bar-labels">
                        <span>{business_name}</span>
                        <span>{reviews} Reviews</span>
                    </div>
                    <div class="bar-outer">
                        <div class="bar-inner bar-own" style="width: {reviews_bar_pct}%;"></div>
                    </div>
                </div>
                <div class="bar-row">
                    <div class="bar-labels">
                        <span>Average Competitor Average</span>
                        <span>500 Reviews</span>
                    </div>
                    <div class="bar-outer">
                        <div class="bar-inner bar-comp" style="width: 100%;"></div>
                    </div>
                </div>
            </div>
        </section>

        <section class="card info-panel">
            <h2>Core Discovery & Findings</h2>
            <div class="finding-box">
                <h4>Biggest Visibility Problem</h4>
                <p>{biggest_problem}</p>
            </div>
            <p style="color: var(--text-main); font-size: 1rem; margin-top: 1rem; line-height: 1.7;">
                <strong>Why this is a high-intent prospect:</strong><br>
                {why_good}
            </p>
        </section>

        <section class="card info-panel">
            <h2>Recommended local SEO Action Plan</h2>
            <ul class="recommendation-list">
                <li class="recommendation-item">
                    <div class="recommendation-title">Close the {review_gap}-Review Gap</div>
                    <div class="recommendation-desc">Implement an automated review generation funnel to collect dynamic feedbacks from table dine-ins.</div>
                </li>
                <li class="recommendation-item">
                    <div class="recommendation-title">Optimise Google Maps Ranking Factors</div>
                    <div class="recommendation-desc">Update categories, local hours, address validation, and configure automated FAQs on the profile.</div>
                </li>
                <li class="recommendation-item">
                    <div class="recommendation-title">Implement Direct Booking / Ordering CTA</div>
                    <div class="recommendation-desc">Provide direct links to WhatsApp ordering or mobile calls on your profile to bypass high-commission food aggregators.</div>
                </li>
                {extra_website_recommendation}
            </ul>
        </section>

        <section style="margin-bottom: 4rem;">
            <a href="https://wa.me/{clean_phone}?text={pitch_url_encoded}" class="cta-btn" target="_blank">
                Pitch Business Owner (WhatsApp Link)
            </a>
        </section>
    </div>
</body>
</html>
"""

def clean_phone_number(phone):
    return re.sub(r'\D', '', phone)

def generate_report(lead):
    # Calculate gauge percentages (dasharrays based on 283 full circle stroke)
    g_opt_score = lead.get("Google Profile Optimization Score", 5)
    g_opt_pct = g_opt_score * 10
    g_opt_dash = int((g_opt_pct / 100) * 283)

    web_score = lead.get("Website Score", 1)
    web_pct = int((web_score / 10) * 100)
    web_dash = int((web_pct / 100) * 283)

    priority_score = lead.get("Priority Score", 50)
    priority_dash = int((priority_score / 100) * 283)

    # Competitor gap progress bar styling
    reviews = lead.get("Google Reviews", 0)
    reviews_bar_pct = min(100, int((reviews / 500) * 100))

    # Badge styling
    lead_type = lead.get("Lead Type", "🔥 Hot Lead")
    if "Hot" in lead_type:
        badge_class = "badge-hot"
    elif "Warm" in lead_type:
        badge_class = "badge-warm"
    else:
        badge_class = "badge-medium"

    # Website specific recommendation
    website = lead.get("Website", "None")
    if website == "None" or not website:
        website_link = '<span style="color: var(--score-low);">No Website Found</span>'
        extra_web = """<li class="recommendation-item">
                    <div class="recommendation-title">Build a Conversion-Ready Landing Page</div>
                    <div class="recommendation-desc">Create a mobile-optimized, fast page to convert Google Maps searchers into delivery/reservation orders directly.</div>
                </li>"""
    else:
        website_link = f'<a href="{website}" target="_blank" style="color: var(--accent-blue); text-decoration: none;">{website}</a>'
        extra_web = """<li class="recommendation-item">
                    <div class="recommendation-title">Optimise Current Website Conversion Funnels</div>
                    <div class="recommendation-desc">Improve SEO meta-tags, structural loading speeds, and install clear Call-To-Action conversion anchors.</div>
                </li>"""

    # Clean phone for CTA links
    phone = lead.get("Phone", "")
    clean_phone = clean_phone_number(phone)
    # Add country code for WhatsApp if needed (Indian mobile numbers)
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone

    # WhatsApp Pitch Encoding
    pitch_text = f"Hi! I just did a local visibility and Google Maps review audit for {lead['Business Name']}. You have an amazing {lead['Rating']} rating but are currently behind your local competitors by over {lead['Review Gap']} reviews. We have built a free action plan for you to rank top-3 on Maps and get more dine-in bookings. Let me know if you would like me to share it!"
    from urllib.parse import quote
    pitch_url_encoded = quote(pitch_text)

    # Format HTML
    html_content = HTML_TEMPLATE.format(
        business_name=lead.get("Business Name", "Unknown Business"),
        city=lead.get("City", ""),
        lead_type=lead_type,
        badge_class=badge_class,
        g_opt_pct=g_opt_pct,
        g_opt_dash=g_opt_dash,
        web_pct=web_pct,
        web_dash=web_dash,
        priority_score=priority_score,
        priority_dash=priority_dash,
        category=lead.get("Category", ""),
        phone=phone,
        website_link=website_link,
        address=lead.get("Address", "No physical address listed"),
        est_revenue=lead.get("Estimated Monthly Revenue Potential", "₹0"),
        reviews=reviews,
        reviews_bar_pct=reviews_bar_pct,
        biggest_problem=lead.get("Biggest Problem", ""),
        why_good=lead.get("Why Good Prospect", ""),
        review_gap=lead.get("Review Gap", 0),
        extra_website_recommendation=extra_web,
        clean_phone=clean_phone,
        pitch_url_encoded=pitch_url_encoded
    )

    # Create audits folder if it does not exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Sanitize filename
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', lead.get("Business Name", "business"))
    filename = os.path.join(OUTPUT_DIR, f"audit_{safe_name}.html")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filename

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Growth Audits Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0b0f19;
            --bg-card: #161f30;
            --accent-purple: #8b5cf6;
            --accent-blue: #3b82f6;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --score-high: #10b981;
            --score-medium: #f59e0b;
            --score-low: #ef4444;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            line-height: 1.6;
            padding: 3rem 1.5rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 3rem;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 3rem;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        header p {
            color: var(--text-muted);
            font-size: 1.2rem;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .stat-card {
            background: var(--bg-card);
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            text-align: center;
            transition: transform 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
        }

        .stat-val {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .stat-card.total .stat-val { color: var(--accent-blue); }
        .stat-card.hot .stat-val { color: #f87171; }
        .stat-card.warm .stat-val { color: #fbbf24; }
        .stat-card.medium .stat-val { color: #60a5fa; }

        .stat-label {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-muted);
        }

        /* Controls Section */
        .controls-card {
            background: var(--bg-card);
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            align-items: center;
            justify-content: space-between;
        }

        .search-box {
            flex: 1;
            min-width: 300px;
            position: relative;
        }

        .search-box input {
            width: 100%;
            padding: 0.85rem 1rem;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 0.5rem;
            color: white;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            transition: all 0.2s ease;
        }

        .search-box input:focus {
            outline: none;
            border-color: var(--accent-blue);
            background: rgba(255, 255, 255, 0.05);
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
        }

        .filter-buttons {
            display: flex;
            gap: 0.75rem;
        }

        .filter-btn {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-muted);
            padding: 0.6rem 1.2rem;
            border-radius: 2rem;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .filter-btn:hover, .filter-btn.active {
            background: var(--accent-purple);
            color: white;
            border-color: var(--accent-purple);
        }

        .sort-box select {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            padding: 0.6rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.9rem;
            cursor: pointer;
            outline: none;
        }

        /* Leads Grid */
        .leads-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 1.5rem;
        }

        .lead-card {
            background: var(--bg-card);
            border-radius: 1rem;
            padding: 1.8rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .lead-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
            border-color: rgba(255, 255, 255, 0.1);
        }

        .lead-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .badge {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 2rem;
            font-size: 0.8rem;
            font-weight: 700;
        }

        .badge-hot { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-warm { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-medium { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }

        .priority-score {
            font-family: 'Outfit', sans-serif;
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--score-high);
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .priority-score span {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-weight: 500;
        }

        .lead-name {
            font-family: 'Outfit', sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            line-height: 1.3;
        }

        .lead-meta {
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .meta-item {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            padding-bottom: 0.3rem;
        }

        .meta-item span:last-child {
            color: var(--text-main);
            font-weight: 500;
        }

        .lead-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            margin-top: auto;
        }

        .btn {
            display: block;
            text-align: center;
            text-decoration: none;
            padding: 0.75rem;
            border-radius: 0.5rem;
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            font-weight: 700;
            transition: all 0.2s ease;
        }

        .btn-audit {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            color: white;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
        }

        .btn-audit:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 18px rgba(139, 92, 246, 0.5);
        }

        .btn-pitch {
            background: rgba(255, 255, 255, 0.05);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .btn-pitch:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: scale(1.02);
        }

        @media (max-width: 768px) {
            body { padding: 2rem 1rem; }
            h1 { font-size: 2.2rem; }
            .controls-card { flex-direction: column; align-items: stretch; }
            .search-box { min-width: 100%; }
            .filter-buttons { overflow-x: auto; padding-bottom: 0.5rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Local SEO Lead Audits</h1>
            <p>Interactive dashboard containing visibility and conversion audit reports for restaurant leads in India.</p>
        </header>

        <!-- Stats -->
        <section class="stats-grid">
            <div class="stat-card total">
                <div class="stat-val">{total_leads}</div>
                <div class="stat-label">Total Leads</div>
            </div>
            <div class="stat-card hot">
                <div class="stat-val">{hot_leads}</div>
                <div class="stat-label">🔥 Hot Leads</div>
            </div>
            <div class="stat-card warm">
                <div class="stat-val">{warm_leads}</div>
                <div class="stat-label">🟠 Warm Leads</div>
            </div>
            <div class="stat-card medium">
                <div class="stat-val">{medium_leads}</div>
                <div class="stat-label">🟡 Medium Leads</div>
            </div>
        </section>

        <!-- Controls -->
        <section class="controls-card">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search business name, category, or city...">
            </div>
            <div class="filter-buttons">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="🔥 Hot Lead">🔥 Hot</button>
                <button class="filter-btn" data-filter="🟠 Warm Lead">🟠 Warm</button>
                <button class="filter-btn" data-filter="🟡 Medium Lead">🟡 Medium</button>
            </div>
            <div class="sort-box">
                <select id="sortSelect">
                    <option value="priority-desc">Priority: High to Low</option>
                    <option value="reviews-desc">Reviews: High to Low</option>
                    <option value="reviews-asc">Reviews: Low to High</option>
                    <option value="name-asc">Name: A to Z</option>
                </select>
            </div>
        </section>

        <!-- Leads Grid -->
        <main class="leads-grid" id="leadsGrid">
            <!-- Dynamically populated via JS -->
        </main>
    </div>

    <script>
        const leadsData = {leads_json_str};

        const searchInput = document.getElementById('searchInput');
        const filterBtns = document.querySelectorAll('.filter-btn');
        const sortSelect = document.getElementById('sortSelect');
        const leadsGrid = document.getElementById('leadsGrid');

        let activeFilter = 'all';
        let searchQuery = '';
        let activeSort = 'priority-desc';

        function renderLeads() {
            // Filter
            let filtered = leadsData.filter(lead => {
                const matchesFilter = activeFilter === 'all' || lead.type === activeFilter;
                const matchesSearch = lead.name.toLowerCase().includes(searchQuery) ||
                                      lead.city.toLowerCase().includes(searchQuery) ||
                                      lead.category.toLowerCase().includes(searchQuery);
                return matchesFilter && matchesSearch;
            });

            // Sort
            filtered.sort((a, b) => {
                if (activeSort === 'priority-desc') return b.priority - a.priority;
                if (activeSort === 'reviews-desc') return b.reviews - a.reviews;
                if (activeSort === 'reviews-asc') return a.reviews - b.reviews;
                if (activeSort === 'name-asc') return a.name.localeCompare(b.name);
                return 0;
            });

            // Render
            leadsGrid.innerHTML = filtered.map(lead => `
                <div class="lead-card">
                    <div>
                        <div class="lead-header">
                            <span class="badge ${lead.badge_class}">${lead.type}</span>
                            <div class="priority-score">${lead.priority}<span>score</span></div>
                        </div>
                        <div class="lead-name">${lead.name}</div>
                        <div class="lead-meta">
                            <div class="meta-item">
                                <span>City</span>
                                <span>${lead.city}</span>
                            </div>
                            <div class="meta-item">
                                <span>Category</span>
                                <span>${lead.category}</span>
                            </div>
                            <div class="meta-item">
                                <span>Google Reviews</span>
                                <span>${lead.reviews}</span>
                            </div>
                            <div class="meta-item">
                                <span>Phone</span>
                                <span>${lead.phone || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="lead-actions">
                        <a href="${lead.url}" class="btn btn-audit" target="_blank">View Audit</a>
                        <a href="${lead.wa_link}" class="btn btn-pitch" target="_blank">WhatsApp Pitch</a>
                    </div>
                </div>
            `).join('');
        }

        // Event Listeners
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            renderLeads();
        });

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeFilter = btn.getAttribute('data-filter');
                renderLeads();
            });
        });

        sortSelect.addEventListener('change', (e) => {
            activeSort = e.target.value;
            renderLeads();
        });

        // Initial render
        renderLeads();
    </script>
</body>
</html>
"""

def generate_index_dashboard(leads):
    # Construct a list of records for the dashboard
    records = []
    for lead in leads:
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', lead.get("Business Name", "business"))
        audit_url = f"audits/audit_{safe_name}.html"
        
        # Calculate badge class
        lead_type = lead.get("Lead Type", "🔥 Hot Lead")
        if "Hot" in lead_type:
            badge_class = "badge-hot"
        elif "Warm" in lead_type:
            badge_class = "badge-warm"
        else:
            badge_class = "badge-medium"
            
        phone = lead.get("Phone", "")
        clean_phone = clean_phone_number(phone)
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
            
        pitch_text = f"Hi! I just did a local visibility and Google Maps review audit for {lead['Business Name']}. You have an amazing {lead['Rating']} rating but are currently behind your local competitors by over {lead['Review Gap']} reviews. We have built a free action plan for you to rank top-3 on Maps and get more dine-in bookings. Let me know if you would like me to share it!"
        from urllib.parse import quote
        pitch_url_encoded = quote(pitch_text)
        wa_link = f"https://wa.me/{clean_phone}?text={pitch_url_encoded}"

        records.append({
            "name": lead.get("Business Name", "Unknown"),
            "city": lead.get("City", ""),
            "category": lead.get("Category", ""),
            "reviews": lead.get("Google Reviews", 0),
            "priority": lead.get("Priority Score", 50),
            "type": lead_type,
            "badge_class": badge_class,
            "url": audit_url,
            "wa_link": wa_link,
            "phone": phone
        })
        
    # Stats counts
    total_leads = len(records)
    hot_leads = sum(1 for r in records if "Hot" in r["type"])
    warm_leads = sum(1 for r in records if "Warm" in r["type"])
    medium_leads = sum(1 for r in records if "Medium" in r["type"])

    html = INDEX_TEMPLATE
    html = html.replace("{total_leads}", str(total_leads))
    html = html.replace("{hot_leads}", str(hot_leads))
    html = html.replace("{warm_leads}", str(warm_leads))
    html = html.replace("{medium_leads}", str(medium_leads))
    html = html.replace("{leads_json_str}", json.dumps(records, indent=2))

    filename = "index.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename

def main():
    if not os.path.exists(JSON_FILENAME):
        print(f"Error: Scored leads database '{JSON_FILENAME}' not found!")
        print("Please run 'python scrape_leads_v2.py --score-only' first.")
        sys.exit(1)

    try:
        with open(JSON_FILENAME, "r", encoding="utf-8") as f:
            leads = json.load(f)
    except Exception as e:
        print(f"Error reading JSON leads database: {e}")
        sys.exit(1)

    if not leads:
        print("Error: The leads database is empty!")
        sys.exit(1)

    # Support bulk mode via command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ("--bulk", "-b"):
        print(f"Generating audits for all {len(leads)} leads in bulk...")
        count = 0
        for lead in leads:
            try:
                generate_report(lead)
                count += 1
            except Exception as e:
                print(f"Error generating audit for '{lead.get('Business Name', 'Unknown')}': {e}")
        index_file = generate_index_dashboard(leads)
        print(f"\n[SUCCESS] Generated {count} audit reports inside the '{OUTPUT_DIR}' directory!")
        print(f"[SUCCESS] Generated dashboard index file: {os.path.abspath(index_file)}")
        sys.exit(0)

    print(f"=== Welcome to the Lead Visibility Audit Generator ===")
    print(f"Successfully loaded {len(leads)} leads from '{JSON_FILENAME}'.")
    
    # Pre-generate dashboard on launch
    generate_index_dashboard(leads)

    # Let user search or choose
    while True:
        print("\nChoose an option:")
        print("1. Audit a lead from the TOP 20 high-converting list")
        print("2. Search leads by Business Name or City")
        print("3. Audit ALL current leads in bulk")
        print("4. Exit")
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == "1":
            print("\n--- TOP 20 PRIORITY LEADS ---")
            top_20 = leads[:20]
            for i, lead in enumerate(top_20):
                print(f"[{i+1}] {lead['Business Name']} ({lead['City']}) | Score: {lead['Priority Score']} | Reviews: {lead['Google Reviews']}")
            
            sel = input("\nSelect lead index to audit (1-20) or 'b' to go back: ").strip()
            if sel.lower() == 'b':
                continue
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(top_20):
                    filename = generate_report(top_20[idx])
                    generate_index_dashboard(leads)
                    print(f"\n[SUCCESS] Audit generated: {os.path.abspath(filename)}")
                else:
                    print("Invalid selection!")
            except ValueError:
                print("Please enter a valid number.")

        elif choice == "2":
            query = input("\nEnter search query (Business Name or City): ").strip().lower()
            if not query:
                print("Query cannot be empty.")
                continue
            
            matches = [l for l in leads if query in l['Business Name'].lower() or query in l['City'].lower()]
            
            if not matches:
                print("No matching businesses found.")
                continue
            
            print(f"\nFound {len(matches)} matches:")
            for i, lead in enumerate(matches):
                print(f"[{i+1}] {lead['Business Name']} ({lead['City']}) | Score: {lead['Priority Score']}")
                
            sel = input(f"\nSelect lead index to audit (1-{len(matches)}) or 'b' to go back: ").strip()
            if sel.lower() == 'b':
                continue
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(matches):
                    filename = generate_report(matches[idx])
                    generate_index_dashboard(leads)
                    print(f"\n[SUCCESS] Audit generated: {os.path.abspath(filename)}")
                else:
                    print("Invalid selection!")
            except ValueError:
                print("Please enter a valid number.")

        elif choice == "3":
            print(f"\nGenerating audits for all {len(leads)} leads in bulk...")
            count = 0
            for lead in leads:
                try:
                    generate_report(lead)
                    count += 1
                except Exception as e:
                    print(f"Error generating audit for '{lead.get('Business Name', 'Unknown')}': {e}")
            index_file = generate_index_dashboard(leads)
            print(f"\n[SUCCESS] Generated {count} audit reports inside the '{OUTPUT_DIR}' directory!")
            print(f"[SUCCESS] Generated dashboard index file: {os.path.abspath(index_file)}")

        elif choice == "4":
            print("\nExiting. Good luck with your pitches!")
            break
        else:
            print("Invalid option. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
