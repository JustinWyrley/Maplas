import pandas as pd
import requests
from bs4 import BeautifulSoup


def scrape_flag_colours():
    """Scrape flag colours per country from flagpictures.com."""
    url = "https://flagpictures.com/countries/flag-colors/"

    try:
        # verify=False because the site has SSL certificate issues
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.content, "html.parser")
    rows = soup.find_all("tr")

    # Some scraped names differ from the names used in our CSV, so we map them manually
    name_mapping = {
        "Czechia": "Czech Republic",
        "Côte D'Ivoire": "Ivory Coast",
        "Democratic Republic Of The Congo": "Democratic Republic of the Congo",
        "Georgia": "Georgia (country)",
        "Republic Of The Congo": "Republic of the Congo",
        "Russian Federation": "Russia",
        "Syrian Arab Republic": "Syria",
        "Tanzania, United Republic Of": "Tanzania",
    }

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            country = cols[0].get_text(strip=True)
            colours = cols[1].get_text(separator=", ", strip=True)
            country = name_mapping.get(country, country)  # Apply mapping if exists
            data.append([country, colours])

    return pd.DataFrame(data, columns=["name", "flag_colours"])


def merge_into_csv(df_scraped, csv_path="country_info_updated.csv"):
    """Merge scraped flag colour data into an existing CSV on the 'name' column.
    If the CSV is not found, save the scraped data on its own instead."""
    try:
        df_csv = pd.read_csv(csv_path)
        if "name" not in df_csv.columns:
            print("CSV does not have a 'name' column. Exiting merge.")
            return

        # Check if column already exists to avoid overwriting or duplicating data
        if "flag_colours" in df_csv.columns:
            print("Column 'flag_colours' already exists in CSV. Skipping merge to avoid overwriting.")
            return

        df_merged = df_csv.merge(df_scraped, on="name", how="left")
        matched = df_merged["flag_colours"].notna().sum()
        print(f"Matched {matched} out of {len(df_merged)} countries.")

        df_merged.to_csv(csv_path, index=False)
        print(f"Updated {csv_path} with flag colour data.")

    except FileNotFoundError:
        print(f"{csv_path} not found. Saving scraped data to flag_colours.csv instead.")
        df_scraped.to_csv("flag_colours.csv", index=False)


if __name__ == "__main__":
    print("Scraping flag colours...")
    df = scrape_flag_colours()
    if df.empty:
        print("No data scraped. Exiting.")
    else:
        print(f"Scraped {len(df)} countries.")
        merge_into_csv(df)