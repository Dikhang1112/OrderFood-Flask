# Base image
FROM python:3.12-slim

# Set workdir
WORKDIR /app

# Cài đặt dependency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ project
COPY . .

# Set biến môi trường (nếu cần)
ENV PYTHONUNBUFFERED=1

# Run Flask
CMD ["flask", "--app", "OrderFood/index.py", "run", "--host=0.0.0.0", "--port=5000"]

