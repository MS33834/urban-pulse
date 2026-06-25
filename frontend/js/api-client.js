/**
 * Urban Pulse API 客户端
 */

const API_BASE = "/api/v1";

class UrbanPulseAPI {
  constructor(baseUrl = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async post(path, body) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`API ${path} failed: ${err}`);
    }
    return res.json();
  }

  async get(path) {
    const res = await fetch(`${this.baseUrl}${path}`);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`API ${path} failed: ${err}`);
    }
    return res.json();
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
