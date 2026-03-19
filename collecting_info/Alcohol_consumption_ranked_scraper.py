import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

def scrape_alcohol_data():
    """Scrape alcohol consumption per capita from Wikipedia"""
    url = "https://en.wikipedia.org/wiki/List_of_countries_by_alcohol_consumption_per_capita"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching Wikipedia page: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all wikitable tables
    tables = soup.find_all("table", class_="wikitable")
    if not tables:
        print("No wikitable found on page.")
        return pd.DataFrame()

    # Use the second table if possible, fallback to last
    table = tables[1] if len(tables) > 1 else tables[-1]

    # Function to clean cell text
    def clean_cell(cell):
        for sup in cell.find_all("sup"):
            sup.decompose()
        for ref in cell.find_all("span", class_="reference"):
            ref.decompose()
        text = cell.get_text(strip=True)
        text = re.sub(r'\[\d+\]', '', text)  # remove footnote numbers
        return text.strip()

    # Extract country and alcohol consumption
    data = []
    for row in table.find_all("tr")[1:]:  # skip header
        cols = row.find_all("td")
        if len(cols) >= 2:
            country = clean_cell(cols[0])
            consumption = clean_cell(cols[1])

            # Extract numeric value
            match = re.search(r'[-+]?\d*\.?\d+', consumption)
            consumption_value = float(match.group()) if match else 0.0

            if country:
                data.append([country, consumption_value])

    df = pd.DataFrame(data, columns=['country', 'alcohol_consumption'])
    return df

def clean_country_names(df):
    """Standardize country names to match the CSV"""
    replacements = {
        'Bahamas, The': 'Bahamas',
        'The Bahamas': 'Bahamas',
        'Congo, Democratic Republic of the': 'Democratic Republic of the Congo',
        'DR Congo': 'Democratic Republic of the Congo',
        'Congo, Republic of the': 'Republic of the Congo',
        'Gambia, The': 'Gambia',
        'The Gambia': 'Gambia',
        'North Macedonia': 'North Macedonia',
        'Micronesia, Federated States of': 'Federated States of Micronesia',
        'Russia': 'Russia',
        'Russian Federation': 'Russia',
        'South Korea': 'South Korea',
        'Korea, South': 'South Korea',
        'Republic of Korea': 'South Korea',
        'UK': 'United Kingdom',
        'USA': 'United States',
        'US': 'United States',
        "Côte d'Ivoire": "Côte d'Ivoire",
        'North Korea': 'North Korea',
        'Korea, North': 'North Korea',
        'São Tomé and Príncipe': 'São Tomé and Príncipe',
        'Sao Tome and Principe': 'São Tomé and Príncipe',
    }
    df['country'] = df['country'].replace(replacements)
    return df

def main():
    # Step 1: Scrape alcohol data
    print("Scraping Wikipedia for alcohol consumption data...")
    df_wiki = scrape_alcohol_data()
    if df_wiki.empty:
        print("No data scraped from Wikipedia.")
        return

    df_wiki = clean_country_names(df_wiki)
    print(f"Scraped {len(df_wiki)} countries from Wikipedia.\n")

    # Step 2: Load CSV
    try:
        df_csv = pd.read_csv('country_info_updated.csv')
        if 'country' not in df_csv.columns:
            print("CSV does not have a 'country' column.")
            return
        print(f"Loaded CSV with {len(df_csv)} rows.\n")
    except FileNotFoundError:
        print("File country_info_updated.csv not found.")
        return

    # Step 3: Merge on 'country'
    df_merged = df_csv.merge(df_wiki, on='country', how='left')

    # Step 4: Show summary
    matched = df_merged['alcohol_consumption'].notna().sum()
    print(f"Successfully matched {matched} out of {len(df_merged)} countries.\n")

    # Step 5: Save merged CSV
    df_merged.to_csv('country_info_updated.csv', index=False)
    print("Updated country_info_updated.csv with alcohol_consumption column.")

if __name__ == "__main__":
    main()