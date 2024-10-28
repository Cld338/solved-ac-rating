from flask import Flask, request, send_file
import requests
import matplotlib.pyplot as plt
from scipy.stats import percentileofscore, gaussian_kde
import numpy as np
import time
import io
import threading
import pandas as pd

app = Flask(__name__)

# 주기적인 데이터 수집 설정
COLLECTION_INTERVAL = 60*60*24  # 하루 주기로 분포 업데이트

ratings_collecting=[]
ratings=[]
def search_user_rating(username):
    
    url = "https://solved.ac/api/v3/search/user"
    querystring = {"query":username}
    headers = {
        "x-solvedac-language": "",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=querystring)
    return response.json()["items"][0]["rating"]

# 데이터 수집 함수
def collect_data():
    while True:
        url = "https://solved.ac/api/v3/ranking/tier"
        requests_per_cycle = 300  # 15분당 최대 300회
        entries_per_request = 50  # 한 페이지당 50개
        total_entries = 173942  # 총 예상 엔트리 수
        pages_to_retrieve = total_entries // entries_per_request + 1

        print("Starting data collection...")
        for page in range(pages_to_retrieve):
            print(page)
            if page > 0 and page % requests_per_cycle == 0:
                print("Rate limit reached, waiting for 15 minutes...")
                time.sleep(15 * 60)  # 15분 대기

            querystring = {"page": str(page + 1)}
            headers = {
                "x-solvedac-language": "",
                "Accept": "application/json",
            }
            print(f"Fetching page {page + 1} of {pages_to_retrieve}")

            response = requests.get(url, headers=headers, params=querystring)

            if response.status_code == 200:
                items = response.json().get("items", [])
                for item in items:
                    ratings_collecting.append(item["rating"])  # 각 사용자의 레이팅을 리스트에 추가
            else:
                print("데이터 수집 중 오류 발생: ", response.status_code)
                break

        ratings = ratings_collecting
        # 주기 대기 후 재수집
        time.sleep(COLLECTION_INTERVAL)



# 이미지 제공 엔드포인트
@app.route('/user-rating-image')
def user_rating_image():
    # URL 파라미터에서 사용자 ID와 현재 레이팅 값 추출
    user_id = request.args.get("name", "wlgns06")
    curr_rating = search_user_rating(user_id)
    fill = request.args.get("fill", "true").lower() == "true"

    # 색상 파라미터 받기 (기본 색상 설정)
    color = request.args.get("color", "mediumseagreen")
    outer_bg_color = request.args.get("outerBgColor", "white")
    inner_bg_color = request.args.get("innerBgColor", "white")
    point_color = request.args.get("pointColor", "darkcyan")
    text_color = request.args.get("textColor", "teal")

    # 데이터를 로드
    df = pd.DataFrame(ratings, columns=["Rating"])
    
    # 사용자 퍼센타일 계산
    # user_percentile = 100 - percentileofscore(df["Rating"], curr_rating)
    
    # 커널 밀도 함수 계산
    kde = gaussian_kde(df["Rating"])
    x_vals = np.linspace(min(df["Rating"]), max(df["Rating"]), 1000)
    y_vals = kde(x_vals)
    
    # currRating에 해당하는 y값 계산
    y_at_currRating = kde(curr_rating)
    
    # KDE 시각화
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(outer_bg_color)  # 그래프 바깥 배경색
    ax.set_facecolor(inner_bg_color)  # 그래프 내부 배경색

    # fill이 True인 경우 그래프 아래를 채움
    if fill:
        ax.fill_between(x_vals, y_vals, color=color, alpha=0.3)
    
    ax.plot(x_vals, y_vals, color=color, linewidth=3, alpha=0.7)
    
    # 사용자 레이팅 위치 표시
    ax.scatter(curr_rating, y_at_currRating, color=point_color, s=100, zorder=5, marker="o", edgecolor="black", linewidth=0.5)
    # ax.text(curr_rating, y_at_currRating + , f"{user_percentile:.2f} %", color=text_color, 
    #         ha="center", fontsize=12, fontweight="bold", style='italic')

    # percentiles = [10, 30, 50, 70]
    # percentile_ratings = [np.percentile(df["Rating"], 100 - p) for p in percentiles]

    # # 각 퍼센타일에 해당하는 위치에 수직선 추가
    # for perc, rating in zip(percentiles, percentile_ratings):
    #     ax.axvline(rating, color="grey", linestyle="--", linewidth=1.2)
    #     ax.text(rating, 0, f"Top {perc}%", color="grey", 
    #             ha="center", fontsize=10, fontweight="semibold", style='italic')

    
    # 그래프 제목에 사용자 ID 포함
    ax.set_title(f"Solved.ac Rating for {user_id}", fontsize=20, fontweight="bold", color=text_color)
    # ax.set_xlabel("Rating", fontsize=16, color=text_color, fontweight="semibold")
    
    # 축 숨기기
    ax.get_yaxis().set_visible(False)

    
    # 그래프 바깥 여백 줄이기
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

    # 이미지를 BytesIO 객체에 저장
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
    img.seek(0)
    plt.close()
    
    # 이미지를 파일로 반환
    return send_file(img, mimetype='image/png')

@app.route('/user-rating-image')
def test():
    return "Hello, World!"

if __name__ == '__main__':
    # 데이터 수집 스레드를 데몬 스레드로 설정하고 시작
    data_collection_thread = threading.Thread(target=collect_data, daemon=True)
    data_collection_thread.start()
    # Flask 서버 시작
    app.run(__name__)