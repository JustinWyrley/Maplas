import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL for flag colors
url = "https://flagpictures.com/countries/flag-colors/"

response = requests.get(url, verify=False)
soup = BeautifulSoup(response.content, "html.parser")

# Extract table rows
rows = soup.find_all("tr")

# Mapping scraped names to dataset names
name_mapping = {
    "Czechia": "Czech Republic",
    "Côte D’Ivoire": "Ivory Coast",
    "Democratic Republic Of The Congo": "Democratic Republic of the Congo",
    "Georgia": "Georgia (country)",
    "Republic Of The Congo": "Republic of the Congo",
    "Russian Federation": "Russia",
    "Syrian Arab Republic": "Syria",
    "Tanzania, United Republic Of": "Tanzania"
}

# Scrape flag colors
scraped_data = []

for row in rows:
    cols = row.find_all("td")
    if len(cols) >= 2:
        country = cols[0].get_text(strip=True)
        colors = cols[1].get_text(separator=", ", strip=True)
        
        # Normalize country name
        if country in name_mapping:
            country = name_mapping[country]
        
        scraped_data.append((country, colors))

# Convert to DataFrame
df_flags_colours = pd.DataFrame(scraped_data, columns=["name", "flag_colours"])

# Optionally merge with CSV
try:
    df_csv = pd.read_csv('country_info_updated.csv')
    if 'name' not in df_csv.columns:
        print("CSV does not have a 'name' column. Exiting merge.")
    else:
        df_merged = df_csv.merge(df_flags_colours, on='name', how='left')
        df_merged.to_csv('country_info_updated.csv', index=False)
        print(f"Merged flag colors into country_info_updated.csv ({len(df_merged)} rows).")
