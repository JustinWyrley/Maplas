import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

def scrape_land_borders():
    """Scrape countries and their land borders from Wikipedia"""
    url = "https://en.wikipedia.org/wiki/List_of_countries_and_territories_by_number_of_land_borders"
    headers = {
        "User-Agent": "StudentResearchBot/1.0 (jochem.van.der.geest.3@student.rug.nl)"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching Wikipedia page: {e}")
        return pd.DataFrame()
    
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="wikitable")
    if not table:
        print("No wikitable found on page.")
        return pd.DataFrame()
    
    # Function to clean a cell
    def clean(cell):
        for sup in cell.find_all("sup"):
            sup.decompose()
        for br in cell.find_all("br"):
            br.replace_with("; ")
        text = cell.get_text()
        text = text.replace("\xa0", " ")
        neighbors_raw = [n.strip() for n in text.split(";") if n.strip()]
        neighbors_clean = [re.sub(r"\s+", " ", n).strip() for n in neighbors_raw]
        return "; ".join(neighbors_clean)
    
    # Extract rows
    rows = table.find_all("tr")
    cols_idx = (0, 1, 4, 5)  # columns we want
    header_cells = rows[0].find_all(["th", "td"])
    header = [clean(header_cells[i]) if i < len(header_cells) else "" for i in cols_idx]
    
    data = []
    for r in rows[1:]:
        cols = r.find_all("td")
        if len(cols) >= max(cols_idx)+1:
            data.append([clean(cols[i]) for i in cols_idx])
    
    df = pd.DataFrame(data, columns=header)
    return df

def clean_country_names(df, column="Country"):
    """Standardize country names to match CSV 'name' column"""
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
    df[column] = df[column].replace(replacements)
    return df

def main():
    print("Scraping Wikipedia for number of land borders...")
    df_borders = scrape_land_borders()
    if df_borders.empty:
        print("No data scraped. Exiting.")
        return
    
    df_borders = clean_country_names(df_borders, column="Country")
    print(f"Scraped {len(df_borders)} countries with land borders.")
    
    # Optionally merge with CSV
    try:
        df_csv = pd.read_csv('country_info_updated.csv')
        if 'name' not in df_csv.columns:
            print("CSV does not have a 'name' column. Exiting merge.")
        else:
            df_merged = df_csv.merge(df_borders, left_on='name', right_on='Country', how='left')
            df_merged.to_csv('country_info_updated.csv', index=False)
            print(f"Merged land borders data into country_info_updated.csv ({len(df_merged)} rows).")
    except FileNotFoundError:
        print("country_info_updated.csv not found. You can save the borders DataFrame separately if needed.")
        df_borders.to_csv('land_borders.csv', index=False)
        print("Saved scraped data to land_borders.csv for review.")

if __name__ == "__main__":
    main()