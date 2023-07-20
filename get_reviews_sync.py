import json
import requests
import sys
import time
import base64
import glob
import math
from loguru import logger
import pickle

logger.add("get_reviews.log", format="{time} {level} {message}", level="INFO")

url_template = "https://www.rottentomatoes.com/napi/movie/%s/reviews/user"

movies: dict[str, dict] = {}
fresh = False

@logger.catch
def fetch(title: str, ems: str, previous=None, max_refiews=math.inf) -> dict[str, dict]:
    url = url_template % ems
    reviews = previous if previous else {}
    after = None
    while True:
        if len(reviews) >= max_refiews:
            break
        if after:
            logger.info(f"<{title}> GET {url} with 'after'")
            response = requests.get(url, params={'after': after})
        else:
            logger.info(f"<{title}> GET {url}")
            response = requests.get(url)
        try:
            data = json.loads(response.text)
        except json.decoder.JSONDecodeError:
            breakpoint()
            pickle.dump(response, open(f"data/{ems}_response.pickle", "wb"))
        for review in data['reviews']:
            if review['reviewId'] in reviews:
                logger.debug(f"<{title}> Already exists: {review['reviewId']}")
                logger.debug(f"<{title}> Skip all remain reviews")
                break
            reviews[review['reviewId']] = review
            if len(reviews) >= max_refiews:
                logger.debug(f"<{title}> Max reviews reached: {max_refiews}")
                break
        else:
            # should continue fetching
            if not data['pageInfo']['hasNextPage']:
                logger.debug(f"<{title}> No more reviews")
                break
            after = data['pageInfo']['endCursor']
            continue
        # skip all remain reviews
        break
    return reviews

@logger.catch
def main():
    global movies
    movies = json.load(open(sys.argv[1], 'r'))
    for title, movie in movies.items():
        ems = movie['emsId']
        if glob.glob(f"data/{ems}.json") != [] and not fresh:
            logger.warning(f"Skipping {title}")
            continue
        reviews = fetch(title, ems, max_refiews=200)
        assert isinstance(reviews, dict)
        json.dump(reviews, open(f"data/{ems}.json", "w"), indent=4)
        logger.info(f"Saved {len(reviews)} reviews for <{title}>")
        # breakpoint()

if __name__ == '__main__':
    main()