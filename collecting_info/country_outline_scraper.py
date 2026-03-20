import json
import requests
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from tqdm import tqdm
from pathlib import Path
from shapely.geometry import MultiPolygon


# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).parent

DATA_URL = "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_countries.geojson"

OUTPUT_PNG = BASE_DIR / "collecting_info/countries"
CSV_PATH   = BASE_DIR / "collecting_info/country_info_updated.csv"

# The Natural Earth dataset uses different names for some countries.
# This mapping translates our CSV names to the dataset names so we can match them.
NAME_MAPPING = {
    "Antigua and Barbuda":              "Antigua and Barb.",
    "Bosnia and Herzegovina":           "Bosnia and Herz.",
    "Cabo Verde":                       "Cape Verde",
    "Central African Republic":         "Central African Rep.",
    "Democratic Republic of the Congo": "Dem. Rep. Congo",
    "Republic of the Congo":            "Congo",
    "Ivory Coast":                      "Côte d'Ivoire",
    "Czech Republic":                   "Czech Rep.",
    "Dominican Republic":               "Dominican Rep.",
    "Equatorial Guinea":                "Eq. Guinea",
    "Eswatini":                         "Swaziland",
    "Laos":                             "Lao PDR",
    "Marshall Islands":                 "Marshall Is.",
    "North Korea":                      "Dem. Rep. Korea",
    "North Macedonia":                  "Macedonia",
    "Saint Kitts and Nevis":            "St. Kitts and Nevis",
    "Saint Vincent and the Grenadines": "St. Vin. and Gren.",
    "São Tomé and Príncipe":            "São Tomé and Principe",
    "Solomon Islands":                  "Solomon Is.",
    "South Korea":                      "Korea",
    "South Sudan":                      "S. Sudan",
    "Timor-Leste":                      "East Timor",
    "United Arab Emirates":             "United Arab Emirates",
    "United Kingdom":                   "United Kingdom",
    "United States":                    "United States",
    "Vatican City":                     "Vatican",
}

# Reverse mapping to translate dataset names back to our CSV names
REVERSE_MAPPING = {v: k for k, v in NAME_MAPPING.items()}

# These countries have remote overseas territories in the dataset — we only
# want to render their main landmass, not their entire global footprint.
REMOTE_TERRITORY_COUNTRIES = {
    "Netherlands", "France", "United Kingdom", "United States",
    "Denmark", "Spain", "Portugal", "Norway", "Australia", "New Zealand"
}


# =========================
# GEOMETRY FILTERING
# =========================

def filter_european_netherlands(geometry):
    """Return only the European part of the Netherlands geometry.
    The Natural Earth dataset includes Caribbean territories, so we filter
    by bounding box to keep only the mainland."""
    if geometry.geom_type == "MultiPolygon":
        european_polygons = [
            p for p in geometry.geoms
            if 3 <= p.centroid.x <= 7 and 50.5 <= p.centroid.y <= 53.5
        ]
        if european_polygons:
            return MultiPolygon(european_polygons) if len(european_polygons) > 1 else european_polygons[0]
    return geometry


def filter_main_landmass(geometry, country_name):
    """Filter out remote territories and small islands, keeping only the main landmass.
    For countries with overseas territories we keep only the largest polygon.
    For others we keep all polygons that are at least 5% of the largest polygon's area."""
    if geometry.geom_type != "MultiPolygon":
        return geometry

    if country_name == "Netherlands":
        return filter_european_netherlands(geometry)

    polygons = sorted(geometry.geoms, key=lambda g: g.area, reverse=True)

    if country_name in REMOTE_TERRITORY_COUNTRIES:
        return polygons[0]

    main_area = polygons[0].area
    main_polygons = [p for p in polygons if p.area > 0.05 * main_area]
    return MultiPolygon(main_polygons) if len(main_polygons) > 1 else main_polygons[0]


# =========================
# PROCESSING
# =========================

def process_country(feature, target_countries):
    """Match a GeoJSON feature to a country in our list, save its outline as
    a PNG and return the country name and PNG path."""
    dataset_name = feature["properties"]["name"]

    # Try direct match first, then fall back to reverse mapping
    if dataset_name in target_countries:
        matched_name = dataset_name
    elif dataset_name in REVERSE_MAPPING and REVERSE_MAPPING[dataset_name] in target_countries:
        matched_name = REVERSE_MAPPING[dataset_name]
        print(f"  Matched via mapping: {dataset_name} -> {matched_name}")
    else:
        return None, None

    # Build a filesystem-safe filename from the country name
    safe_name = (matched_name
                 .replace(" ", "_")
                 .replace(",", "")
                 .replace("(", "")
                 .replace(")", "")
                 .replace("-", "_"))

    # Filter to main landmass and render as PNG
    gdf = gpd.GeoDataFrame.from_features([feature])
    filtered_geometry = filter_main_landmass(gdf.geometry.iloc[0], matched_name)
    gdf = gpd.GeoDataFrame(geometry=[filtered_geometry])

    fig, ax = plt.subplots(figsize=(4, 4))
    gdf.plot(ax=ax, edgecolor="black", facecolor="none", linewidth=1)

    minx, miny, maxx, maxy = gdf.total_bounds
    padding_x = (maxx - minx) * 0.1
    padding_y = (maxy - miny) * 0.1
    ax.set_xlim(minx - padding_x, maxx + padding_x)
    ax.set_ylim(miny - padding_y, maxy + padding_y)
    ax.set_axis_off()

    png_path = OUTPUT_PNG / f"{safe_name}.png"
    plt.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close()

    return matched_name, png_path.relative_to(BASE_DIR)


def download_and_process(target_countries):
    """Download the Natural Earth GeoJSON and process each feature."""
    print("Downloading Natural Earth dataset...")
    response = requests.get(DATA_URL, timeout=30)
    response.raise_for_status()
    features = response.json()["features"]

    processed = []
    for feature in tqdm(features):
        name, png_path = process_country(feature, target_countries)
        if name:
            processed.append((name, png_path))

    return processed


# =========================
# MAIN
# =========================

def main():
    OUTPUT_PNG.mkdir(parents=True, exist_ok=True)

    # Load target countries from CSV instead of a hardcoded list
    if not CSV_PATH.exists():
        print(f"{CSV_PATH} not found. Exiting.")
        return

    df_csv = pd.read_csv(CSV_PATH)
    if "name" not in df_csv.columns:
        print("CSV does not have a 'name' column. Exiting.")
        return

    target_countries = set(df_csv["name"].dropna().unique())
    print(f"Loaded {len(target_countries)} countries from CSV.")

    # Check if column already exists to avoid overwriting or duplicating data
    if "Country_outline" in df_csv.columns:
        print("Column 'Country_outline' already exists in CSV. Skipping to avoid overwriting.")
        return

    processed = download_and_process(target_countries)
    print(f"\nProcessed {len(processed)} countries.")

    # Map results back into the CSV and save
    outline_dict = dict(processed)
    df_csv["Country_outline"] = df_csv["name"].map(outline_dict).astype(str)
    df_csv.to_csv(CSV_PATH, index=False)
    print(f"Updated {CSV_PATH} with Country_outline column.")


if __name__ == "__main__":
    main()