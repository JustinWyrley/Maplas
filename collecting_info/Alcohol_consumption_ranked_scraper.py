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

def create_ranking(df):
    """Add alcohol consumption ranking (1 = highest)"""
    df = df.sort_values('alcohol_consumption', ascending=False).reset_index(drop=True)
    df['alcohol_consumption_ranked'] = range(1, len(df) + 1)
    return df

def main():
    print("Scraping Wikipedia for alcohol consumption data...")
    alc_consumption = scrape_alcohol_data()
    if alc_consumption.empty:
        print("No data scraped. Exiting.")
        return

    alc_consumption = clean_country_names(alc_consumption)
    alc_consumption = create_ranking(alc_consumption)

    # Rename 'country' column to match your CSV 'name'
    alc_consumption.rename(columns={'country': 'name'}, inplace=True)

    print(f"Scraped and ranked {len(alc_consumption)} countries.")

    # Load CSV
    try:
        countries = pd.read_csv('collecting_info/country_info_updated.csv')
        if 'name' not in countries.columns:
            print("CSV does not have a 'name' column. Exiting.")
            return
    except FileNotFoundError:
        print("File country_info_updated.csv not found. Exiting.")
        return

    # Merge scraped data into CSV
    df_merged = countries.merge(alc_consumption[['name', 'alcohol_consumption', 'alcohol_consumption_ranked']],
                             on='name', how='left')

    matched = df_merged['alcohol_consumption'].notna().sum()
    print(f"Successfully matched {matched} out of {len(df_merged)} countries.")

    # Save updated CSV
    df_merged.to_csv('collecting_info/country_info_updated.csv', index=False)
    print("Updated country_info_updated.csv with alcohol_consumption and ranking.")

if __name__ == "__main__":
    main()