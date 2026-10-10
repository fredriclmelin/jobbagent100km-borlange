
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG_FILE = Path("job_config.json")
OUTPUT_FILE = Path("matches.json")

def read_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

def get_text(value):
    """Gör om API-fält till sökbar text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(get_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(get_text(v) for v in value)
    return ""

def fetch_ads(query, location, radius_km):
    params = {
        "q": query,
        "position": (
            f'{location["latitude"]},{location["longitude"]}'
        ),
        "position.radius": radius_km,
        "limit": 100
    }

    url = (
        "https://jobsearch.api.jobtechdev.se/search?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json",
                 "User-Agent": "Jobbagent-Borlange/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("hits", [])

def score_ad(ad, config):
    title = get_text(ad.get("headline", "")).lower()
    description = get_text(ad.get("description", "")).lower()
    employer = get_text(ad.get("employer", ""))
    text = f"{title} {description}"

    groups = {
        "job_content": [
            "underhållschef", "maintenance manager",
            "teknisk chef", "technical manager",
            "engineering manager", "automationschef",
            "produktionschef", "fabrikschef",
            "underhållsledare", "reliability manager",
            "asset reliability", "maintenance and engineering",
            "industrial improvement"
        ],
        "leadership": [
            "personalansvar", "personalansvarig",
            "ledningsgrupp", "chef", "team",
            "medarbetare", "budgetansvar", "manager"
        ],
        "maintenance_reliability": [
            "underhåll", "driftsäkerhet", "reliability",
            "asset management", "förebyggande underhåll",
            "avhjälpande underhåll", "maintenance"
        ],
        "automation_industrial_technology": [
            "automation", "plc", "ot", "industriell it",
            "elkraft", "el och instrument", "process control",
            "styrsystem"
        ],
        "improvement_economics_results": [
            "förbättringsarbete", "effektivisering",
            "kostnad", "resultat", "produktivitet",
            "lean", "continuous improvement"
        ]
    }

    weights = config["scoring_weights"]
    total = 0

    for group, keywords in groups.items():
        weight = weights.get(group, 0)
        hits = sum(1 for word in keywords if word in text)

        # Maxpoäng för varje kategori nås vid flera relevanta träffar.
        category_score = min(hits / 3, 1) * weight
        total += category_score

    # Extra vikt när titeln uttryckligen matchar en målroll.
    title_matches = sum(
        1 for role in config["job_titles"]
        if role.lower() in title
    )
    total += min(title_matches * 5, 10)

    return min(round(total), 100)

def main():
    config = read_config()
    location = config["location"]
    all_ads = {}

    for query in config["job_titles"]:
        try:
            ads = fetch_ads(
                query, location, location["radius_km"]
            )
            print(f"{query}: {len(ads)} annonser")
        except Exception as exc:
            print(f"Varning: sökningen '{query}' misslyckades: {exc}")
            continue

        for ad in ads:
            ad_id = str(ad.get("id", "")).strip()
            if not ad_id:
                continue

            if ad_id not in all_ads:
                all_ads[ad_id] = ad

    results = []

    for ad_id, ad in all_ads.items():
        score = score_ad(ad, config)

        if score < config["minimum_match_score"]:
            continue

        results.append({
            "id": ad_id,
            "title": get_text(ad.get("headline", "Okänd titel")),
            "employer": get_text(ad.get("employer", "Okänd arbetsgivare")),
            "location": get_text(ad.get("workplace_address", "")),
            "published": ad.get("publication_date", ""),
            "url": ad.get("webpage_url", ""),
            "score": score,
            "description": get_text(ad.get("description", ""))[:1200]
        })

    results.sort(key=lambda item: item["score"], reverse=True)

    OUTPUT_FILE.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\nKlart. Hittade {len(results)} annonser över gränsen.")
    print(f"Resultatet sparades i {OUTPUT_FILE}.")

    for item in results[:10]:
        print(f'{item["score"]:3} poäng | {item["title"]}')

if __name__ == "__main__":
    main()
