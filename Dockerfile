# 使用輕量級的 Python 映像檔
FROM python:3.10-slim

# 安裝 LilyPond
RUN apt-get update && apt-get install -y lilypond && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt 並安裝套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼到容器內
COPY . .

# 啟動 FastAPI 伺服器
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
