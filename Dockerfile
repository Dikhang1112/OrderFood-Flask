# Base image Python 3.12
FROM python:3.12-slim

# Cài đặt các thư viện hệ thống cần thiết
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục app
WORKDIR /app

# Copy file requirements trước (tối ưu cache)
COPY requirements.txt .

# Cài đặt Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code vào container
COPY . .

# Copy file .env
COPY .env .env

# Expose cổng Flask (5000) container chay 443
EXPOSE 5000

# Chạy Flask app
CMD ["python", "index.py"]
