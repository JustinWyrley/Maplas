import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

def scrape_land_borders():
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

    rows = table.find_all("tr")
    cols_idx = (0, 1, 4, 5)
    header_cells = rows[0].find_all(["th", "td"])
    header = [clean(header_cells[i]) if i < len(header_cells) else "" for i in cols_idx]

    data = []
    for r in rows[1:]:
        cols = r.find_all("td")
        if len(cols) >= max(cols_idx)+1:
            data.append([clean(cols[i]) for i in cols_idx])

    df = pd.DataFrame(data, columns=header)

    # Renaming the wikipedia columns for simplicity
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        df.columns[0]: "name",
        df.columns[1]: "Total_borders_km",
        df.columns[2]: "Num_borders",
        df.columns[3]: "Neighbors"
    })

    # Filter and clean country names for main entities only
    def standardize_main_countries(name):
        # Remove constituent country mentions in parentheses
        name = re.sub(r"\s*\(constituent country\).*", "", name)
        name = re.sub(r"\s*\(including.*\)", "", name)
        # Replace longer descriptions with main country names
        replacements = {
            'Netherlands, Kingdom of': 'Netherlands',
            'Denmark, Kingdom of': 'Denmark',
            'France, Metropolitan': 'France',
            'United Kingdom[ar]': 'United Kingdom',
        }
        return replacements.get(name, name)

    df["name"] = df["name"].apply(standardize_main_countries)

    return df

def clean_country_names(df, column="name"):
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

def safe_merge_columns(df_main, df_new, on="name"):
    """Merge new columns only if they do not already exist"""
    for col in df_new.columns:
        if col != on and col not in df_main.columns:
            df_main = df_main.merge(df_new[[on, col]], on=on, how='left')
    return df_main

def main():
    print("Scraping Wikipedia for number of land borders...")
    df_borders = scrape_land_borders()
    if df_borders.empty:
        print("No data scraped. Exiting.")
        return

    df_borders = clean_country_names(df_borders, column="name")
    print(f"Scraped {len(df_borders)} countries with land borders.")

    # Optionally merge with CSV
    try:
        df_csv = pd.read_csv('country_info_updated.csv')
        if 'name' not in df_csv.columns:
            print("CSV does not have a 'name' column. Exiting merge.")
        else:
            df_csv = safe_merge_columns(df_csv, df_borders, on='name')
            df_csv.to_csv('country_info_updated.csv', index=False)
            print(f"Merged land borders data into country_info_updated.csv ({len(df_csv)} rows).")
    except FileNotFoundError:
        print("country_info_updated.csv not found. Saving scraped data separately.")
        df_borders.to_csv('land_borders.csv', index=False)
        print("Saved scraped data to land_borders.csv for review.")

if __name__ == "__main__":
    main()