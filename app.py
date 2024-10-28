from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import numpy as np
import time
import io
import threading
import pandas as pd
import uvicorn
import matplotlib
import asyncio
import aiohttp
import requests

matplotlib.use('Agg')

app = FastAPI()

import logging
logging.basicConfig(level=logging.INFO)

# 전역 변수 선언
ratings_df = None
x_vals = None
y_vals = None
kde = None

# 데이터 및 KDE 로드 함수
def load_data_and_compute_kde():
    global ratings_df, x_vals, y_vals, kde
    try:
        ratings_df = pd.read_csv("ratings_finished.csv", encoding="utf-8")
        kde = gaussian_kde(ratings_df["Rating"])
        x_vals = np.linspace(min(ratings_df["Rating"]), max(ratings_df["Rating"]), 1000)
        y_vals = kde(x_vals)
        logging.info("Data and KDE loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading data and computing KDE: {e}")

# 비동기 사용자 레이팅 검색 함수
async def search_user_rating(username: str):
    url = "https://solved.ac/api/v3/search/user"
    querystring = {"query": username}
    headers = {
        "x-solvedac-language": "",
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=querystring) as response:
            if response.status == 200:
                resp_json = await response.json()
                return resp_json["items"][0]["rating"]
            else:
                logging.error(f"Error fetching user rating: {response.status}")
                return None

# 데이터 수집 함수
def collect_data():
    global ratings_collecting, ratings
    while True:
        url = "https://solved.ac/api/v3/ranking/tier"
        requests_per_cycle = 300
        entries_per_request = 50
        total_entries = 173942
        pages_to_retrieve = total_entries // entries_per_request + 1

        logging.info("Starting data collection...")
        for page in range(pages_to_retrieve):
            logging.info(f"Collecting page {page + 1} of {pages_to_retrieve}")
            if page > 0 and page % requests_per_cycle == 0:
                logging.info("Rate limit reached, waiting for 15 minutes...")
                df = pd.DataFrame(ratings if ratings else ratings_collecting, columns=["Rating"])
                df.to_csv("ratings.csv", encoding="utf-8", index=False)
                time.sleep(15 * 60)

            querystring = {"page": str(page + 1)}
            headers = {
                "x-solvedac-language": "",
                "Accept": "application/json",
            }
            response = requests.get(url, headers=headers, params=querystring)

            if response.status_code == 200:
                items = response.json().get("items", [])
                for item in items:
                    ratings_collecting.append(item["rating"])
            else:
                logging.error("Error during data collection: ", response.status_code)
                df = pd.DataFrame(ratings if ratings else ratings_collecting, columns=["Rating"])
                df.to_csv("ratings.csv", encoding="utf-8", index=False)
                time.sleep(15 * 60)
                response = requests.get(url, headers=headers, params=querystring)

                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for item in items:
                        ratings_collecting.append(item["rating"])
        ratings = ratings_collecting
        df = pd.DataFrame(ratings if ratings else ratings_collecting, columns=["Rating"])
        df.to_csv("ratings.csv", encoding="utf-8", index=False)
        load_data_and_compute_kde()
        time.sleep(COLLECTION_INTERVAL)

@app.get("/")
async def test():
    return {"message": "Hello, World!"}

# 이미지 제공 엔드포인트
@app.get("/user-rating-image")
async def user_rating_image(
    name: str = Query("wlgns06"),
    fill: bool = Query(True),
    color: str = Query("mediumseagreen"),
    outerbgcolor: str = Query("white"),
    innerbgcolor: str = Query("white"),
    pointcolor: str = Query("darkcyan"),
    textcolor: str = Query("teal"),
    size: str = Query("100")
):
    curr_rating = await search_user_rating(name)
    if curr_rating is None:
        return {"error": "User rating not found."}

    global x_vals, y_vals, kde

    if x_vals is None or y_vals is None or kde is None:
        load_data_and_compute_kde()

    y_at_currRating = kde(curr_rating)
    
    # KDE 시각화
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(outerbgcolor)
    ax.set_facecolor(innerbgcolor)

    if fill:
        ax.fill_between(x_vals, y_vals, color=color, alpha=0.3)
    
    ax.plot(x_vals, y_vals, color=color, linewidth=3, alpha=0.7)
    
    ax.scatter(curr_rating, y_at_currRating, color=pointcolor, s=100, zorder=5, marker="o", edgecolor="black", linewidth=0.5)
    
    ax.set_title(f"Solved.ac Rating for @{name}", fontsize=20, fontweight="bold", color=textcolor)
    ax.get_yaxis().set_visible(False)
    
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=int(size))
    img.seek(0)
    plt.close()
    
    return StreamingResponse(img, media_type="image/png")

# 주기적인 데이터 수집 설정
COLLECTION_INTERVAL = 60 * 60 * 24
ratings_collecting = []
ratings = []

# 앱 시작 시 데이터 로드
load_data_and_compute_kde()

# 데이터 수집 스레드 시작
data_collection_thread = threading.Thread(target=collect_data, daemon=True)
data_collection_thread.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)