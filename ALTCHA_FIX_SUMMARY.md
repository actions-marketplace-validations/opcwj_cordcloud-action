# CordCloud Action - Altcha 验证修复总结

## 问题诊断

原错误消息：
```
::error::[2026-08-02 16:23:19] CordCloud 帐号登录失败，错误信息：系统无法接受您的验证结果，请刷新页面后重试。
```

根本原因：Altcha（一个服务端集成的验证系统）验证失败。

## 关键发现

通过网络请求分析，发现实际登录请求中的 `altcha` 参数是 **Base64 编码的 JSON 对象**：

```
altcha = base64.b64encode({
  "algorithm": "SHA-256",
  "challenge": "...",
  "number": 57333,
  "salt": "...",
  "signature": "...",
  "took": 96
})
```

## Altcha 算法更正

### 之前的理解（错误）
- 认为需要找到一个数 N，使得 SHA256(salt+N) 的哈希值以多个 0 开头（leading zeros）
- 这是标准 PoW 验证，但不适用于 CordCloud

### 正确的算法
- 客户端需要找到一个数 N，使得 SHA256(salt + N) 的结果**精确等于**服务器返回的 `challenge`
- `signature` 字段由服务器提供，客户端不应修改
- `took` 字段记录求解耗时（毫秒）

## 实现修复

### 1. 修复 solve_altcha_challenge() 函数

```python
def solve_altcha_challenge(challenge: str, salt: str, algorithm: str = 'SHA-256', maxnumber: int = 100000) -> dict:
    """
    找到 number 使得 SHA256(salt + number) == challenge
    """
    import time
    start = time.time()
    
    for number in range(maxnumber):
        if algorithm.upper() == 'SHA-256':
            data = f"{salt}{number}".encode()
            result = hashlib.sha256(data).hexdigest()
            
            if result == challenge:  # 精确匹配，不是 leading zeros
                took = int((time.time() - start) * 1000)
                return {
                    'algorithm': algorithm,
                    'challenge': challenge,
                    'number': number,
                    'salt': salt,
                    'signature': '',  # 由服务器提供
                    'took': took
                }
```

### 2. 修复 login() 方法

关键变化：

1. **添加必需的请求头**
   ```python
   'X-Requested-With': 'XMLHttpRequest'
   ```

2. **Base64 编码 Altcha 参数**
   ```python
   altcha_encoded = base64.b64encode(
       json.dumps(altcha_json).encode()
   ).decode()
   ```

3. **正确的表单数据结构**
   - email
   - passwd
   - altcha (Base64 编码)
   - csrf_token
   - device_fingerprint (16 字节十六进制)
   - remember_me: 'week'
   - code (可选，两步验证码)

4. **使用服务器的 signature**
   ```python
   'signature': challenge_data.get('signature', '')
   ```

## 验证步骤

### 测试数据验证
使用用户提供的实际登录请求数据验证：

```python
salt = 'c6b3f407e509ddcd38b77626?expires=1785661782&'
challenge = 'ca77a97e3aa2b57d164da167ffc9215df9ddc3a9bf8615fb215c27f936ab212d'
number = 57333

# 验证
SHA256(salt+57333) == challenge  ✓ 正确
```

### 求解器测试
```
python -c "from app.action import solve_altcha_challenge; \
result = solve_altcha_challenge(challenge, salt); \
print(result['number'])"  # 输出: 57333 ✓
```

## 技术细节

| 项目 | 说明 |
|------|------|
| Algorithm | SHA-256 |
| Challenge | 服务器返回的 64 字符十六进制字符串 |
| Number | 我们求解出的整数（0-100000） |
| Salt | 服务器返回，包含 URL 参数（expires, etc） |
| Signature | 由服务器提供，用于验证 challenge 的有效性 |
| Took | 求解耗时（毫秒） |

## 重要说明

1. **Salt 格式**：Salt 通常以 `?expires=...&` 结尾，这是意图的一部分，不应删除
2. **Device Fingerprint**：生成为用户代理 + 邮箱的 SHA256 哈希的前 16 字符
3. **Remember Me**：设置为 'week' 以保持会话一周
4. **Signature**：这不是我们计算的，而是从 `/auth/altcha/challenge` 响应中获取的

## 文件更改

修改文件：`app/action.py`
- 第 1-4 行：添加 `import base64`
- 第 13-43 行：重写 `solve_altcha_challenge()` 函数
- 第 63-138 行：重写 `login()` 方法以包含 Base64 编码的 Altcha

## 下一步

1. 使用您的 CordCloud 凭证运行测试：
   ```bash
   export EMAIL="your-email@example.com"
   export PASSWORD="your-password"
   python test_login.py
   ```

2. 验证登录响应返回 `"ret": 1`（成功）

3. 如果仍然失败，检查：
   - 邮箱和密码是否正确
   - 网络连接是否正常
   - CordCloud 服务是否可用
