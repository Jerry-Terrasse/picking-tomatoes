import asyncio
import aiohttp
from aiohttp.cookiejar import SimpleCookie

import json
import sys
import time
import base64
import glob
import math
from loguru import logger
import pickle

from tqdm import tqdm
from colorama import Fore

logger.remove()
logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
logger.add("get_reviews.log", format="{time} {level} {message}", level="INFO")

url_template = "https://www.rottentomatoes.com/napi/movie/%s/reviews/user"

movies: dict[str, dict] = {}
fresh = False
max_reqs = 5

sem = asyncio.Semaphore(max_reqs)

headers = json.load(open("headers.json", "r"))
cookies = SimpleCookie(headers['Cookie'])
del headers['Cookie']

def await_(coroutine: asyncio.coroutine):
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(coroutine)
    return result

@logger.catch(reraise=True)
async def get_review(title: str, url: str, after: str|None) -> dict|None:
    logger.debug(f"<{title}> GET {url}")
    async with aiohttp.ClientSession(cookies=cookies) as session:
        if after:
            params = {'after': after}
        else:
            params = {}
        while True:
            async with session.get(url, params=params, headers=headers) as response:
                # logger.debug(cookies['bm_sv'], "pre")
                cookies.update(response.cookies)
                # logger.debug(cookies['bm_sv'], "post")
                if response.status != 200:
                    logger.warning(f"<{title}> Status {response.status} for {url}, retrying")
                    # breakpoint()
                    time.sleep(20) # blocked waiting
                    continue
                try:
                    data = await response.json()
                except Exception as e:
                    logger.warning(f"<{title}> Failed to parse json: {e}, retrying")
                    text = await response.text()
                    # breakpoint()
                    time.sleep(20) # blocked waiting
                    continue
                time.sleep(0.1) # blocked waiting
                return data

@logger.catch(reraise=True)
async def fetch(title: str, ems: str, previous=None, max_reviews=math.inf) -> dict[str, dict]|None:
    url = url_template % ems
    reviews = previous if previous else {}
    after = None
    while True:
        if len(reviews) >= max_reviews:
            break
        
        data = await get_review(title, url, after)
        if data is None:
            logger.error(f"<{title}> Fetch failed")
            return None
        
        for review in data['reviews']:
            if 'reviewId' not in review:
                logger.debug(f"<{title}> No reviewId, skip")
                continue
            if review['reviewId'] in reviews:
                logger.debug(f"<{title}> Already exists: {review['reviewId']}")
                logger.debug(f"<{title}> Skip all remain reviews")
                break
            reviews[review['reviewId']] = review
            if len(reviews) >= max_reviews:
                logger.debug(f"<{title}> Max reviews reached: {max_reviews}")
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

@logger.catch(reraise=True)
async def work(title: str, ems: str, previous=None, max_reviews=math.inf, pbar=None) -> None|str:
    async with sem:
        logger.info(f"Working on <{title}>")
        reviews = await fetch(title, ems, previous, max_reviews)
        if reviews is None:
            logger.error(f"<{title}> Failed to fetch reviews, skip")
            pbar.update(1)
            return title
        json.dump(reviews, open(f"data/{ems}.json", "w"), indent=4)
        logger.success(f"Saved {len(reviews)} reviews for <{title}>")
        pbar.update(1)

@logger.catch(reraise=True)
async def main():
    global movies
    movies = json.load(open(sys.argv[1], 'r'))
    
    # test = movies[]
    
    tasks: list[asyncio.Task[None|str]] = []
    
    bar_format = f"{Fore.MAGENTA}{{l_bar}}{{bar}}{Fore.CYAN}{{r_bar}}{Fore.RESET}"
    with tqdm(total=len(movies), bar_format=bar_format) as pbar:
        for title, movie in movies.items():
            ems = movie['emsId']
            if glob.glob(f"data/{ems}.json") != [] and not fresh:
                logger.warning(f"Skipping {title}")
                pbar.update(1)
                # time.sleep(0.01)
                continue
            reviews_promise = asyncio.create_task(work(title, ems, max_reviews=200, pbar=pbar))
            tasks.append(reviews_promise)
        if tasks == []:
            logger.error("No movies to fetch")
            return
        
        logger.info(f"Fetching {len(tasks)} movies")
        
        done, pending = await asyncio.wait(tasks)
    
    if len(pending) > 0:
        logger.error(f"{len(pending)} tasks are not done")
        breakpoint()
        return
    
    for task in done:
        res = task.result()
        if res is None:
            continue
        logger.error(f"Failed task: {res}")
    # for task in done:
    #     res = task.result()
    #     if res is None:
    #         continue
    #     title, reviews = res
    #     ems = movies[title]['emsId']
    #     # breakpoint()

if __name__ == '__main__':
    asyncio.run(main())