# Solved.ac Rating 

이 프로젝트는 Solved.ac의 사용자의 레이팅을 기반으로 분포 그래프를 생성하여 이미지를 반환하는 FastAPI 애플리케이션입니다. 이를 통해 사용자는 자신의 레이팅이 전체 사용자 분포에서 어느 위치에 있는지 시각적으로 확인할 수 있습니다.

**Sample Request:**

    GET /user-rating-image?name=wlgns06&size=100
    
    ![Solved.ac Rating](https://solved-ac-rating.run.goorm.site/user-rating-image?name=wlgns06&size=100)

![Solved.ac Rating](https://solved-ac-rating.run.goorm.site/user-rating-image?name=wlgns06&size=100)


| Params        | Default            | Description                       |
| --------------- | ----------------- | ---------------------------------------- |
| `name`          | `wlgns06`         | 레이팅을 조회할 Solved.ac 사용자명        |
| `fill`          | `True`            | 그래프 아래를 색으로 채울지 여부          |
| `color`         | `mediumseagreen`  | 그래프 선 및 채우기 색상                  |
| `outerbgcolor`  | `white`           | 이미지의 배경색                           |
| `innerbgcolor`  | `white`           | 그래프 영역의 배경색                      |
| `pointcolor`    | `darkcyan`        | 사용자 레이팅을 표시하는 포인트의 색상    |
| `textcolor`     | `teal`            | 제목 등의 텍스트 색상                     |
| `size`          | `100`             | 이미지의 DPI 설정                         |




## Functions
- **사용자 레이팅 조회**: 입력한 Solved.ac 사용자명의 레이팅을 조회합니다.
- **KDE 그래프 생성**: 전체 사용자 레이팅 데이터를 기반으로 KDE 그래프를 생성합니다.
- **이미지 반환**: 생성된 그래프에 사용자의 레이팅을 표시하여 이미지로 반환합니다.
- **주기적인 데이터 수집**: 백그라운드에서 별도의 스레드를 통해 사용자 레이팅 데이터를 주기적으로 수집하고 업데이트합니다.

## Requirements

- Python 3.7 이상
  - `fastapi`
  - `uvicorn`
  - `pandas`
  - `matplotlib`
  - `numpy`
  - `scipy`
  - `aiohttp`
  - `requests`

## Installation

1. **Clone Repository**

       git clone https://github.com/yourusername/solvedac-rating-image-generator.git
       cd solvedac-rating-image-generator

2. **Create venv**

       python -m venv venv
       source venv/bin/activate  # Windows의 경우: venv\Scripts\activate
       pip install -r requirements.txt

## Usage

    uvicorn app:app --host 0.0.0.0 --port 5000

또는 파이썬에서 실행:

    python app.py

## 사용 방법

웹 브라우저나 HTTP 클라이언트를 통해 다음 엔드포인트에 접근합니다:

    GET /user-rating-image




## Cautions

- **API 제한**: Solved.ac API의 호출 제한에 유의하세요. 과도한 요청 시 일시적으로 차단될 수 있습니다.
- **데이터 수집 주기**: `COLLECTION_INTERVAL` 변수를 통해 데이터 수집 주기를 설정할 수 있습니다. 기본값은 하루(60 * 60 * 24초)입니다.
- **데이터 저장**: 수집된 레이팅 데이터는 `ratings.csv` 파일에 저장되며, KDE 계산을 위해 사용됩니다.

## License

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참고하세요.
