import json
import requests
import sys
import time
import base64
import glob

# url = "https://www.rottentomatoes.com/napi/browse/movies_in_theaters/sort:newest"
url = "https://www.rottentomatoes.com/napi/browse/movies_at_home/sort:newest"
# https://www.rottentomatoes.com/napi/movie/ff5d4e50-22d1-4ffc-a41d-179bd193e5d8/reviews/user?after=eyJyZWFsbV91c2VySWQiOiJGYW5kYW5nb19FMjJFNTk5OS1CQkI3LTREMTItQjEyNS03NTE2NEEzNTkyMjIiLCJlbXNJZCI6ImZmNWQ0ZTUwLTIyZDEtNGZmYy1hNDFkLTE3OWJkMTkzZTVkOCIsImVtc0lkX2hhc1Jldmlld0lzVmlzaWJsZSI6ImZmNWQ0ZTUwLTIyZDEtNGZmYy1hNDFkLTE3OWJkMTkzZTVkOF9UIiwiY3JlYXRlRGF0ZSI6IjIwMjMtMDctMTZUMDM6NDE6NDkuMzQwWiJ9&pagecount=199

movies: dict[str, dict] = {}
if glob.glob("movies.json"):
    movies = json.load(open("movies.json", "r"))
    print(f"Loaded {len(movies)} movies")
    breakpoint()

if __name__ == '__main__':
    after = None
    if len(sys.argv) > 1:
        after = int(sys.argv[1])
    
    print(f"{after=}")
    
    while True:
        if after is None:
            response = requests.get(url)
        else:
            # Base64
            after_encoded = base64.b64encode(str(after).encode('utf-8')).decode('utf-8')
            response = requests.get(url, params={'after': after_encoded})
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            breakpoint()
        
        data = json.loads(response.text)
        items: list[dict] = data['grid']['list']
        for movie in items:
            print(f"{movie['title']} => {movie['emsId']}")
            if movie['title'] in movies:
                print(f"Already exists: {movie['title']}")
                continue
            movies[movie['title']] = movie
        
        if not data['pageInfo']['hasNextPage']:
            break
        
        after_encoded = data['pageInfo']['endCursor']
        after = int(base64.b64decode(after_encoded).decode('utf-8'))
        
        # time.sleep(1)
    
    json.dump(movies, open("movies.json", "w"), indent=4)