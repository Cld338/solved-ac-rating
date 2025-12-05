# 1. 베이스 이미지 설정 (Python 3.10 slim 버전 사용)
FROM python:3.10-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 시스템 패키지 업데이트 및 한글 폰트(나눔폰트) 설치
# Matplotlib에서 한글이 깨지지 않게 하기 위해 필수입니다.
RUN apt-get update && apt-get install -y \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# 4. Matplotlib 캐시 삭제 (새로운 폰트 인식을 위해)
RUN rm -rf /root/.cache/matplotlib

# 5. 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 소스 코드 및 데이터 파일 복사
COPY . .

# 7. 포트 노출
EXPOSE 8000

# 8. 실행 명령어 (FastAPI 실행)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]