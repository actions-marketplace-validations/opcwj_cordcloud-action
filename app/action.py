import re
import json
import hashlib
from typing import Tuple

import requests
import urllib3

urllib3.disable_warnings()


def solve_altcha_challenge(challenge: str, salt: str, algorithm: str = 'SHA-256', maxnumber: int = 100000) -> str:
    """
    解决 Altcha 工作量证明验证码
    正确算法：SHA256(salt + number)
    找到一个数字 N，使得 SHA256(salt + N) 的哈希有足够的前导零
    
    注意：由于 Altcha 可能有时间限制，此函数应尽快执行
    """
    # 尝试难度 1-4，快速找到任何解决方案
    for difficulty in range(1, 5):
        target_prefix = '0' * difficulty
        
        for number in range(maxnumber):
            if algorithm.upper() == 'SHA-256':
                data = f"{salt}{number}".encode()
                result = hashlib.sha256(data).hexdigest()
                
                if result.startswith(target_prefix):
                    return str(number)
    
    return str(0)


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

        # 1. 确保请求头带有浏览器标识
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': login_url
        })

        # 2. 获取登录页面
        login_page_res = self.session.get(login_url, timeout=self.timeout, verify=False)
        html_text = login_page_res.text
        
        # 3. 提取 CSRF Token
        token_match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text) or \
                      re.search(r'csrf_token\s*=\s*["\']([^"\']+)["\']', html_text) or \
                      re.search(r'data-csrf=["\']([^"\']+)["\']', html_text)

        # 4. 获取 Altcha Challenge 并求解
        challenge_url = self.format_url('auth/altcha/challenge')
        challenge_res = self.session.get(challenge_url, timeout=self.timeout, verify=False)
        altcha_data = challenge_res.json()
        
        altcha_solution = solve_altcha_challenge(
            altcha_data.get('challenge', ''),
            altcha_data.get('salt', ''),
            altcha_data.get('algorithm', 'SHA-256'),
            altcha_data.get('maxnumber', 100000)
        )

        # 5. 构建登录表单数据
        # 根据网页JavaScript代码，应该提交以下字段：
        # - email
        # - passwd
        # - code (两步验证码)
        # - csrf_token
        # - altcha (需要是正确的格式)
        # - remember_me (可选)
        # - device_fingerprint (需要生成)
        
        form_data = {
            'email': self.email,
            'passwd': self.passwd,
            'code': self.code,
        }

        # 6. 添加 CSRF Token
        if token_match:
            form_data['csrf_token'] = token_match.group(1)

        # 7. 添加设备指纹（简单生成）
        device_id = hashlib.sha256(
            f"{self.session.headers['User-Agent']}{self.email}".encode()
        ).hexdigest()[:32]
        form_data['device_fingerprint'] = device_id

        # 8. 尝试方式1：直接使用 Altcha challenge 对象作为 JSON
        form_data['altcha'] = json.dumps({
            'algorithm': altcha_data.get('algorithm'),
            'challenge': altcha_data.get('challenge'),
            'number': int(altcha_solution),
            'salt': altcha_data.get('salt'),
            'signature': altcha_data.get('signature')
        })

        # 9. 提交登录请求
        response = self.session.post(login_url, data=form_data, timeout=self.timeout, verify=False)
        result = response.json()
        
        return result

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
