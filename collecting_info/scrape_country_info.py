import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).parent


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}


def extract_country_facts(html_excerpt):
    soup = BeautifulSoup(html_excerpt, 'html.parser')

    facts = {
        'capital': None,
        'languages': None,
        'largest_religion': None,
        'area_total': None,
        'population': None,
        'gdp_ppp_total': None,
        'gdp_ppp_per_capita': None,
        'currency': None,
        'time_zone': None,
        'observes_dst': 0,
        'calling_code': None
    }

    current_section = None

    for row in soup.find_all('tr'):
        th_header = row.find('th', class_='infobox-header')
        if th_header:
            current_section = th_header.get_text(strip=True).lower()
            continue

        th = row.find('th')
        td = row.find('td')

        if not (th and td):
            continue

        label = th.get_text(separator=" ", strip=True).replace('\xa0', ' ').lower()
        clean_data = re.sub(r'\[.*?\]', '', td.get_text(separator=" ", strip=True)).strip()

        if 'capital' in label:
            facts['capital'] = clean_data
        elif 'official language' in label or 'national language' in label:
            facts['languages'] = clean_data
        elif 'religion' in label:
            first_religion = td.find('li')
            facts['largest_religion'] = (
                re.sub(r'\[.*?\]', '', first_religion.get_text()).strip()
                if first_religion else clean_data
            )
        elif 'currency' in label:
            facts['currency'] = clean_data
        elif 'time zone' in label:
            facts['time_zone'] = clean_data
        elif 'summer (dst)' in label or 'dst' in label:
            facts['observes_dst'] = 1
        elif 'calling code' in label:
            facts['calling_code'] = clean_data
        elif '• total' in label:
            if current_section and 'area' in current_section:
                facts['area_total'] = clean_data
            elif current_section and 'gdp' in current_section and 'ppp' in current_section:
                facts['gdp_ppp_total'] = clean_data
        elif '• 20' in label and 'estimate' in label:
            if current_section and 'population' in current_section:
                facts['population'] = clean_data
        elif '• per capita' in label:
            if current_section and 'gdp' in current_section and 'ppp' in current_section:
                facts['gdp_ppp_per_capita'] = clean_data

    return facts


def get_country_data(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return extract_country_facts(response.text)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return {}


def main():
    df = pd.read_csv(BASE_DIR / 'country_info.csv')

    print("Starting webscraping...")
    results = []
    for _, row in df.iterrows():
        url = row['url']
        print(f"Processing: {url}")
        results.append(get_country_data(url))

    df = pd.concat([df, pd.DataFrame(results)], axis=1)
    df.to_csv(BASE_DIR / 'country_info.csv', index=False)
    print("Done. Results saved")


if __name__ == "__main__":
    main()