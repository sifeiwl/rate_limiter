# Rate Limiter

Rate Limiter 是一个用于管理 API 密钥使用的限流库，支持滑动窗口速率限制。

## 特性

- 支持每个 API 密钥的自定义速率限制
- 使用 Redis 作为后端存储
- 提供简单的接口来获取可用的 API 密钥

## 安装

首先，确保你已经安装了 Python 和 Redis。然后，你可以通过以下命令安装依赖：

```bash
pip install -r requirements.txt
```

## 使用说明

以下是一个简单的使用示例：

```python
from rate_limiter import RateWindowLimiter

api_key_limits = {
    "api_key_1": {"max_rpm": 2, "max_tpm": 5000, "max_tpd": 100000},
    "api_key_2": {"max_rpm": 3, "max_tpm": 6000, "max_tpd": 120000},
    "api_key_3": {"max_rpm": 4, "max_tpm": 7000, "max_tpd": 140000},    
}

# 初始化Redis客户端
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# 创建限流器
rate_limiter = RateWindowLimiter(api_key_limits=api_key_limits, redis_client=redis_client)

# 模拟请求
for _ in range(15):
    allowed, wait_time, api_key = rate_limiter.acquire()
    if allowed:
        print(f"请求成功，使用API密钥: {api_key}")
        # 执行API调用...
    else:
        print(f"需等待 {wait_time:.2f} 秒后重试，API密钥: {api_key}")
        time.sleep(wait_time)
```

## 贡献

欢迎贡献代码！请 fork 本仓库并提交 pull request。

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。