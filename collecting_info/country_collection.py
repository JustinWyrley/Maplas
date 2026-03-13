import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_wiki_un_members():
    url = "https://en.wikipedia.org/wiki/Member_states_of_the_United_Nations"
    base_url = "https://en.wikipedia.org"
    
    # Add a standard user-agent to ensure the server processes the request properly
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 1. Fetch the webpage content
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return
        
    # 2. Parse the HTML using Beautiful Soup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 3. Target the data tables
    tables = soup.find_all('table', class_='wikitable')
    
    country_data = []
    
    for table in tables:
        rows = table.find_all('tr')
        
        if not rows:
            continue
            
        # Verify if this is the target table by checking the header row text
        header = rows[0].text.lower()
        if "member state" in header and "date of admission" in header:
            
            # Iterate through the rows, skipping the initial header
            for row in rows[1:]:
                # The country name is located in the first <th> or <td> cell of the row
                first_cell = row.find(['th', 'td'])
                
                if first_cell:
                    # Find all links within the cell
                    links = first_cell.find_all('a')
                    
                    for link_tag in links:
                        country_name = link_tag.text.strip()
                        
                        # The flag icon link has no text. If text exists, it is the country link.
                        if country_name:
                            # Wikipedia hrefs are relative (e.g., '/wiki/Afghanistan'), 
                            # so we append them to the base URL
                            country_url = base_url + link_tag['href']
                            
                            country_data.append({
                                'name': country_name, 
                                'url': country_url
                            })
                            break # Move to the next row once the correct link is processed
            
            # Break the outer loop once the main table has been fully parsed
            break

    countries = pd.DataFrame(country_data)
    countries.to_csv('country_info.csv', index=False)


if __name__ == "__main__":
    scrape_wiki_un_members()