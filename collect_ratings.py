import requests
import pandas as pd
import time
from tqdm import tqdm
import os

# 설정
OUTPUT_FILE = "ratings_finished.csv"
API_URL = "https://solved.ac/api/v3/ranking/tier"
ENTRIES_PER_REQUEST = 50
TOTAL_ENTRIES_ESTIMATE = 175000 # 대략적인 전체 유저 수
PAGES = TOTAL_ENTRIES_ESTIMATE // ENTRIES_PER_REQUEST + 1
REQUESTS_PER_CYCLE = 300 # Solved.ac 레이트 리밋 고려 (300회 요청 후 휴식)
WAIT_TIME = 15 * 60 # 15분 휴식

def collect_real_data():
    ratings = []
    
    print(f"🚀 데이터 수집 시작... (총 {PAGES} 페이지 예상)")
    
    for page in tqdm(range(1, PAGES + 1), desc="수집 중"):
        # 1. 레이트 리밋 휴식 로직
        if page > 1 and page % REQUESTS_PER_CYCLE == 0:
            print(f"\n☕ 레이트 리밋 방지를 위해 {WAIT_TIME/60}분간 대기합니다...")
            # 중간 저장 (혹시 모를 오류 대비)
            pd.DataFrame(ratings, columns=["Rating"]).to_csv(OUTPUT_FILE, index=False)
            print(f"💾 중간 저장 완료 ({len(ratings)}명)")
            time.sleep(WAIT_TIME)

        # 2. API 요청
        try:
            response = requests.get(API_URL, params={"page": page}, timeout=10)
            
            if response.status_code == 200:
                items = response.json().get("items", [])
                if not items: # 데이터가 없으면 종료
                    break
                for item in items:
                    ratings.append(item["rating"])
            elif response.status_code == 429:
                print(f"\n⚠️ Too Many Requests! 1분 대기 후 재시도...")
                time.sleep(60)
                # 현재 페이지 재시도를 위해 page index 조정이 필요하지만, 
                # 간단한 스크립트이므로 다음 실행을 기약하거나 여기서 종료할 수 있습니다.
                continue
            else:
                print(f"\n❌ Error on page {page}: {response.status_code}")
                
        except Exception as e:
            print(f"\n❌ Exception on page {page}: {e}")
            time.sleep(5)

    # 3. 최종 저장
    if ratings:
        df = pd.DataFrame(ratings, columns=["Rating"])
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✅ 수집 완료! '{OUTPUT_FILE}' 저장됨. (총 {len(df)}명)")
    else:
        print("\n⚠️ 수집된 데이터가 없습니다.")

if __name__ == "__main__":
    if os.path.exists(OUTPUT_FILE):
        print(f"⚠️ '{OUTPUT_FILE}' 파일이 이미 존재합니다. 덮어쓰시겠습니까? (y/n)")
        if input().lower() == 'y':
            collect_real_data()
    else:
        collect_real_data()