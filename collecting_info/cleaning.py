import pandas as pd
import re

def format_population(pop_str):
    if pd.isna(pop_str): 
        return ""
    
    # Extract numeric part
    multiplier = 1_000_000 if 'million' in pop_str.lower() else 1
    nums = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', pop_str)
    if not nums: 
        return ""
    
    val = float(nums[0].replace(',', '')) * multiplier
    
    # Rounding logic
    if val >= 1_000_000:
        rounded_m = round(val / 1_000_000, 1)
        return f"{int(rounded_m) if rounded_m == int(rounded_m) else rounded_m} million"
    elif val >= 100_000:
        return f"{int(round(val, -5)):,}"
    elif val >= 1_000:
        return f"{int(round(val, -3)):,}"
    else:
        return str(int(val))

def format_timezone(text):
    if pd.isna(text):
        return text
    
    # 1. Standardise dashes and minus signs
    text = text.replace('–', '-').replace('—', '-').replace('−', '-')
    
    # 2. Slice off anything inside or after parentheses
    text = text.split('(')[0]
    
    # 3. Clean and format the numerical offsets
    def clean_offset(match):
        sign = match.group(1).strip() if match.group(1) else ''
        hours = int(match.group(2)) 
        fraction = match.group(3) if match.group(3) else ''
        
        if fraction in [':00', '.0', '']:
            return f"{sign}{hours}"
        return f"{sign}{hours}{fraction}"
        
    text = re.sub(r'([±+-]?)\s*(\d+)((?:[:.]\d+)?)', clean_offset, text)
    
    # 4. Remove all unwanted alphabetical text
    words_to_keep = {'utc', 'to', 'and'}
    def filter_words(match):
        word = match.group(0)
        if word.lower() in words_to_keep:
            return 'UTC' if word.lower() == 'utc' else word.lower()
        return ''
        
    text = re.sub(r'[A-Za-z]+', filter_words, text)
    
    # 5. Tidy up spacing
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'UTC(?=[^\s])', 'UTC ', text) 
    
    # 6. Remove dangling punctuation
    text = text.strip(' ,;/')
    
    return text

def format_area(area_str):
    if pd.isna(area_str): 
        return ""
    
    match = re.search(r'([\d,]+(?:\.\d+)?)\s*km', str(area_str), re.IGNORECASE)
    
    if match:
        num_str = match.group(1).replace(',', '')
        val = float(num_str)
        if val.is_integer():
            return f"{int(val):,} km²"
        else:
            return f"{val:,} km²"
    return ""

def format_currency(text):
    if pd.isna(text): 
        return ""
    
    matches = re.findall(r'\(([^)]+)\)', str(text))
    if not matches:
        return ""
        
    formatted_items = []
    for match in matches:
        inner_text = match.strip()
        if re.fullmatch(r'[A-Za-z]+', inner_text):
            formatted_items.append(f"({inner_text})")
        else:
            formatted_items.append(inner_text)
            
    return ' '.join(formatted_items)

def main():
    # Load initial data
    df = pd.read_csv('collecting_info/country_info.csv')

    # Add duck data
    duck = pd.read_csv('collecting_info/random_data/duck_data.csv', dtype={'Population Count': str, 'Ducks Per Capita (per 1.000)': str})
    duck['name'] = duck['Country/Territory']
    duck.reset_index(inplace=True)
    duck['index'] = duck['index'] + 1
    duck['duck_pop_rank'] = duck['index'].astype('Int64')
    duck = duck[['duck_pop_rank', 'name']]
    df = pd.merge(df, duck, on='name', how='left')

    # Manually add missing info
    df.at[0, "calling_code"] = "+93"
    df.at[97, "time_zone"] = "UTC +1"
    df.at[20, "languages"] = "bosnian"
    df.at[108, "area_total"] = "33,843 km 2"
    df.at[29, "largest_religion"] = "Christianity"
    df.at[36, "largest_religion"] = "Islam"
    df.at[61, "largest_religion"] = "Christianity"
    df.at[70, "largest_religion"] = "Christianity"
    df.at[81, "largest_religion"] = "Shinto"
    df.at[116, "largest_religion"] = "Christianity"
    df.at[136, "largest_religion"] = "Christianity"
    df.at[141, "largest_religion"] = "Christianity"
    df.at[179, "largest_religion"] = "Islam"
    df.at[138, "time_zone"] = "UTC ±0"

    # Apply data cleaning transformations
    df['population'] = df['population'].apply(format_population)
    
    # Alphabetical country ranking
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'alphabetic_country_rank'}, inplace=True)
    df['alphabetic_country_rank'] = df['alphabetic_country_rank'] + 1

    # Clean up timezones
    df['time_zone'] = df['time_zone'].apply(format_timezone)
    zero_replacements = {'UTC +0': 'UTC ±0', 'UTC -0': 'UTC ±0', 'UTC 0': 'UTC ±0'}
    for old_val, new_val in zero_replacements.items():
        df['time_zone'] = df['time_zone'].str.replace(old_val, new_val, regex=False)

    # Clean up area, currency and capital
    df['area_total'] = df['area_total'].apply(format_area)
    df['currency'] = df['currency'].apply(format_currency)
    df['capital'] = df['capital'].str.extract(r'^(\D+)')[0].str.strip()

    # Add continents
    continents = pd.read_csv('collecting_info/random_data/list-of-countries-by-continent-2026.csv')
    continents.rename(columns={'country': 'name'}, inplace=True)
    df = pd.merge(df, continents[['name', 'continent']], on='name', how='left')

    # Final Save
    df.to_csv('country_info_updated.csv', index=False)
    print("Process complete. File saved as 'country_info_updated.csv'.")

if __name__ == "__main__":
    main()