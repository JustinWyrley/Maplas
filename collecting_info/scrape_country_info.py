import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import urllib.parse

BASE_DIR = Path(__file__).parent
COUNTRIES_DIR = BASE_DIR / 'countries'

HEADERS = {
    "User-Agent": "CountryDataScraperBot/1.0 (justinwyrley@icloud.com) python-requests/2.x"
}

session = requests.Session()
session.headers.update(HEADERS)

retry_strategy = Retry(
    total=5,
    backoff_factor=5, 
    status_forcelist=[429, 500, 502, 503, 504],
    respect_retry_after_header=True
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


def download_media(url, filepath):
    """Downloads a file from a URL and saves it to the given filepath."""
    if not url:
        return None
    
    if url.startswith('//'):
        url = 'https:' + url

    try:
        response = session.get(url, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return f"countries/{filepath.name}"
    except Exception as e:
        print(f"Error downloading media from {url}: {e}")
        return None


def extract_country_facts(html_excerpt):
    soup = BeautifulSoup(html_excerpt, 'html.parser')

    # Updated keys to reflect Nominal GDP
    facts = {
        'capital': None,
        'languages': None,
        'largest_religion': None,
        'area_total': None,
        'population': None,
        'gdp_nominal_total': None, # Does not work
        'gdp_nominal_per_capita': None, # Does not work
        'currency': None,
        'time_zone': None,
        'observes_dst': 0,
        'calling_code': None
    }

    current_category = None

    for row in soup.find_all('tr'):
        th = row.find('th')
        td = row.find('td')

        if th and not td:
            header_text = th.get_text(separator=" ", strip=True).lower()
            
            # Switch to targeting the Nominal GDP header
            if 'gdp' in header_text and 'nominal' in header_text:
                current_category = 'gdp_nominal'
            elif 'population' in header_text:
                current_category = 'population'
            elif 'area' in header_text:
                current_category = 'area'
            else:
                current_category = None 
            continue

        if not (th and td):
            continue

        label = th.get_text(separator=" ", strip=True).replace('\xa0', ' ').lower()
        clean_data = re.sub(r'\[.*?\]', '', td.get_text(separator=" ", strip=True)).strip()

        if 'capital' in label:
            facts['capital'] = clean_data
        elif 'official language' in label or 'national language' in label:
            facts['languages'] = clean_data
        elif 'religion' in label:
            
            # Handle different Wikipedia formatting for lists (<br> or <li>)
            for tag in td.find_all(['br', 'hr']):
                tag.replace_with('\n')
            for tag in td.find_all('li'):
                tag.insert(0, '\n')
                
            text = td.get_text(separator=" ", strip=True)
            text = re.sub(r'\[.*?\]', '', text).strip()
            
            # Split by newline and take the first valid line
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                facts['largest_religion'] = lines[0]
                
        elif 'currency' in label:
            facts['currency'] = clean_data
        elif 'time zone' in label:
            facts['time_zone'] = clean_data
        elif 'summer (dst)' in label or 'dst' in label:
            facts['observes_dst'] = 1
        elif 'calling code' in label:
            facts['calling_code'] = clean_data

        # Handle section-dependent rows using the new category
        if current_category == 'gdp_nominal':
            if 'total' in label:
                facts['gdp_nominal_total'] = clean_data
            elif 'per capita' in label:
                facts['gdp_nominal_per_capita'] = clean_data
                
        elif current_category == 'population':
            if 'total' in label or 'estimate' in label or 'census' in label or re.search(r'\b20\d{2}\b', label):
                if not facts['population']:
                    facts['population'] = clean_data
                    
        elif current_category == 'area':
            if 'total' in label:
                facts['area_total'] = clean_data

    return facts


def get_country_data(url):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        facts = extract_country_facts(response.text)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # More robust flag extraction logic
        infobox = soup.select_one('.infobox')
        flag_img = None
        
        if infobox:
            # First, try to find an image explicitly mentioning 'flag' in alt text
            flag_img = infobox.find('img', alt=re.compile(r'flag', re.IGNORECASE))
            # If not found, try the source URL
            if not flag_img:
                flag_img = infobox.find('img', src=re.compile(r'flag', re.IGNORECASE))
        
        # Fallback to the original selector just in case
        if not flag_img:
            flag_img = soup.select_one('.infobox-image img')
            
        flag_url = flag_img['src'] if flag_img else None
        
        audio_src = soup.select_one('.infobox audio source')
        anthem_url = audio_src['src'] if audio_src else None
        
        country_slug = urllib.parse.unquote(url.split('/')[-1]).replace(' ', '_')
        
        if flag_url:
            time.sleep(1) 
            ext = flag_url.split('.')[-1].split('?')[0]
            flag_path = COUNTRIES_DIR / f"{country_slug}_flag.{ext}"
            facts['flag_path'] = download_media(flag_url, flag_path)
        else:
            facts['flag_path'] = None

        if anthem_url:
            time.sleep(5)
            ext = anthem_url.split('.')[-1].split('?')[0]
            anthem_path = COUNTRIES_DIR / f"{country_slug}_anthem.{ext}"
            facts['anthem_path'] = download_media(anthem_url, anthem_path)
        else:
            facts['anthem_path'] = None

        return facts

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return {}


def main():
    COUNTRIES_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(BASE_DIR / 'countries.csv')

    print("Starting web scraping...")
    results = []
    
    for index, row in df.iterrows():
        url = row['url']
        print(f"Processing: {url}")
        results.append(get_country_data(url))
        
        if index < len(df) - 1:
            time.sleep(2)

    df = pd.concat([df, pd.DataFrame(results)], axis=1)
    df.to_csv(BASE_DIR / 'country_info.csv', index=False)
    print("Done. Results and files saved.")


if __name__ == "__main__":
    main()