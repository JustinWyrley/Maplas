import pandas as pd
import requests
from bs4 import BeautifulSoup
import re


def scrape_alcohol_data():
    """Scrape alcohol consumption per capita from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_countries_by_alcohol_consumption_per_capita"
    headers = {"User-Agent": "StudentResearchBot/1.0 (jochem.van.der.geest.3@student.rug.nl)"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching Wikipedia page: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", class_="wikitable")
    if not tables:
        print("No wikitable found on page.")
        return pd.DataFrame()

    # The second table contains the main consumption data
    table = tables[1] if len(tables) > 1 else tables[-1]

    def clean_cell(cell):
        """Remove footnotes and normalize whitespace."""
        for sup in cell.find_all("sup"):
            sup.decompose()
        return cell.get_text(strip=True)

    data = []
    for row in table.find_all("tr")[1:]:  # Skip header row
        cols = row.find_all("td")
        if len(cols) >= 2:
            country = clean_cell(cols[0])
            consumption_text = clean_cell(cols[1])

            # Extract the numeric value from the consumption cell
            match = re.search(r"[-+]?\d*\.?\d+", consumption_text)
            consumption_value = float(match.group()) if match else 0.0

            if country:
                data.append([country, consumption_value])

    return pd.DataFrame(data, columns=["name", "alcohol_consumption"])


def clean_country_names(df):
    """Standardize country names to match the CSV."""
    replacements = {
        "Bahamas, The": "Bahamas",
        "The Bahamas": "Bahamas",
        "Congo, Democratic Republic of the": "Democratic Republic of the Congo",
        "DR Congo": "Democratic Republic of the Congo",
        "Congo, Republic of the": "Republic of the Congo",
        "Gambia, The": "Gambia",
        "The Gambia": "Gambia",
        "Micronesia, Federated States of": "Federated States of Micronesia",
        "Russian Federation": "Russia",
        "Korea, South": "South Korea",
        "Republic of Korea": "South Korea",
        "UK": "United Kingdom",
        "USA": "United States",
        "US": "United States",
        "Korea, North": "North Korea",
        "Sao Tome and Principe": "São Tomé and Príncipe",
    }
    df["name"] = df["name"].replace(replacements)
    return df


def add_ranking(df):
    """Add alcohol consumption ranking (1 = highest consumer)."""
    df = df.sort_values("alcohol_consumption", ascending=False).reset_index(drop=True)
    df["alcohol_consumption_ranked"] = range(1, len(df) + 1)
    return df


def merge_into_csv(df_scraped, csv_path="collecting_info/country_info_updated.csv"):
    """Merge scraped alcohol data into an existing CSV on the 'name' column.
    If the CSV is not found, save the scraped data on its own instead."""
    try:
        df_csv = pd.read_csv(csv_path)
        if "name" not in df_csv.columns:
            print("CSV does not have a 'name' column. Exiting merge.")
            return

        # Check if columns already exist to avoid overwriting or duplicating data
        existing = [col for col in ["alcohol_consumption", "alcohol_consumption_ranked"] if col in df_csv.columns]
        if existing:
            print(f"Columns {existing} already exist in CSV. Skipping merge to avoid overwriting.")
            return

        df_merged = df_csv.merge(df_scraped[["name", "alcohol_consumption", "alcohol_consumption_ranked"]],
                                 on="name", how="left")

        matched = df_merged["alcohol_consumption"].notna().sum()
        print(f"Matched {matched} out of {len(df_merged)} countries.")

        df_merged.to_csv(csv_path, index=False)
        print(f"Updated {csv_path} with alcohol consumption data.")

    except FileNotFoundError:
        print(f"{csv_path} not found. Saving scraped data to alcohol_data.csv instead.")
        df_scraped.to_csv("alcohol_data.csv", index=False)


if __name__ == "__main__":
    print("Scraping Wikipedia for alcohol consumption data...")
    df = scrape_alcohol_data()
    if df.empty:
        print("No data scraped. Exiting.")
    else:
        df = clean_country_names(df)
        df = add_ranking(df)
        print(f"Scraped and ranked {len(df)} countries.")
        merge_into_csv(df)