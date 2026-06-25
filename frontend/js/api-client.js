/**
 * Urban Pulse API 客户端
 *
 * 增强能力：
 *  - AbortController 超时（默认 18s，可配）
 *  - 5xx/408/429 网络错误指数退避重试（默认 2 次）
 *  - GET 请求的内存响应缓存（默认 TTL 60s，最多 64 条）
 */

const API_BASE = "/api/v1";

class UrbanPulseAPI {
  constructor(baseUrl = API_BASE, options = {}) {
    this.baseUrl = baseUrl;
    this.timeoutMs = options.timeoutMs ?? 18000;
    this.retryMax = options.retryMax ?? 2;
    this.retryBackoffMs = options.retryBackoffMs ?? 600;
    // 仅对幂等 GET 重试；对 502/503/504/408/429 退避重试
    this.retryStatuses = new Set(options.retryStatuses ?? [502, 503, 504, 408, 429]);
    // 简单 LRU + TTL 缓存：仅缓存 GET
    this._cache = new Map();
    this._cacheTtlMs = options.cacheTtlMs ?? 60000;
    this._cacheMax = options.cacheMax ?? 64;
  }

  /** 清空 GET 响应缓存（用于显式失效，如刷新按钮） */
  clearCache() {
    this._cache.clear();
  }

  _cacheGet(key) {
    const entry = this._cache.get(key);
    if (!entry) return undefined;
    if (Date.now() - entry.t > this._cacheTtlMs) {
      this._cache.delete(key);
      return undefined;
    }
    // LRU：访问即重新插入保持最新顺序
    this._cache.delete(key);
    this._cache.set(key, entry);
    return entry.v;
  }

  _cacheSet(key, value) {
    if (this._cache.size >= this._cacheMax) {
      const oldest = this._cache.keys().next().value;
      this._cache.delete(oldest);
    }
    this._cache.set(key, { v: value, t: Date.now() });
  }

  async post(path, body) {
    return this._request("POST", path, body);
  }

  async get(path) {
    const cacheKey = `GET ${path}`;
    const cached = this._cacheGet(cacheKey);
    if (cached !== undefined) return cached;
    const value = await this._request("GET", path);
    this._cacheSet(cacheKey, value);
    return value;
  }

  /**
   * 统一请求入口：超时 + 重试
   * POST 不重试（非幂等），GET 对可重试状态码做指数退避重试。
   */
  async _request(method, path, body) {
    const url = `${this.baseUrl}${path}`;
    let lastError;
    const attempts = method === "GET" ? this.retryMax + 1 : 1;
    for (let attempt = 0; attempt < attempts; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeoutMs);
      try {
        const init = {
          method,
          headers: method === "POST" ? { "Content-Type": "application/json" } : undefined,
          body: method === "POST" ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        };
        const res = await fetch(url, init);
        if (!res.ok) {
          const errText = await res.text();
          const err = new Error(`API ${path} failed: ${errText}`);
          err.status = res.status;
          err.statusText = res.statusText;
          lastError = err;
          if (method === "GET" && this.retryStatuses.has(res.status) && attempt < attempts - 1) {
            await this._backoff(attempt);
            continue;
          }
          throw err;
        }
        return await res.json();
      } catch (e) {
        // 超时 / 网络中断：可重试
        if (e.name === "AbortError") {
          lastError = new Error(`API ${path} timeout after ${this.timeoutMs}ms`);
        } else {
          lastError = e;
        }
        const retryable = method === "GET" && (e.name === "AbortError" || e instanceof TypeError) && attempt < attempts - 1;
        if (retryable) {
          await this._backoff(attempt);
          continue;
        }
        throw lastError;
      } finally {
        clearTimeout(timer);
      }
    }
    throw lastError ?? new Error(`API ${path} failed`);
  }

  _backoff(attempt) {
    // 指数退避：base * 2^attempt，加少量抖动避免惊群
    const delay = this.retryBackoffMs * (2 ** attempt) + Math.floor(Math.random() * 100);
    return new Promise((resolve) => setTimeout(resolve, delay));
  }

  async vizProfile(data) {
    return this.post("/viz/profile", { data });
  }

  async vizRecommend(data) {
    return this.post("/viz/recommend", { data });
  }

  async vizRender(config, data) {
    return this.post("/viz/render", { config, data });
  }

  async vizAuto(data, maxCharts = 3) {
    return this.post("/viz/auto", { data, max_charts: maxCharts });
  }

  async listCities() {
    return this.get("/cities/list");
  }

  async getCityData(code, indicators = []) {
    return this.get(`/cities/${encodeURIComponent(code)}?indicators=${indicators.join(",")}`);
  }
}

window.UrbanPulseAPI = UrbanPulseAPI;
