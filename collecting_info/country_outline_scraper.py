import os
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
from tqdm import tqdm
import json
from shapely.geometry import MultiPolygon
from pathlib import Path
import pandas as pd

# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).parent
DATA_URL = "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_countries.geojson"

OUTPUT_GEOJSON = BASE_DIR / "countries/countries_geojson"
OUTPUT_PNG = BASE_DIR / "countries/countries_png"

CSV_PATH = BASE_DIR / "country_info_updated.csv"  # CSV to update

# change to using csv to get countries
TARGET_COUNTRIES = set([
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", 
    "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", 
    "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", 
    "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", 
    "Chile", "China", "Colombia", "Comoros", "Congo Democratic Republic of the", "Congo Republic of the", "Costa Rica", 
    "Cote d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czechia", "Denmark", "Djibouti", "Dominica", "Dominican Republic", 
    "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", 
    "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", 
    "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", 
    "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Kosovo", 
    "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", 
    "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", 
    "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", 
    "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", 
    "North Korea", "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", 
    "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", 
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", 
    "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", 
    "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", 
    "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", 
    "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", 
    "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates (UAE)", "United Kingdom (UK)", 
    "United States of America (USA)", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City (Holy See)", 
    "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
])

# Name mapping between your list and Natural Earth dataset
NAME_MAPPING = {
    "Antigua and Barbuda": "Antigua and Barb.",
    "Bosnia and Herzegovina": "Bosnia and Herz.",
    "Cabo Verde": "Cape Verde",
    "Central African Republic": "Central African Rep.",
    "Congo Democratic Republic of the": "Dem. Rep. Congo",
    "Congo Republic of the": "Congo",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Czechia": "Czech Rep.",
    "Dominican Republic": "Dominican Rep.",
    "Equatorial Guinea": "Eq. Guinea",
    "Eswatini": "Swaziland",
    "Laos": "Lao PDR",
    "Marshall Islands": "Marshall Is.",
    "North Korea": "Dem. Rep. Korea",
    "North Macedonia": "Macedonia",
    "Saint Kitts and Nevis": "St. Kitts and Nevis",
    "Saint Vincent and the Grenadines": "St. Vin. and Gren.",
    "Sao Tome and Principe": "São Tomé and Principe",
    "Solomon Islands": "Solomon Is.",
    "South Korea": "Korea",
    "South Sudan": "S. Sudan",
    "Timor-Leste": "East Timor",
    "United Arab Emirates (UAE)": "United Arab Emirates",
    "United Kingdom (UK)": "United Kingdom",
    "United States of America (USA)": "United States",
    "Vatican City (Holy See)": "Vatican",
}

REVERSE_MAPPING = {v: k for k, v in NAME_MAPPING.items()}

REMOTE_TERRITORY_COUNTRIES = {
    "Netherlands", "France", "United Kingdom", "United States", 
    "Denmark", "Spain", "Portugal", "Norway", "Australia", "New Zealand"
}

# =========================
# FUNCTIONS
# =========================

def filter_european_netherlands(geometry):
    if geometry.geom_type == "MultiPolygon":
        european_polygons = []
        for polygon in geometry.geoms:
            centroid = polygon.centroid
            if 3 <= centroid.x <= 7 and 50.5 <= centroid.y <= 53.5:
                european_polygons.append(polygon)
        if european_polygons:
            return MultiPolygon(european_polygons) if len(european_polygons) > 1 else european_polygons[0]
    return geometry

def filter_main_landmass(geometry, country_name):
    if geometry.geom_type == "MultiPolygon":
        if country_name == "Netherlands":
            return filter_european_netherlands(geometry)
        polygons = sorted(geometry.geoms, key=lambda g: g.area, reverse=True)
        if country_name in REMOTE_TERRITORY_COUNTRIES:
            return polygons[0]
        else:
            main_area = polygons[0].area
            main_polygons = [p for p in polygons if p.area > 0.05 * main_area]
            return MultiPolygon(main_polygons) if len(main_polygons) > 1 else main_polygons[0]
    return geometry

def process_country(feature):
    dataset_name = feature["properties"]["name"]
    matched_name = None
    if dataset_name in TARGET_COUNTRIES:
        matched_name = dataset_name
    elif dataset_name in REVERSE_MAPPING:
        matched_name = REVERSE_MAPPING[dataset_name]
        print(f"  Matched: {dataset_name} -> {matched_name}")
    if not matched_name:
        return None, None
    
    safe_name = matched_name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("-", "_")
    # Save GeoJSON
    geojson_path = OUTPUT_GEOJSON / f"{safe_name}.geojson"
    with open(geojson_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": [feature]}, f)
    
    # Convert to PNG
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
    
    return matched_name, png_path.relative_to(BASE_DIR)  # Return relative path for CSV

def download_and_process_data():
    print("Downloading dataset...")
    response = requests.get(DATA_URL)
    geojson_data = response.json()
    features = geojson_data["features"]
    processed_info = []
    for feature in tqdm(features):
        name, png_path = process_country(feature)
        if name:
            processed_info.append((name, png_path))
    return processed_info

def main():
    OUTPUT_GEOJSON.mkdir(exist_ok=True)
    OUTPUT_PNG.mkdir(exist_ok=True)
    
    processed_info = download_and_process_data()
    
    # Update CSV
    if CSV_PATH.exists():
        df_csv = pd.read_csv(CSV_PATH)
        # Add Country_outline column
        outline_dict = dict(processed_info)
        df_csv["Country_outline"] = df_csv["name"].map(outline_dict).astype(str)
        df_csv.to_csv(CSV_PATH, index=False)
        print(f"Updated {CSV_PATH} with Country_outline column.")
    else:
        print(f"{CSV_PATH} not found. Skipping CSV update.")

if __name__ == "__main__":
    main()