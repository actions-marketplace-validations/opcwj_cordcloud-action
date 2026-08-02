# CordCloud Action 登录问题诊断

## 当前状态

✅ **已完成：**
- 实现了 Altcha SHA256(salt+number) 求解算法
- 验证了算法的正确性（生成 4 个前导零的哈希）
- 提取了 CSRF Token
- 构建了登录表单参数

❌ **失败：**
- 登录返回："系统无法接受您的验证结果，请刷新页面后重试"

## 发现的关键信息

### 登录页面结构
```html
<form action="javascript:void(0);" method="POST" id="login-form">
    <input type="hidden" name="csrf_token" value="...">
    <input type="email" name="email" class="auth-form-input" ...>
    <input type="password" name="passwd" class="auth-form-input" ...>
    <input type="checkbox" name="remember_me" value="week" ...>
    <altcha-widget 
        id="altcha-widget"
        challengeurl="/auth/altcha/challenge"
        auto="onload"
        hidefooter
        hidelogo>
    </altcha-widget>
</form>
```

### JavaScript 登录处理
```javascript
$.ajax({
    type: "POST",
    url: location.pathname,  // 即 /auth/login
    data: {
        altcha: (function() {
            var altchaInput = document.querySelector('input[name="altcha"]');
            return altchaInput ? altchaInput.value : '';
        })(),
        code: ...,           // 两步验证码
        email: ...,
        passwd: ...,
        remember_me: ...,
        csrf_token: ...,
        device_fingerprint: ...  // 通过 FingerprintJS 生成
    }
})
```

## 关键发现

1. **altcha-widget 是一个 Web Component**
   - 它会自动从 `/auth/altcha/challenge` 获取验证码
   - 自动求解
   - 将结果放在 `input[name="altcha"]` 中

2. **altcha 字段值来自 `input[name="altcha"]`**
   - 这个值由 altcha-widget JavaScript 生成
   - 我们目前不知道确切的格式

3. **device_fingerprint 是必需的**
   - 通过 FingerprintJS 库生成
   - 不仅仅是简单的哈希

4. **form 使用 AJAX 提交**
   - POST 到 `/auth/login`
   - 返回 JSON 响应

## 需要的信息

要获得成功，我们需要知道：

1. **altcha-widget 生成的 `input[name="altcha"]` 值的确切格式**
   - 示例值是什么？
   - 它是 JSON、Base64、JWT、还是其他格式？

2. **确切的 device_fingerprint 格式**
   - 需要 FingerprintJS 库吗？
   - 还是简单的哈希就可以？

3. **成功登录时的完整参数**
   - 所有参数名称
   - 所有参数值
   - 顺序是否重要？

## 如何获取这些信息

### 方法1：浏览器开发者工具
1. F12 打开开发者工具
2. 切换到 **Network** 标签
3. 手动登录一次
4. 找到最后的 **POST /auth/login** 请求
5. 展开 **Request** 部分，查看 **Payload**
6. 截图或复制所有参数

### 方法2：检查浏览器 Console
1. F12 打开开发者工具
2. 切换到 **Console** 标签
3. 粘贴以下代码：
```javascript
// 检查 altcha 字段
var altchaInput = document.querySelector('input[name="altcha"]');
console.log('altcha value:', altchaInput ? altchaInput.value : 'NOT FOUND');

// 检查 device fingerprint
console.log('device_fingerprint:', typeof deviceFingerprint !== 'undefined' ? deviceFingerprint : 'NOT FOUND');

// 检查 widget 状态
var widget = document.querySelector('altcha-widget');
console.log('widget state:', widget ? widget.getAttribute('data-state') : 'NOT FOUND');
```

## 现有的尝试及结果

| 方案 | altcha 格式 | 结果 |
|------|-----------|------|
| 方案1 | JSON 字符串 | ❌ "系统无法接受您的验证结果" |
| 方案2 | 分开字段 `altcha[*]` | ❌ 500 服务器错误 |
| 方案3 | 纯数字 | ❌ "系统无法接受您的验证结果" |
| 方案4 | Base64 编码 | ❌ "系统无法接受您的验证结果" |

## 下一步

需要你提供成功登录时的**准确的网络请求详情**，才能继续修复代码。
