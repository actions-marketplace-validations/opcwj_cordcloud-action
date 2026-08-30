FROM python:3-slim

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt

# 安装 playwright 和浏览器
RUN pip install playwright
# 设置浏览器安装路径并安装
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium --with-deps

COPY . /app

ENV PYTHONPATH /app
CMD ["python", "/app/main.py"]