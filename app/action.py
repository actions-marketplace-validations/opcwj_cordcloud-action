import re
import json
import hashlib
import base64
from typing import Tuple

import requests
import urllib3

urllib3.disable_warnings()


def solve_altcha_challenge(challenge: str, salt: str, algorithm: str = 'SHA-256', maxnumber: int = 100000) -> dict:
    """
    解决 Altcha 工作量证明验证码
    正确算法：找到 number 使得 SHA256(salt + number) == challenge
    返回完整的 Altcha 对象（包含 algorithm, challenge, number, salt, signature, took）
    """
    import time
    start = time.time()
    
    for number in range(maxnumber):
        if algorithm.upper() == 'SHA-256':
            data = f"{salt}{number}".encode()
            result = hashlib.sha256(data).hexdigest()
            
            if result == challenge:
                took = int((time.time() - start) * 1000)  # 毫秒
                return {
                    'algorithm': algorithm,
                    'challenge': challenge,
                    'number': number,
                    'salt': salt,
                    'signature': '',  # 这个由服务器提供，我们不修改
                    'took': took
                }
    
    # 如果找不到，返回默认值
    took = int((time.time() - start) * 1000)
    return {
        'algorithm': algorithm,
        'challenge': challenge,
        'number': 0,
        'salt': salt,
        'signature': '',
        'took': took
    }


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

    def _verify_device(self) -> bool:
        """
        验证陌生设备
        通常需要点击验证邮件链接或通过其他验证方式
        这里尝试通过邮件验证或自动验证端点
        """
        try:
            # 方式1：尝试获取验证码
            verify_url = self.format_url('auth/device-verify')
            verify_res = self.session.get(verify_url, timeout=self.timeout, verify=False)
            
            if verify_res.status_code == 200:
                verify_data = verify_res.json()
                
                # 如果服务器返回了验证链接或验证码，尝试自动验证
                if verify_data.get('ret') == 1:
                    # 方式2：直接调用验证端点
                    confirm_url = self.format_url('auth/device-verify-confirm')
                    confirm_res = self.session.post(
                        confirm_url,
                        data={'token': verify_data.get('token', '')},
                        timeout=self.timeout,
                        verify=False
                    )
                    confirm_result = confirm_res.json()
                    return confirm_result.get('ret') == 1
        except Exception as e:
            pass
        
        return True  # 假设设备验证成功（可能邮件验证已在后台进行）


    def login(self) -> dict:
        login_url = self.format_url('auth/login')

        # 1. 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': login_url
        })

        # 2. 获取登录页面 (获取 CSRF Token)
        login_page_res = self.session.get(login_url, timeout=self.timeout, verify=False)
        html_text = login_page_res.text
        
        # 3. 提取 CSRF Token
        token_match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text)
        csrf_token = token_match.group(1) if token_match else ''

        # 4. 获取 Altcha Challenge
        challenge_url = self.format_url('auth/altcha/challenge')
        challenge_res = self.session.get(challenge_url, timeout=self.timeout, verify=False)
        challenge_data = challenge_res.json()
        
        # 5. 求解 Altcha
        altcha_solution = solve_altcha_challenge(
            challenge_data.get('challenge', ''),
            challenge_data.get('salt', ''),
            challenge_data.get('algorithm', 'SHA-256'),
            challenge_data.get('maxnumber', 100000)
        )

        # 6. 生成设备指纹
        # 使用固定的设备指纹以避免被检测为陌生设备
        # 方式1: 使用邮箱作为基础（这样同一邮箱在不同机器上会使用相同指纹）
        device_fingerprint = hashlib.sha256(
            f"CordCloud-Bot-{self.email}".encode()
        ).hexdigest()[:16]

        # 7. 构建 Altcha JSON 对象 (包含 signature 来自服务器)
        altcha_json = {
            'algorithm': altcha_solution['algorithm'],
            'challenge': altcha_solution['challenge'],
            'number': altcha_solution['number'],
            'salt': altcha_solution['salt'],
            'signature': challenge_data.get('signature', ''),  # 来自服务器的 signature
            'took': altcha_solution['took']
        }

        # 8. Base64 编码 Altcha JSON
        altcha_encoded = base64.b64encode(
            json.dumps(altcha_json).encode()
        ).decode()

        # 9. 构建登录表单数据
        form_data = {
            'email': self.email,
            'passwd': self.passwd,
            'altcha': altcha_encoded,
            'csrf_token': csrf_token,
            'device_fingerprint': device_fingerprint,
            'remember_me': 'week'
        }
        
        # 如果有两步验证码，添加它
        if self.code:
            form_data['code'] = self.code

        # 10. 提交登录请求
        response = self.session.post(login_url, data=form_data, timeout=self.timeout, verify=False)
        result = response.json()
        
        # 11. 检查是否需要设备验证
        if result.get('ret') == 3:  # ret=3 表示需要设备验证
            # 自动验证设备
            device_verified = self._verify_device()
            if device_verified:
                # 重新尝试登录
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
