"""
Main orchestrator script for running all country data scrapers.

This script coordinates the execution of all scrapers in the correct order:
1. country_collection.py - Gets the list of countries
2. scrape_country_info.py - Scrapes detailed country information
3. cleaning.py - Cleans and formats the data
4. Alcohol, Bordering Countries, Flag Colours, and Outline scrapers - Add additional data
"""

import sys
import traceback
from pathlib import Path

# Add the scrapers directory to the path so we can import from it
SCRAPERS_DIR = Path(__file__).parent / "scrapers"
sys.path.insert(0, str(SCRAPERS_DIR))


def run_scraper(name, func, required_files=None):
    """Helper function to run a scraper and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print('='*60)

    try:
        func()
        print(f"✓ {name} completed successfully")
        return True
    except Exception as e:
        print(f"✗ {name} failed with error: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all scrapers in the correct order."""
    results = {}

    # Step 1: Get the list of countries
    print("\n" + "="*60)
    print("STEP 1: Fetching country list")
    print("="*60)
    from country_collection import scrape_sovereign_states
    results['country_collection'] = run_scraper(
        "Country Collection",
        scrape_sovereign_states
    )

    # Step 2: Scrape detailed country info (depends on countries.csv)
    print("\n" + "="*60)
    print("STEP 2: Scraping detailed country information")
    print("="*60)
    from scrape_country_info import main as scrape_country_main
    results['country_info'] = run_scraper(
        "Country Info Scraper",
        scrape_country_main
    )

    # Step 3: Clean and format the data (depends on country_info.csv)
    print("\n" + "="*60)
    print("STEP 3: Cleaning and formatting data")
    print("="*60)
    from data_cleaner import main as cleaning_main
    results['cleaning'] = run_scraper(
        "Data Cleaning",
        cleaning_main
    )

    # Step 4: Run additional scrapers (depends on country_info_updated.csv)
    print("\n" + "="*60)
    print("STEP 4: Running additional data scrapers")
    print("="*60)

    # Alcohol consumption scraper
    from Alcohol_consumption_ranked_scraper import (
        scrape_alcohol_data,
        clean_country_names,
        add_ranking,
        merge_into_csv as merge_alcohol
    )
    def run_alcohol_scraper():
        df = scrape_alcohol_data()
        if not df.empty:
            df = clean_country_names(df)
            df = add_ranking(df)
            merge_alcohol(df)
    results['alcohol'] = run_scraper(
        "Alcohol Consumption Scraper",
        run_alcohol_scraper
    )

    # Bordering countries scraper
    from Bordering_Countries_Scraper import (
        scrape_land_borders,
        merge_into_csv as merge_borders
    )
    def run_border_scraper():
        df = scrape_land_borders()
        if not df.empty:
            merge_borders(df)
    results['borders'] = run_scraper(
        "Bordering Countries Scraper",
        run_border_scraper
    )

    # Flag colours scraper
    from Country_flag_colour_scraper import (
        scrape_flag_colours,
        merge_into_csv as merge_flags
    )
    def run_flag_scraper():
        df = scrape_flag_colours()
        if not df.empty:
            merge_flags(df)
    results['flag_colours'] = run_scraper(
        "Flag Colours Scraper",
        run_flag_scraper
    )

    # Country outline scraper
    from country_outline_scraper import main as outline_main
    results['outlines'] = run_scraper(
        "Country Outline Scraper",
        outline_main
    )

    # Print summary
    print("\n" + "="*60)
    print("SCRAPING SUMMARY")
    print("="*60)
    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {name:.<40} {status}")

    failed = sum(1 for s in results.values() if not s)
    if failed == 0:
        print("\n✓ All scrapers completed successfully!")
    else:
        print(f"\n✗ {failed} scraper(s) failed. Check the output above for details.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
