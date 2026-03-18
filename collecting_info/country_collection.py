import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

# Get the directory where the script is located
BASE_DIR = Path(__file__).parent

def scrape_sovereign_states():
    """
    Scrapes country names and their Wikipedia URLs from the "List of sovereign states" page
    Filters for UN member states and General Assembly observer states
    Allows for manual overrides and additions 
    """
    url = "https://en.wikipedia.org/wiki/List_of_sovereign_states"
    base_url = "https://en.wikipedia.org"
    
    # Standard user-agent to ensure the server processes the request properly
    headers = {
        "User-Agent": "CountryDataScraperBot/1.0 (justinwyrley@icloud.com) python-requests/2.x"
    }
    
    # 1. Fetch the webpage content
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve the page. Error: {e}")
        return
        
    # 2. Parse the HTML using Beautiful Soup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 3. Locate the primary data table
    tables = soup.find_all('table', class_='wikitable')
    target_table = None
    
    for table in tables:
        headers_text = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if any("common and formal names" in h for h in headers_text) or any("membership within the un system" in h for h in headers_text):
            target_table = table
            break
            
    if not target_table:
        print("Could not find the sovereign states table. The page structure might have changed.")
        return

    country_data = []

    # 4. Dictionary for manual overrides
    # Map the exact scraped Wikipedia title to your desired output
    manual_overrides = {
        'Kingdom of the Netherlands': {
            'name': 'Netherlands',
            'url': 'https://en.wikipedia.org/wiki/Netherlands'
        },
        'Danish Realm': {
            'name': 'Denmark',
            'url': 'https://en.wikipedia.org/wiki/Denmark'
        },
    }

    # 5. Iterate through the rows, skipping the header row
    for row in target_table.find_all('tr')[1:]:
        cols = row.find_all('td')
        
        if len(cols) < 2:
            continue
            
        first_cell = cols[0]
        status_cell = cols[1]
        
        # Filter for UN members and observer states
        status_text = status_cell.get_text(strip=True).lower()
        if "un member" not in status_text and "observer" not in status_text:
            continue

        # Extract the country link
        link_tag = None
        for a in first_cell.find_all('a'):
            if a.has_attr('href') and a.has_attr('title') and a['href'].startswith('/wiki/'):
                if not a['href'].startswith('/wiki/File:'):
                    link_tag = a
                    break
                    
        if link_tag:
            raw_name = link_tag['title']
            raw_url = base_url + link_tag['href']
            
            # Apply override if it exists; otherwise, use the raw data
            if raw_name in manual_overrides:
                country_data.append(manual_overrides[raw_name])
            else:
                country_data.append({
                    'name': raw_name, 
                    'url': raw_url
                })

    # 6. List of manual additions (for entities not scraped at all)
    manual_additions = [
        {
            'name': 'Kosovo',
            'url': 'https://en.wikipedia.org/wiki/Kosovo'
        }
    ]

    for country in manual_additions:
        if not any(d['name'].lower() == country['name'].lower() for d in country_data):
            country_data.append(country)

    if not country_data:
        print("No country data was scraped. The page structure might have changed.")
        return

    # 7. Format and save the data
    countries = pd.DataFrame(country_data)
    
    # Eliminate any potential duplicates and sort alphabetically
    countries.drop_duplicates(subset=['name'], keep='first', inplace=True)
    countries = countries.sort_values(by='name').reset_index(drop=True)
    
    output_path = BASE_DIR / 'countries.csv'
    countries.to_csv(output_path, index=False)
    print(f"Successfully scraped {len(countries)} countries and saved to {output_path}")

if __name__ == "__main__":
    scrape_sovereign_states()