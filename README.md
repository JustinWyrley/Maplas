# Geo trivia
This is a work in progress Geo Trivia game. It scrapes data from wikipedia and other websites and gives you questions using these we want to make other trivia games and wld appreciate any suggestions

### How it works

1. country_collection.py collects UN recognised country names and urls from wikipedia 
2. The series of .py files each add seperate data to the country info. scrape_country_info should be ran first as the others build on top of it. In the future this will be able to be done with one command and will be organised better
3. Once there is an up to date set of data this can played using countrydle.html currently we run it using the live server extension however once the repo is public we will host it from there.
