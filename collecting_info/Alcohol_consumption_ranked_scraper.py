import pandas as pd
import requests
from bs4 import BeautifulSoup

def scrape_alcohol_data():
    """Scrape alcohol consumption data from Wikipedia"""
    url = "https://en.wikipedia.org/wiki/List_of_countries_by_alcohol_consumption_per_capita"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table - it's the first table with class 'wikitable'
    table = soup.find('table', {'class': 'wikitable'})
    
    # Extract data
    data = []
    rows = table.find_all('tr')[1:]  # Skip header
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 2:
            country = cols[0].text.strip()
            # Remove any reference numbers in brackets
            country = country.split('[')[0].strip()
            
            # Get 2019 consumption (second column)
            consumption = cols[1].text.strip().replace('—', '0')
            if consumption == '–':
                consumption = '0'
            
            data.append([country, consumption])
    
    return pd.DataFrame(data, columns=['country', 'alcohol_consumption'])

def clean_country_names(df):
    """Standardize country names to match your existing dataset"""
    
    # Dictionary of country name replacements
    replacements = {
        'Bahamas, The': 'Bahamas',
        'Bahamas': 'Bahamas',  # Keep as is
        'Congo, Democratic Republic of the': 'Democratic Republic of the Congo',
        'Congo, Republic of the': 'Republic of the Congo',
        'Gambia, The': 'Gambia',
        'Georgia': 'Georgia (country)',
        'Ireland': 'Republic of Ireland',
        'Macedonia': 'North Macedonia',
        'Micronesia, Federated States of': 'Federated States of Micronesia',
        'Russia': 'Russia',
        'South Korea': 'South Korea',
        'United Kingdom': 'United Kingdom',
        'United States': 'United States',
        'Ivory Coast': 'Ivory Coast',
        'North Korea': 'North Korea',
        'South Korea': 'South Korea',
        'São Tomé and Príncipe': 'São Tomé and Príncipe',
    }
    
    # Apply replacements
    df['country'] = df['country'].replace(replacements)
    
    # Filter out territories not in your main dataset
    exclude_list = ['Netherlands Antilles', 'New Caledonia', 'Niue', 'Cook Islands']
    df = df[~df['country'].isin(exclude_list)]
    
    return df

def create_ranking(df):
    """Create ranking (1 = highest consumption)"""
    df['alcohol_consumption'] = pd.to_numeric(df['alcohol_consumption'], errors='coerce')
    df = df.dropna(subset=['alcohol_consumption'])
    
    # Create rank (1 is highest consumption)
    df['alcohol_consumption_ranked'] = df['alcohol_consumption'].rank(
        method='min', 
        ascending=False
    ).astype(int)
    
    return df[['country', 'alcohol_consumption_ranked']]

def main():
    print("Scraping alcohol consumption data...")
    
    # Scrape the data
    df = scrape_alcohol_data()
    print(f"Scraped {len(df)} countries")
    
    # Clean country names
    df = clean_country_names(df)
    print(f"After cleaning: {len(df)} countries")
    
    # Create ranking
    df_ranked = create_ranking(df)
    print(f"Created rankings for {len(df_ranked)} countries")
    
    # Load existing country_info.csv
    try:
        country_info = pd.read_csv('country_info.csv')
        print(f"Loaded country_info.csv with {len(country_info)} rows")
        
        # Merge the ranked data
        country_info = country_info.merge(df_ranked, on='country', how='left')
        
        # Save back to CSV
        country_info.to_csv('country_info.csv', index=False)
        print("Successfully appended alcohol_consumption_ranked to country_info.csv")
        
    except FileNotFoundError:
        print("country_info.csv not found - creating new file with just the rankings")
        df_ranked.to_csv('country_info.csv', index=False)
    
    
    
    return df_ranked

if __name__ == "__main__":
    df_result = main()