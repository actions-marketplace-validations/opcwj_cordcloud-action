import re
from typing import Tuple

import requests
import urllib3

urllib3.disable_warnings()


class Action:
    def __init__(self, email: str, passwd: str, code: str = '', host: str = 'cordcloud.us'):
        self.email = email
        self.passwd = passwd
        self.code = code
        self.host = host.replace('https://', '').replace('http://', '').strip()
        self.session = requests.session()
        self.timeout = 6

    def format_url(self, path) -> str:
        return f'https://{self.host}/{path}'


    def login(self) -> dict:
        login_url = self.format_url('auth/login')

        # 1. 确保请求头带有极简的浏览器标识和 Referer（极其关键！）
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': login_url
        })

        # 2. 先 GET 访问登录页，利用同一个 self.session 自动保存 Cookie
        login_page_res = self.session.get(login_url, timeout=self.timeout, verify=False)

        # 3. 提取 CSRF Token（适配多种常见的 HTML 标签写法）
        html_text = login_page_res.text
        token_match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text) or \
                      re.search(r'csrf_token\s*=\s*["\']([^"\']+)["\']', html_text) or \
                      re.search(r'data-csrf=["\']([^"\']+)["\']', html_text)

        form_data = {
            'email': self.email,
            'passwd': self.passwd,
            'code': self.code
        }

        # 4. 如果提取到了 csrf_token，填入参数中
        if token_match:
            form_data['csrf_token'] = token_match.group(1)
            # 部分 SSR 面板后端接受的是 csrf_token 或 token，这里建议保持 csrf_token

        # 5. 用同一个 self.session 提交 POST 请求（此时带上了第一步获得的 Cookie 和 Token）
        return self.session.post(login_url, data=form_data, timeout=self.timeout, verify=False).json()

    def check_in(self) -> dict:
        check_in_url = self.format_url('user/checkin')
        return self.session.post(check_in_url, timeout=self.timeout, verify=False).json()

    def info(self) -> Tuple:
        user_url = self.format_url('user')
        html = self.session.get(user_url, verify=False).text
        today_used = re.search('<span class="traffic-info">今日已用</span>(.*?)<code class="card-tag tag-red">(.*?)</code>',
                               html,
                               re.S)
        total_used = re.search(
            '<span class="traffic-info">过去已用</span>(.*?)<code class="card-tag tag-orange">(.*?)</code>',
            html, re.S)
        rest = re.search(
            '<span class="traffic-info">剩余流量</span>(.*?)<code class="card-tag tag-green" id="remain">(.*?)</code>',
            html, re.S)
        if today_used and total_used and rest:
            return today_used.group(2), total_used.group(2), rest.group(2)
        return ()

    def run(self):
        self.login()
        self.check_in()
        self.info()
