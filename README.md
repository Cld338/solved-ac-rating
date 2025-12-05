# Solved.ac 레이팅 분포 배지

## 개요
 Solved.ac 사용자의 레이팅을 시각화하여 배지를 생성합니다. 전체 사용자 대비 특정 사용자의 위치를 보여주는 이미지(SVG 또는 PNG)로 제공합니다.
 
<img width="384" height="249" alt="image" src="https://github.com/user-attachments/assets/228a3763-1ce7-4028-85f8-22598b7188cd" />

### 의존성 패키지

다음의 Python 패키지가 필요합니다:

* `fastapi`
* `uvicorn`
* `aiohttp`
* `pandas`
* `numpy`
* `scipy`
* `matplotlib`

## 설치 방법

1. 저장소를 복제(Clone)합니다.
2. pip를 사용하여 필요한 의존성을 설치합니다:

```bash
pip install fastapi uvicorn aiohttp pandas numpy scipy matplotlib
```

## 애플리케이션 실행

서버를 시작하려면 Python 스크립트를 직접 실행합니다. 이 애플리케이션은 `uvicorn`을 ASGI 서버로 사용합니다.

```bash
python main.py
```

기본 설정으로 서버는 `0.0.0.0`의 `8000` 포트에서 수신 대기합니다.

* **초기화 동작**: 시스템 초기화 시 기존 레이팅 데이터(`ratings_finished.csv`)를 로드합니다. 파일이 존재하지 않는 경우, 임시 더미 데이터를 생성하여 서비스를 즉시 시작하고 백그라운드 수집기를 가동합니다.

## API 참조

### 사용자 레이팅 배지 조회

사용자의 레이팅 분포를 나타내는 생성된 이미지를 반환합니다.

**엔드포인트**
`GET /user-rating-image`

**파라미터**

| 파라미터 | 타입 | 필수 여부 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `name` | string | **예** | - | 조회할 Solved.ac 사용자 ID입니다. |
| `theme` | string | 아니요 | `dark` | 시각 테마입니다. 옵션: `light`, `dark`, `emerald`. |
| `color` | string | 아니요 | *자동* | 그래프 강조 색상(HEX 코드, 예: `#FF0000`)입니다. 기본값은 티어 색상입니다. |
| `width` | float | 아니요 | `4.0` | 이미지 너비(인치 단위)입니다. |
| `height` | float | 아니요 | `2.6` | 이미지 높이(인치 단위)입니다. |
| `size_dpi` | int | 아니요 | `100` | 해상도(DPI)입니다. |
| `format` | string | 아니요 | `svg` | 출력 형식입니다. 옵션: `svg`, `png`. |
| `plot_type`| string | 아니요 | `kde` | 시각화 방식입니다. 옵션: `kde`, `histogram`. |

**요청 예시**

```http
GET /user-rating-image?name=example_user&theme=dark&format=svg
```

**응답**

* `200 OK`: 이미지 파일 스트림을 반환합니다 (MIME 타입: `image/svg+xml` 또는 `image/png`).
* 사용자를 찾을 수 없거나 외부 API 호출 중 오류가 발생한 경우, 레이팅이 0인 배지를 반환합니다.

## 구성 (Configuration)

주요 설정 상수는 스크립트 상단에 정의되어 있으며 필요에 따라 수정할 수 있습니다:

* `RATING_DATA_FILE`: 활성 데이터셋 파일 경로입니다.
* `COLLECTION_INTERVAL`: 데이터 수집 주기(초 단위)입니다 (기본값: 24시간).
* `WAIT_TIME_LIMIT`: API 속도 제한 회복을 위한 대기 시간입니다 (기본값: 60분).
* `TIER_COLORS`: 레이팅 임계값에 따른 색상 코드 매핑입니다.

## 로깅
로그에는 타임스탬프, 심각도 수준 및 다음 메시지가 포함됩니다:
* 서버 시작 및 종료
* 데이터 수집 진행 상황 및 상태
* 파일 작업 (저장/로드/교체)
* API 요청 및 파일 입출력 오류 처리
