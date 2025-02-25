import time
import redis


class RateWindowLimiter:
    """
    支持滑动窗口速率限制和API密钥轮询的限流器。
    """

    def __init__(self, api_key_limits, redis_client):
        if not api_key_limits:
            raise ValueError("至少需要提供一个API密钥及其限制")
        self.api_key_limits = api_key_limits
        self.redis = redis_client
        self.lua_script = self._load_lua_script()

    def _load_lua_script(self):
        return """
            local current_time = tonumber(ARGV[1])
            local rpm_max = tonumber(ARGV[2])
            local rpm_window = tonumber(ARGV[3])
            local tpm_max = tonumber(ARGV[4])
            local tpm_window = tonumber(ARGV[5])
            local tpd_max = tonumber(ARGV[6])
            local tpd_window = tonumber(ARGV[7])

            local rpm_key = KEYS[1]
            local tpm_key = KEYS[2]
            local tpd_key = KEYS[3]

            local function check_limit(key, max_tokens, window)
                redis.call('zremrangebyscore', key, 0, current_time - window)
                local count = redis.call('zcard', key)
                if count >= max_tokens then
                    local earliest = redis.call('zrange', key, 0, 0, 'WITHSCORES')
                    if #earliest > 0 then
                        local earliest_time = tonumber(earliest[2])
                        return earliest_time + window - current_time
                    else
                        return 0
                    end
                else
                    return -1
                end
            end

            local rpm_wait = check_limit(rpm_key, rpm_max, rpm_window)
            local tpm_wait = check_limit(tpm_key, tpm_max, tpm_window)
            local tpd_wait = check_limit(tpd_key, tpd_max, tpd_window)

            local max_wait = 0
            local allowed = true

            if rpm_wait >= 0 then
                max_wait = math.max(max_wait, rpm_wait)
                allowed = false
            end
            if tpm_wait >= 0 then
                max_wait = math.max(max_wait, tpm_wait)
                allowed = false
            end
            if tpd_wait >= 0 then
                max_wait = math.max(max_wait, tpd_wait)
                allowed = false
            end

            if allowed then
                redis.call('zadd', rpm_key, current_time, current_time)
                redis.call('expire', rpm_key, rpm_window)
                redis.call('zadd', tpm_key, current_time, current_time)
                redis.call('expire', tpm_key, tpm_window)
                redis.call('zadd', tpd_key, current_time, current_time)
                redis.call('expire', tpd_key, tpd_window)
                return {1, 0}
            else
                return {0, tostring(max_wait)}
            end
        """

    def _check_key_limits(self, api_key):
        limits = self.api_key_limits.get(api_key)
        if not limits:
            raise ValueError(f"未找到API密钥 {api_key} 的限制配置")

        rpm_key = f"rate_limit:{api_key}:rpm"
        tpm_key = f"rate_limit:{api_key}:tpm"
        tpd_key = f"rate_limit:{api_key}:tpd"

        current_time = time.time()
        try:
            result = self.redis.eval(
                self.lua_script,
                3,
                rpm_key,
                tpm_key,
                tpd_key,
                current_time,
                limits['max_rpm'],
                10,
                limits['max_tpm'],
                3600,
                limits['max_tpd'],
                86400,
            )
        except redis.exceptions.ResponseError as e:
            print(f"Lua脚本错误: {e}")
            return False, 0

        allowed = result[0] == 1 if result else False
        wait_time = float(result[1]) if result and len(result) > 1 else 0
        return allowed, wait_time

    def acquire(self):
        index_key = "rate_limit:key_index"
        total_keys = len(self.api_key_limits)
        if total_keys == 0:
            raise ValueError("无可用API密钥")

        current_index = self.redis.get(index_key)
        if current_index is None:
            current_index = 0
        else:
            current_index = int(current_index)

        api_keys = list(self.api_key_limits.keys())
        min_wait = float('inf')
        selected = False

        for i in range(total_keys):
            idx = (current_index + i) % total_keys
            api_key = api_keys[idx]
            allowed, wait_time = self._check_key_limits(api_key)
            if allowed:
                self.redis.set(index_key, idx)
                return True, 0, api_key
            min_wait = min(min_wait, wait_time)

        # 如果没有可用的密钥，更新索引以尝试下一个密钥
        self.redis.set(index_key, (current_index + 1) % total_keys)
        return False, min_wait, ""


# 初始化Redis客户端
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# 创建限流器（示例参数）
api_key_limits = {
    "api_key_1": {"max_rpm": 2, "max_tpm": 5000, "max_tpd": 100000},
    "api_key_2": {"max_rpm": 3, "max_tpm": 6000, "max_tpd": 120000},
    "api_key_3": {"max_rpm": 4, "max_tpm": 7000, "max_tpd": 140000},
}
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
