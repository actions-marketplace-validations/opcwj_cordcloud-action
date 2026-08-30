FROM python:3-slim

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt

# 安装 playwright 和浏览器
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . /app

ENV PYTHONPATH /app
CMD ["/app/main.py"]