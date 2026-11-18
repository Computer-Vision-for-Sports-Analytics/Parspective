import asyncio
import json
import requests
import logging
import os

log = logging.getLogger(__name__)

USE_MOCK = False #this will be false when api is ready
API_URL = "http:example"# api link go here after api is ready
SHARE_PATH = "/share"
#SHARE_PATH = "/post"   
# API_KEY = "..."  #loaded from config 

class ShareError(Exception): 
    """Raised when sharing fails after all retries."""


def load_stats(path: str) -> dict: #loads stats from json where the Parspective data is held
    # reads the stats file and returns it as a dictionary
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

#func takes in email, stats and video path and posts to the api
def _post(email:str, stats:dict, video_path:str): #-> None optional
    with open(video_path, 'rb') as f: #opens the video path
        r= requests.post( #sends the api's HTTPS post request
            f"{API_URL}{SHARE_PATH}", #access the api to share
        #   headers={"x-api-key": API_KEY}, # this is for when we have the API key in prod
            data={"email": email, "stats": json.dumps(stats)}, #holds the text fields and turns dict  in to a json string
            files={"video": ("putt.mp4", f, "video/mp4")}, #putt.mp4 will have to be changed to the video name. with video mp4 the api knows to look for a video
            # video mp4 content type
            timeout=(10, 120), #(connect timeout, read timeout)
        )
    print(r.status_code, r.text[:500])
    r.raise_for_status()


#for testing mock is true
async def share_capture(email: str, stats_path: str, video_path: str,
                        retries: int = 3) -> None:
    if USE_MOCK:
        await asyncio.sleep(1.5)  # fake network delay
        print("MOCK SHARE", email, stats_path, video_path)
        # To test the error path, uncomment:
        # raise ShareError("mock failure")
        return

    try: #in prod
        stats = load_stats(stats_path)
    except (OSError, json.JSONDecodeError) as e: #check for OS error and Json decode error
        log.error("Couldn't read stats file: %s", e) # outputs couldnt read file as error
        raise ShareError("Couldn't read the stats file.") from e
    if not os.path.isfile(video_path): #check if video is found or not
        log.error("Video file not found: %s", video_path)
        raise ShareError("Couldn't find the video file.") #log and output error video not found

    for attempt in range(1, retries + 1):
        try:
            await asyncio.to_thread(_post, email, stats, video_path)  # keeps the UI responsive
            return
        except requests.HTTPError as e:
            # 4xx means the request itself is bad: retrying won't help
            if e.response is not None and 400 <= e.response.status_code < 500:
                log.error("Share rejected: %s", e)
                raise ShareError("The server rejected the request.") from e
            log.warning("Share attempt %d failed: %s", attempt, e)
        except (requests.ConnectionError, requests.Timeout, OSError) as e:
            log.warning("Share attempt %d failed: %s", attempt, e)

        if attempt < retries:
            await asyncio.sleep(2 ** attempt)  # wait 2s, then 4s

    raise ShareError("Couldn't reach the server. Check the connection.")

if __name__ == "__main__":
    asyncio.run(share_capture("test@example.com", "putt_stats.json", "putt.mp4"))
#in prodution:
#USE_MOCK = False
#the real API_URL
#optionally, uncomment the API_KEY header
#change "putt.mp4" to the real filename  (the name only affects what the API sees)