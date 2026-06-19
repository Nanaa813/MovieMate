import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TMDB_API_KEY")

url = "https://api.themoviedb.org/3/movie/popular"

response = requests.get(url, params={
    "api_key": api_key,
    "language": "en-US",
    "page": 1
})

data = response.json()

print("Popular Movies from TMDB API")
print("-" * 35)

for index, movie in enumerate(data.get("results", [])[:10], start=1):
    title = movie.get("title", "Unknown Title")
    rating = movie.get("vote_average", 0)
    release_date = movie.get("release_date", "-")

    print(f"{index}. {title} | Rating: {rating:.1f} | Release: {release_date}")