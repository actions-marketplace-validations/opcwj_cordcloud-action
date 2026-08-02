#!/usr/bin/env python3
"""
使用 mitmproxy 或类似工具记录网络请求
这个脚本会拦截 HTTP 请求并显示详细信息
"""

import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs

PORT = 8888

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        print("\n" + "=" * 60)
        print(f"POST {self.path}")
        print("=" * 60)
        print("Headers:")
        for header, value in self.headers.items():
            print(f"  {header}: {value}")
        
        print("\nRequest Body:")
        try:
            # 尝试解析为 JSON
            body_json = json.loads(post_data)
            print(json.dumps(body_json, indent=2))
        except:
            # 尝试解析为表单数据
            try:
                body_str = post_data.decode('utf-8')
                params = parse_qs(body_str)
                for key, values in params.items():
                    print(f"  {key}: {values[0] if values else ''}")
            except:
                print(post_data)
        
        # 不转发请求，只记录
        self.send_response(404)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass  # 禁止默认日志

print("提示：这个脚本只用于记录，不实际转发请求")
print("实际的网络请求信息，请使用浏览器开发者工具 → Network 标签来查看")
print("\n建议步骤：")
print("1. 打开浏览器 F12")
print("2. 切换到 Network 标签")
print("3. 手动登录")
print("4. 找到最后的 /auth/login POST 请求")
print("5. 展开查看 'Request' 标签中的 'Payload'")
print("6. 截图或复制所有参数和它们的值")
print("\n然后告诉我所有的参数！")
