import io
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple, List
import os

# 외부 라이브러리
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
import aiohttp
import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde

# Matplotlib 설정
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.path as mpath
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

# 폰트 설정 (시스템에 설치된 폰트에 맞게 수정 필요)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Pretendard', 'Inter', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Arial', 'sans-serif']
plt.rcParams['svg.fonttype'] = 'none'

# ----------------------------------------------------------------
# 1. 설정 및 상수
# ----------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 파일 경로 설정
RATING_DATA_FILE = "ratings_finished.csv" # API 서빙용 (완성된 데이터)
TEMP_DATA_FILE = "ratings_temp.csv"       # 수집용 (임시 데이터)

# 데이터 수집 설정
API_URL = "https://solved.ac/api/v3/ranking/tier"
ENTRIES_PER_REQUEST = 50
TOTAL_ENTRIES_ESTIMATE = 175000 
PAGES = TOTAL_ENTRIES_ESTIMATE // ENTRIES_PER_REQUEST + 1
REQUESTS_PER_CYCLE = 150        # 150회 요청 후 휴식
WAIT_TIME_LIMIT = 60 * 60       # 레이트 리밋 휴식 (60분)
COLLECTION_INTERVAL = 24 * 60 * 60 # 24시간 (수집 완료 후 대기 시간)

TIER_COLORS = [
    (0, "#9D4900"), (400, "#38546E"), (800, "#D28500"),
    (1600, "#00C78B"), (2200, "#00B4FC"), (2700, "#FF0062"), (3000, "#B491FF"),
]

app = FastAPI()

# ----------------------------------------------------------------
# 2. 데이터 수집 로직 (안전한 파일 교체 방식 적용)
# ----------------------------------------------------------------
async def collect_ranking_data():
    """Solved.ac 전체 유저 랭킹 데이터를 비동기로 수집합니다."""
    ratings = []
    logging.info(f"🚀 [Collector] 데이터 수집 시작... (총 {PAGES} 페이지 예상)")

    async with aiohttp.ClientSession() as session:
        for page in range(1, PAGES + 1):
            # 1. 레이트 리밋 휴식 로직
            if page > 1 and page % REQUESTS_PER_CYCLE == 0:
                logging.info(f"☕ [Collector] 레이트 리밋 방지를 위해 {WAIT_TIME_LIMIT/60}분간 대기합니다...")
                
                # 중간 저장 (임시 파일에 저장)
                if ratings:
                    pd.DataFrame(ratings, columns=["Rating"]).to_csv(TEMP_DATA_FILE, index=False)
                    logging.info(f"💾 [Collector] 임시 파일 저장 완료 ({len(ratings)}명)")
                
                await asyncio.sleep(WAIT_TIME_LIMIT)

            # 2. API 요청
            try:
                async with session.get(API_URL, params={"page": page}, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        if not items:
                            logging.info(f"⚠️ [Collector] 페이지 {page}에 데이터가 없어 조기 종료합니다.")
                            break
                        
                        for item in items:
                            ratings.append(item["rating"])
                            
                    elif response.status == 429:
                        logging.warning(f"⚠️ [Collector] Too Many Requests! 1분 대기 후 재시도...")
                        await asyncio.sleep(60)
                        continue
                    else:
                        logging.error(f"❌ [Collector] Error on page {page}: {response.status}")
                        
            except Exception as e:
                logging.error(f"❌ [Collector] Exception on page {page}: {e}")
                await asyncio.sleep(5)

    # 3. 최종 저장 및 파일 교체 (Atomic Swap)
    if ratings:
        try:
            # 1) 데이터를 DataFrame으로 변환
            df = pd.DataFrame(ratings, columns=["Rating"])
            
            # 2) 임시 파일에 전체 데이터 쓰기
            df.to_csv(TEMP_DATA_FILE, index=False)
            logging.info(f"💾 [Collector] 임시 파일 작성 완료. 파일 교체를 시도합니다.")

            # 3) 기존 파일(RATING_DATA_FILE)을 임시 파일로 교체 (OS 레벨에서 안전함)
            if os.path.exists(TEMP_DATA_FILE):
                os.replace(TEMP_DATA_FILE, RATING_DATA_FILE)
                logging.info(f"✅ [Collector] 파일 교체 완료! '{RATING_DATA_FILE}' 업데이트됨. (총 {len(df)}명)")
                return True
            
        except Exception as e:
            logging.error(f"❌ [Collector] 파일 저장/교체 중 오류 발생: {e}")
            return False
    else:
        logging.warning("⚠️ [Collector] 수집된 데이터가 없습니다.")
        return False

async def background_collector(data_manager_instance):
    """백그라운드에서 주기적으로 수집을 수행하는 태스크"""
    while True:
        try:
            # 1. 데이터 수집 수행
            success = await collect_ranking_data()
            
            # 2. 수집 성공 시 메모리에 데이터 갱신
            if success:
                data_manager_instance.load_data()
                logging.info("[Collector] 인메모리 데이터 갱신 완료.")

            # 3. 다음 주기까지 대기
            logging.info(f"💤 [Collector] 다음 수집까지 {COLLECTION_INTERVAL/3600}시간 대기합니다.")
            await asyncio.sleep(COLLECTION_INTERVAL)

        except asyncio.CancelledError:
            logging.info("[Collector] 수집 태스크가 취소되었습니다.")
            break
        except Exception as e:
            logging.error(f"❌ [Collector] 치명적 오류 발생: {e}")
            await asyncio.sleep(3600) # 에러 발생 시 1시간 뒤 재시도

# ----------------------------------------------------------------
# 3. 데이터 관리 클래스
# ----------------------------------------------------------------
class DataManager:
    def __init__(self):
        self.ratings_df: Optional[pd.DataFrame] = None
        self.cache: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def load_data(self):
        try:
            if not os.path.exists(RATING_DATA_FILE):
                logging.warning(f"File {RATING_DATA_FILE} not found. Using dummy data until collection finishes.")
                # 파일이 없으면 더미 데이터 생성 (서버 시작 시 에러 방지)
                sample_ratings = np.random.normal(1500, 500, 1000).astype(int)
                sample_ratings = sample_ratings[(sample_ratings >= 0) & (sample_ratings <= 3500)]
                self.ratings_df = pd.DataFrame(sample_ratings, columns=["Rating"])
            else:
                self.ratings_df = pd.read_csv(RATING_DATA_FILE, encoding="utf-8")
                self.update_cache() # 데이터 로드 시 캐시 초기화
                logging.info(f"📂 [DataManager] 데이터 로드 완료: {len(self.ratings_df)} rows")
        except Exception as e:
            logging.error(f"Failed to load data: {e}")

    def update_cache(self):
        self.cache.clear()
        if self.ratings_df is None or self.ratings_df.empty: return
        # 미리 기본 설정(scott)으로 KDE 계산해두기
        self.get_distribution_data("kde", "scott")

    def get_distribution_data(self, plot_type: str, bw_method: str) -> Dict[str, Any]:
        key = (plot_type, bw_method)
        if key in self.cache: return self.cache[key]
        
        df = self.ratings_df
        if plot_type == "kde":
            kde_obj = gaussian_kde(df["Rating"], bw_method=bw_method)
            x_min, x_max = df["Rating"].min(), df["Rating"].max()
            x_vals = np.linspace(x_min, x_max, 1000)
            y_vals = kde_obj(x_vals)
            data = {"type": "kde", "kde_obj": kde_obj, "x_vals": x_vals, "y_vals": y_vals}
        else:
            counts, bins = np.histogram(df["Rating"], bins=60, density=True)
            bin_centers = (bins[:-1] + bins[1:]) / 2
            data = {"type": "histogram", "counts": counts, "bins": bins, "bin_centers": bin_centers}
        
        self.cache[key] = data
        return data

    def get_percentile(self, rating: int) -> float:
        if self.ratings_df is None: return 0.0
        return (self.ratings_df["Rating"] <= rating).mean() * 100

data_manager = DataManager()

# ----------------------------------------------------------------
# 4. API 유틸리티
# ----------------------------------------------------------------
async def search_user_rating(username: str) -> Optional[int]:
    url = "https://solved.ac/api/v3/search/user"
    querystring = {"query": username}
    headers = {"x-solvedac-language": "", "Accept": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=querystring) as response:
                if response.status == 200:
                    resp_json = await response.json()
                    if "items" in resp_json and len(resp_json["items"]) > 0:
                        return resp_json["items"][0]["rating"]
                    return None
                else:
                    return None
    except Exception:
        return None

# ----------------------------------------------------------------
# 5. 뱃지 그리기
# ----------------------------------------------------------------
class BadgeDrawer:
    THEMES = {
        "light": {"bg": "#ffffff", "border": "#e1e4e8", "text_main": "#24292f", "text_sub": "#57606a", "accent": "#0969da"},
        "dark": {"bg": "#0d1117", "border": "#30363d", "text_main": "#c9d1d9", "text_sub": "#8b949e", "accent": "#58a6ff"},
        "emerald": {"bg": "#041C16", "border": "#073327", "text_main": "#e5e7eb", "text_sub": "#34D399", "accent": "#10B981"},
    }

    @staticmethod
    def get_tier_color(rating: int) -> str:
        color = TIER_COLORS[0][1]
        for threshold, code in TIER_COLORS:
            if rating >= threshold: color = code
        return color

    @staticmethod
    def get_rounded_rect_path(x, y, w, h, r):
        k = r * 0.55228475
        verts = [
            (x + r, y), (x + w - r, y), (x + w - k, y), (x + w, y + k),
            (x + w, y + r), (x + w, y + h - r), (x + w, y + h - k), (x + w - k, y + h),
            (x + w - r, y + h), (x + r, y + h), (x + k, y + h), (x, y + h - k),
            (x, y + h - r), (x, y + r), (x, y + k), (x + k, y),
            (x + r, y), (x + r, y),
        ]
        codes = [
            mpath.Path.MOVETO, mpath.Path.LINETO,
            mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4,
            mpath.Path.LINETO,
            mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4,
            mpath.Path.LINETO,
            mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4,
            mpath.Path.LINETO,
            mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4,
            mpath.Path.CLOSEPOLY,
        ]
        return mpath.Path(verts, codes)

    @staticmethod
    def draw(
        username: str, rating: int, percentile: float, data: Dict[str, Any], 
        theme_name: str, custom_color: Optional[str], 
        width_inch: float, height_inch: float, size_dpi: int, fmt: str
    ):
        t = BadgeDrawer.THEMES.get(theme_name, BadgeDrawer.THEMES["dark"])
        main_color = custom_color if custom_color else BadgeDrawer.get_tier_color(rating)

        fig = Figure(figsize=(width_inch, height_inch), dpi=size_dpi)
        fig.patch.set_alpha(0.0)
        canvas = FigureCanvasAgg(fig)

        # 배경 (Rounded Rect)
        ax_bg = fig.add_axes([0, 0, 1, 1])
        ax_bg.set_axis_off()
        
        pixel_w = width_inch * size_dpi
        pixel_h = height_inch * size_dpi
        ax_bg.set_xlim(0, pixel_w)
        ax_bg.set_ylim(0, pixel_h)

        linewidth = 2.0
        margin = (linewidth / 2) + 1.0 
        rect_w = pixel_w - (margin * 2)
        rect_h = pixel_h - (margin * 2)
        corner_radius = 30 

        rect_path = BadgeDrawer.get_rounded_rect_path(margin, margin, rect_w, rect_h, corner_radius)
        patch = mpatches.PathPatch(rect_path, facecolor=t["bg"], edgecolor=t["border"], linewidth=linewidth, transform=ax_bg.transData, clip_on=False, zorder=0)
        ax_bg.add_patch(patch)

        # 1. 그래프 그리기 (위치 조정됨: 0.35 -> 0.40 높이)
        ax_graph = fig.add_axes([0.05, 0.18, 0.9, 0.40]) 
        ax_graph.set_axis_off()

        if data["type"] == "kde":
            x, y = data["x_vals"], data["y_vals"]
            ax_graph.fill_between(x, y, color=main_color, alpha=0.15, zorder=1)
            ax_graph.plot(x, y, color=main_color, linewidth=2, zorder=2)
            
            kde_func = data["kde_obj"]
            y_curr = kde_func(rating)[0] if isinstance(kde_func(rating), np.ndarray) else kde_func(rating)
            
            ax_graph.axvline(x=rating, color=main_color, linestyle="--", alpha=0.6, linewidth=1.5, zorder=3)
            ax_graph.plot([rating, rating], [0, y_curr], color=main_color, linewidth=1.5, alpha=0.8, zorder=3)
            ax_graph.scatter(rating, y_curr, s=60, facecolor=t["bg"], edgecolor=main_color, linewidth=2.5, zorder=4)

        # 2. 텍스트 정보 (위치 조정됨)
        ax_txt = fig.add_axes([0, 0, 1, 1])
        ax_txt.set_axis_off()
        
        # Username
        ax_txt.text(0.06, 0.83, f"@{username}", transform=ax_txt.transAxes, fontsize=16, fontweight='bold', color=t["text_main"], va='center')
        
        # Tier Points
        ax_txt.text(0.06, 0.69, f"{rating:,} Tier Points", transform=ax_txt.transAxes, fontsize=11, fontweight='medium', color=main_color, va='center')
        
        # Rank Percentile
        rank_percent = 100 - percentile
        rank_text = f"Top {rank_percent:.1f}%"
        ax_txt.text(0.94, 0.83, rank_text, transform=ax_txt.transAxes, fontsize=20, fontweight='bold', color=t["text_main"], ha='right', va='center')
        
        # X축 라벨 (Min/Max)
        x_min, x_max = data["x_vals"].min(), data["x_vals"].max()
        ax_txt.text(0.06, 0.09, f"{int(x_min)}", transform=ax_txt.transAxes, fontsize=8, color=t["text_sub"], ha='left')
        ax_txt.text(0.94, 0.09, f"{int(x_max)}", transform=ax_txt.transAxes, fontsize=8, color=t["text_sub"], ha='right')
        
        buf = io.BytesIO()
        canvas.print_figure(buf, format=fmt, pad_inches=0, bbox_inches=None, facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf

# ----------------------------------------------------------------
# 6. 엔드포인트 및 실행
# ----------------------------------------------------------------
@app.on_event("startup")
async def startup():
    data_manager.load_data()
    # 서버 시작 시 백그라운드 수집기 실행
    asyncio.create_task(background_collector(data_manager))

@app.get("/user-rating-image")
async def get_badge(
    name: str = Query(..., description="Solved.ac Username"),
    theme: str = "dark",
    color: str = None,
    width: float = 4.0,
    height: float = 2.6,
    size_dpi: int = 100,
    format: str = "svg",
    plot_type: str = "kde"
):
    if data_manager.ratings_df is None: 
        data_manager.load_data()
    
    rating = await search_user_rating(name)
    if rating is None: rating = 0
    
    # 캐시된 KDE 데이터 사용 (스레드 블로킹 방지를 위해 to_thread 사용)
    dist_data = await asyncio.to_thread(data_manager.get_distribution_data, plot_type, "scott")
    percentile = data_manager.get_percentile(rating)

    img_buf = await asyncio.to_thread(
        BadgeDrawer.draw, name, rating, percentile, dist_data, theme, color, width, height, size_dpi, format
    )

    media_type = "image/svg+xml" if format == "svg" else "image/png"
    return StreamingResponse(img_buf, media_type=media_type)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)