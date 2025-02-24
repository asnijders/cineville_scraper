# Cineville & Letterboxd Watchlist Matcher  

A Python script that scrapes Cineville movie listings and checks whether a film from your Letterboxd watchlist is being played.  

## Possible Approaches  

### 1. Look up each film in the watchlist on the Cineville page  
- **Downside:** Requires semantic matching and numerous page visits.  

### 2. Collect all films from the Cineville `all_films` page, then match with the Letterboxd watchlist  
- **Problem:** Only allows fetching films screened in the next **3 days**, not further into the future.  

## System Overview  

- **Daily Scraping:** Every morning, the script collects new films for the coming 3 days (potentially using Apache Airflow).  
- **Database Storage:** Films are stored in an S3-hosted database.  
- **User Interaction:**  
  - Users interact with the app via a **Streamlit** interface.  
  - Users provide their Letterboxd watchlist.  
- **Microservices:**  
  1. **Primary Scraper** – Fetches Cineville listings and stores them.  
  2. **Watchlist Matching Service** –  
     - Scrapes the user’s Letterboxd watchlist.  
     - Performs smart matching against the Cineville showings database.  
     - Returns whether any watchlist films will be screened.  

## To-Do  

✅ **Scrape Cineville `all_films` page**  
⬜ Clean up text (remove elements like "(re-release)", etc.)  
✅ Add metadata (theaters, showtimes, ticket links)  
⬜ Scrape Letterboxd user page  
⬜ Perform smart semantic matching  

## Future Features  

- **Extended Lookup:** Include films beyond the next 3 days.  
- **City Toggle:** Allow users to filter showings by location.  
- **Personalized Recommendations:**  
  - Suggest films based on user’s watch history.  
  - Since Letterboxd user data is limited, explore public review data.  
  - Possible approach:  
    1. Identify similar users (even from external datasets).  
    2. Find out what similar users liked.  
    3. Recommend those titles and check if they are playing soon.  
