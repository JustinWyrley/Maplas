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

    # This clean function was implemented for the 5th column since otherwise the output would be stuck together
    def clean(cell):
        """Strip footnotes, replace <br> with semicolons, and normalize whitespace."""
        for sup in cell.find_all("sup"):
            sup.decompose()
        for br in cell.find_all("br"):
            br.replace_with("; ")
        text = cell.get_text().replace("\xa0", " ")
        parts = [re.sub(r"\s+", " ", n).strip() for n in text.split(";") if n.strip()]
        return "; ".join(parts)

    rows = table.find_all("tr")
    cols_idx = (0, 1, 4, 5)  # Country name, total border km, no. of borders, neighbours

    data = []
    for r in rows[1:]:  # Skip header row
        cols = r.find_all("td")
        if len(cols) >= max(cols_idx) + 1:
            data.append([clean(cols[i]) for i in cols_idx])

    df = pd.DataFrame(data, columns=["name", "Total_borders_km", "Num_borders", "Neighbors"])

    # Some countries appear twice on Wikipedia: once as a constituent country (e.g. just
    # "Netherlands") and once as the full Kingdom including overseas territories. We want
    # the richer entry with more territories, so we drop the simpler duplicates by their
    # exact scraped name (including the "→includes:" suffix added by the clean function).
    entries_to_drop = [
        "Netherlands (constituent country)",
        "Denmark (constituent country)",
        "France, Metropolitan",
        "United Kingdom →includes: → England; → Northern Ireland; → Scotland; → Wales",
    ]
    df = df[~df["name"].isin(entries_to_drop)].copy()

    # Rename the long official Kingdom names to their common names.
    # The full →includes: string is part of the scraped name, so we match exactly.
    long_to_simple = {
        "Netherlands, Kingdom of →includes: → Aruba; → Curaçao; → Netherlands (constituent country) (including Caribbean Netherlands); → Sint Maarten": "Netherlands",
        "Denmark, Kingdom of →includes: → Denmark (constituent country); → Faroe Islands; → Greenland": "Denmark",
        "France (including French overseas departments, collectivities, and territories) →includes: → Clipperton Island; → French Guiana; → French Polynesia; → French Southern and Antarctic Lands; → Guadeloupe; → Martinique; → Mayotte; → Metropolitan France; → New Caledonia; → Réunion; → Saint Barthélemy; → Saint Martin; → Saint Pierre and Miquelon; → Wallis and Futuna": "France",
        "United Kingdom (plus British Overseas Territories and Crown Dependencies) →includes: → Akrotiri and Dhekelia; → Anguilla; → Bermuda; → British Indian Ocean Territory; → British Virgin Islands; → Cayman Islands; → England; → Falkland Islands; → Gibraltar; → Guernsey; → Isle of Man; → Jersey; → Montserrat; → Northern Ireland; → Pitcairn Islands; → Saint Helena, Ascension and Tristan da Cunha; → Scotland; → South Georgia and the South Sandwich Islands; → Turks and Caicos Islands; → Wales": "United Kingdom",
    }
    df["name"] = df["name"].replace(long_to_simple)

    return df


def merge_into_csv(df_scraped, csv_path="country_info_updated.csv"):
    """Merge scraped border data into an existing CSV on the 'name' column.
    If the CSV is not found, save the scraped data on its own instead."""
    try:
        df_csv = pd.read_csv(csv_path)
        if "name" not in df_csv.columns:
            print("CSV does not have a 'name' column. Exiting merge.")
            return

        # Check if columns already exist to avoid overwriting or duplicating data
        existing = [col for col in ["Total_borders_km", "Num_borders", "Neighbors"] if col in df_csv.columns]
        if existing:
            print(f"Columns {existing} already exist in CSV. Skipping merge to avoid overwriting.")
            return

        # Left join so all existing CSV rows are kept; scraped columns are added where names match
        df_merged = df_csv.merge(df_scraped, on="name", how="left")
        df_merged.to_csv(csv_path, index=False)
        print(f"Merged land borders data into {csv_path} ({len(df_merged)} rows).")

    except FileNotFoundError:
        print(f"{csv_path} not found. Saving scraped data to land_borders.csv instead.")
        df_scraped.to_csv("land_borders.csv", index=False)


if __name__ == "__main__":
    df = scrape_land_borders()
    if df.empty:
        print("No data scraped. Exiting.")
    else:
        print(f"Scraped {len(df)} countries/territories.")
        merge_into_csv(df)