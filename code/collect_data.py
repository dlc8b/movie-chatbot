# collect_data.py
# Gathers movie info from 3 legal APIs and saves it to movies.json
import json       # lets us save data to a file
import datetime   # lets us stamp the collection date
import os         # lets us access environment variables
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_json(url, params, headers=None):
    """Fetch and decode a JSON response using Python's standard library."""
    url = f"{url}?{urlencode(params)}"
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=30) as response:
        return json.load(response)

#create an .env file with your API keys
OMDB_KEY = os.getenv("OMDB_KEY")
TMDB_KEY = os.getenv("TMDB_KEY")

# Start small; grow to 40+ movies for the final report
TITLES = ["Inception", "The Godfather", "Barbie", "Cats", "Parasite",
          "Joker", "Interstellar", "The Room", "Titanic", "Shrek"]

def get_omdb(title):
    # OMDb returns IMDb rating, Rotten Tomatoes %, Metacritic, plot
    params = {"t": title, "apikey": OMDB_KEY}
    return get_json("https://www.omdbapi.com/", params)

def get_wikipedia(title, year):
    # Search Wikipedia for the film's page and grab its intro text
    params = {"action": "query", "generator": "search",
              "gsrsearch": f"{title} {year} film", "gsrlimit": 1,
              "prop": "extracts", "exintro": 1, "explaintext": 1,
              "format": "json"}
    headers = {"User-Agent": "MovieReviewClassProject/0.1"}  # Wikipedia asks for this
    data = get_json("https://en.wikipedia.org/w/api.php", params, headers)
    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        return {"text": page.get("extract", ""),
                "url": f"https://en.wikipedia.org/?curid={page_id}"}
    return {"text": "", "url": ""}   # nothing found

def get_tmdb_reviews(title, year):
    # Step 1: find the movie's TMDB id
    params = {"api_key": TMDB_KEY, "query": title, "year": year}
    found = get_json("https://api.themoviedb.org/3/search/movie", params)
    if not found.get("results"):
        return {"reviews": [], "url": ""}
    movie_id = found["results"][0]["id"]
    # Step 2: fetch audience reviews (we drop usernames to avoid personal info)
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews"
    rev = get_json(url, {"api_key": TMDB_KEY})
    reviews = [{"text": r["content"][:500]} for r in rev.get("results", [])[:5]]
    return {"reviews": reviews,
            "url": f"https://www.themoviedb.org/movie/{movie_id}"}

all_movies = []
for title in TITLES:
    omdb = get_omdb(title)
    if omdb.get("Response") != "True":      # OMDb couldn't find it
        print("Skipping (not found):", title)
        continue
    year = omdb["Year"]
    all_movies.append({
        "title": omdb["Title"],
        "year": year,
        "omdb": omdb,
        "imdb_url": f"https://www.imdb.com/title/{omdb['imdbID']}/",  # link only, no scraping
        "wikipedia": get_wikipedia(omdb["Title"], year),
        "tmdb": get_tmdb_reviews(omdb["Title"], year),
        "collected": datetime.date.today().isoformat(),  # record collection date
    })
    print("Collected:", omdb["Title"])

# Save everything so the bot doesn't re-download each time
with open("movies.json", "w") as f:
    json.dump(all_movies, f, indent=2)