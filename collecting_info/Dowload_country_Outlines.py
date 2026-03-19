import os
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
from tqdm import tqdm
import json
from shapely.geometry import MultiPolygon
from pathlib import Path

# =========================================
# Country Outlines Downloader
#
# Downloads GeoJSON and PNG outlines for
# countries from Natural Earth data.
#
# Usage:
# Run `python download_countries.py`
#
# Outputs:
# - ./countries_geojson/ → GeoJSON files per country
# - ./countries_png/     → PNG images (4x4, transparent, 300 DPI)
#
# Notes:
# - Tuvalu is not in the Natural Earth 50m dataset
#   and needs to be added manually
# - Special handling for Netherlands
#   (removes Caribbean territories)
# =========================================


# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).parent
DATA_URL = "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_countries.geojson"

# Save outputs to the 'countries' folder
COUNTRIES_DIR = BASE_DIR / "countries"
OUTPUT_GEOJSON = COUNTRIES_DIR / "geojson"
OUTPUT_PNG = COUNTRIES_DIR / "png"

# Your original country list
TARGET_COUNTRIES = set([
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo Democratic Republic of the", "Congo Republic of the", "Costa Rica", "Cote d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czechia", "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates (UAE)", "United Kingdom (UK)", "United States of America (USA)", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City (Holy See)", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
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

# Reverse mapping for lookup
REVERSE_MAPPING = {v: k for k, v in NAME_MAPPING.items()}

# Countries with remote territories that need special handling
REMOTE_TERRITORY_COUNTRIES = {
    "Netherlands", "France", "United Kingdom", "United States", 
    "Denmark", "Spain", "Portugal", "Norway", "Australia", "New Zealand"
}

# =========================
# FILTERING FUNCTIONS
# =========================

def filter_european_netherlands(geometry):
    """Filter for Netherlands to keep only European mainland"""
    if geometry.geom_type == "MultiPolygon":
        european_polygons = []
        for polygon in geometry.geoms:
            centroid = polygon.centroid
            if 3 <= centroid.x <= 7 and 50.5 <= centroid.y <= 53.5:
                european_polygons.append(polygon)
        
        if european_polygons:
            if len(european_polygons) > 1:
                return MultiPolygon(european_polygons)
            else:
                return european_polygons[0]
    return geometry

def filter_main_landmass(geometry, country_name):
    """Filter to keep only the main landmass for countries with remote territories"""
    if geometry.geom_type == "MultiPolygon":
        if country_name == "Netherlands":
            return filter_european_netherlands(geometry)
        
        polygons = sorted(geometry.geoms, key=lambda g: g.area, reverse=True)
        
        if country_name in REMOTE_TERRITORY_COUNTRIES:
            return polygons[0]
        else:
            main_area = polygons[0].area
            main_polygons = [p for p in polygons if p.area > 0.05 * main_area]
            if len(main_polygons) > 1:
                return MultiPolygon(main_polygons)
            else:
                return main_polygons[0]
    return geometry

def process_country(feature):
    """Process a single country feature and save files"""
    dataset_name = feature["properties"]["name"]
    
    # Check if this dataset name matches any of our target countries
    matched_name = None
    
    # Direct match
    if dataset_name in TARGET_COUNTRIES:
        matched_name = dataset_name
    # Check reverse mapping
    elif dataset_name in REVERSE_MAPPING:
        matched_name = REVERSE_MAPPING[dataset_name]
        print(f"  Matched: {dataset_name} -> {matched_name}")
    
    if not matched_name:
        return None
    
    safe_name = matched_name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("-", "_")

    # Save GeoJSON
    geojson_path = OUTPUT_GEOJSON / f"{safe_name}.geojson"
    with open(geojson_path, "w") as f:
        json.dump({
            "type": "FeatureCollection",
            "features": [feature]
        }, f)

    # Convert to PNG
    gdf = gpd.GeoDataFrame.from_features([feature])
    
    # Filter geometry for countries with remote territories
    filtered_geometry = filter_main_landmass(gdf.geometry.iloc[0], matched_name)
    gdf = gpd.GeoDataFrame(geometry=[filtered_geometry])

    # Plot
    fig, ax = plt.subplots(figsize=(4, 4))
    gdf.plot(ax=ax, edgecolor="black", facecolor="none", linewidth=1)

    # Get bounds and add padding
    minx, miny, maxx, maxy = gdf.total_bounds
    padding_x = (maxx - minx) * 0.1
    padding_y = (maxy - miny) * 0.1

    ax.set_xlim(minx - padding_x, maxx + padding_x)
    ax.set_ylim(miny - padding_y, maxy + padding_y)
    ax.set_axis_off()

    # Save PNG
    png_path = OUTPUT_PNG / f"{safe_name}.png"
    plt.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close()
    
    return matched_name

def download_and_process_data():
    """Download the dataset and process all countries"""
    print("Downloading dataset...")
    response = requests.get(DATA_URL)
    geojson_data = response.json()
    features = geojson_data["features"]
    
    print(f"Dataset contains {len(features)} countries")
    print("\n🔄 PROCESSING COUNTRIES...")
    
    processed_countries = []
    for feature in tqdm(features):
        result = process_country(feature)
        if result:
            processed_countries.append(result)
    
    return processed_countries

def check_missing_countries(processed_countries):
    """Check which countries from target list are missing"""
    processed_set = set(processed_countries)
    
    still_missing = []
    for country in sorted(TARGET_COUNTRIES):
        if country not in processed_set:
            still_missing.append(country)
    
    return still_missing

def main():
    """Main function to run the country outline downloader"""
    print("=" * 50)
    print("COUNTRY OUTLINE DOWNLOADER")
    print("=" * 50)
    
    # Create output directories inside the 'countries' folder
    COUNTRIES_DIR.mkdir(exist_ok=True)
    OUTPUT_GEOJSON.mkdir(exist_ok=True)
    OUTPUT_PNG.mkdir(exist_ok=True)
    
    print(f"Output directories created/verified:")
    print(f"  - Main folder: {COUNTRIES_DIR}")
    print(f"  - GeoJSON: {OUTPUT_GEOJSON}")
    print(f"  - PNG: {OUTPUT_PNG}")
    
    # Download and process all countries
    processed_countries = download_and_process_data()
    
    # Final report
    print("\n" + "=" * 50)
    print(f"✅ Successfully processed {len(processed_countries)} countries")
    
    # Check for missing countries
    still_missing = check_missing_countries(processed_countries)
    
    if still_missing:
        print("\n⚠️  COUNTRIES NOT FOUND IN DATASET:")
        for country in still_missing:
            print(f"  - {country}")
    else:
        print("\n✅ All target countries were found and processed!")
    
    print("\n" + "=" * 50)
    print(f"Files saved to:")
    print(f"  - GeoJSON: {OUTPUT_GEOJSON}")
    print(f"  - PNG: {OUTPUT_PNG}")
    print("=" * 50)
    print("Done.")

if __name__ == "__main__":
    main()