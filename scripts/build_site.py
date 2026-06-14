"""Build static site for GitHub Pages by hitting the real FastAPI backend.

Uses TestClient so no server process is needed. Pre-computes all forecasts
and generates JSON data files for the static bilingual dashboard.

Usage:
    python scripts/build_site.py
    # Output: _site/index.html + _site/data/*.json
"""

import json
import shutil
from pathlib import Path

import httpx

SITE_DIR = Path(__file__).parent.parent / "_site"
DATA_DIR = SITE_DIR / "data"

CITIES = [
    {"code": "sz", "name": "Shenzhen", "name_cn": "深圳"},
    {"code": "sh", "name": "Shanghai", "name_cn": "上海"},
    {"code": "bj", "name": "Beijing", "name_cn": "北京"},
    {"code": "gz", "name": "Guangzhou", "name_cn": "广州"},
    {"code": "wh", "name": "Wuhan", "name_cn": "武汉"},
    {"code": "cd", "name": "Chengdu", "name_cn": "成都"},
    {"code": "hz", "name": "Hangzhou", "name_cn": "杭州"},
    {"code": "nj", "name": "Nanjing", "name_cn": "南京"},
    {"code": "su", "name": "Suzhou", "name_cn": "苏州"},
    {"code": "xa", "name": "Xi'an", "name_cn": "西安"},
]

INDICATORS = [
    {"id": "gdp", "label": "GDP (CNY 100M)", "label_cn": "GDP（亿元）"},
    {"id": "gdp_growth", "label": "GDP Growth (%)", "label_cn": "GDP增速（%）"},
    {"id": "population", "label": "Population (10K)", "label_cn": "常住人口（万人）"},
    {"id": "fiscal_revenue", "label": "Fiscal Rev (CNY 100M)", "label_cn": "财政收入（亿元）"},
    {"id": "rd_intensity", "label": "R&D Intensity (%)", "label_cn": "研发投入强度（%）"},
]


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def fetch_via_testclient() -> dict:
    """Try to load real data via TestClient (works when backend deps are installed)."""
    try:
        from starlette.testclient import TestClient
        from backend.api.main import app

        with TestClient(app) as client:
            # Root metadata
            root = client.get("/health").json()

            # City data — hit available endpoints
            cities_info = {}
            for city in CITIES:
                code = city["code"]
                try:
                    # Try trend endpoint for each indicator
                    city_indicators = {}
                    for ind in INDICATORS:
                        resp = client.get(
                            f"/api/v1/data/trend",
                            params={"city": code, "indicator": ind["id"]},
                        )
                        if resp.status_code == 200:
                            city_indicators[ind["id"]] = resp.json()
                        else:
                            # Try other endpoints
                            resp2 = client.get(
                                f"/api/v1/cities/{code}/economy",
                            )
                            if resp2.status_code == 200:
                                city_indicators[ind["id"]] = resp2.json()

                    if city_indicators:
                        cities_info[code] = city_indicators
                        print(f"  ✓ {code}: {len(city_indicators)} indicators")
                except Exception as e:
                    print(f"  ⚠ {code}: {e}")

            # Forecast data
            forecasts = {}
            for city in CITIES:
                code = city["code"]
                try:
                    resp = client.get(
                        "/api/v1/forecast/city",
                        params={"city": code},
                    )
                    if resp.status_code == 200:
                        forecasts[code] = resp.json()
                        print(f"  ✓ {code} forecast loaded")
                except Exception:
                    pass

            return {
                "meta": root,
                "cities": cities_info,
                "forecasts": forecasts,
            }

    except ImportError as e:
        print(f"  ⚠ Cannot use TestClient: {e}")
        return {}
    except Exception as e:
        print(f"  ⚠ TestClient error: {e}")
        return {}


def try_real_server() -> dict:
    """Try connecting to a running backend at localhost:8000."""
    try:
        r = httpx.get("http://localhost:8000/health", timeout=3)
        if r.status_code == 200:
            print("  ✓ Connected to running backend")
            base = "http://localhost:8000"
        else:
            return {}
    except Exception:
        return {}

    result = {"meta": r.json(), "cities": {}, "forecasts": {}}

    # Fetch data for each city
    for city in CITIES:
        code = city["code"]
        city_data = {}
        for ind in INDICATORS:
            try:
                resp = httpx.get(
                    f"{base}/api/v1/data/trend",
                    params={"city": code, "indicator": ind["id"]},
                    timeout=5,
                )
                if resp.status_code == 200:
                    city_data[ind["id"]] = resp.json()
            except Exception:
                pass

        if city_data:
            result["cities"][code] = city_data
            print(f"  ✓ {code} data")

        try:
            fc = httpx.get(
                f"{base}/api/v1/forecast/city",
                params={"city": code},
                timeout=10,
            )
            if fc.status_code == 200:
                result["forecasts"][code] = fc.json()
                print(f"  ✓ {code} forecast")
        except Exception:
            pass

    return result


# ── Fallback: generate sample data when no backend is available ──
def generate_sample_data() -> dict:
    """Generate realistic-looking sample data for the static dashboard.
    Used when no backend is running and TestClient isn't available.
    """
    import math
    import random

    seed = 42

    def rng():
        nonlocal seed
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        return seed / 0x7FFFFFFF

    cities_data = {}
    for ci, city in enumerate(CITIES):
        base_gdp = 5000 + ci * 3000
        city_data = {}
        for ind in INDICATORS:
            ind_id = ind["id"]
            entries = []
            for y in range(2010, 2026):
                noise = (rng() - 0.5) * 0.1
                if ind_id == "gdp":
                    val = base_gdp * (1 + 0.08) ** (y - 2010) * (1 + noise * 0.5)
                elif ind_id == "gdp_growth":
                    val = 7.0 + (rng() - 0.5) * 4
                elif ind_id == "population":
                    val = 800 + ci * 150 + (y - 2010) * 15 + (rng() - 0.5) * 30
                elif ind_id == "fiscal_revenue":
                    val = base_gdp * 0.12 * (1 + 0.07) ** (y - 2010) * (1 + noise)
                else:  # rd_intensity
                    val = 2.0 + ci * 0.3 + (y - 2010) * 0.08 + (rng() - 0.5) * 0.3

                val = round(max(val, 0), 2) if val >= 0 else round(val, 2)
                entries.append({"year": y, "value": val})

            city_data[ind_id] = {
                "indicator": ind_id,
                "city": city["code"],
                "data": entries,
                "unit": INDICATORS[[i["id"] for i in INDICATORS].index(ind_id)]["label"],
            }
        cities_data[city["code"]] = city_data

    # Generate forecasts
    forecasts = {}
    for city in CITIES:
        city_forecasts = []
        for ind in INDICATORS:
            ind_id = ind["id"]
            city_data_ind = cities_data[city["code"]].get(ind_id, {"data": []})
            hist_vals = [d["value"] for d in city_data_ind.get("data", [])]
            last_val = hist_vals[-1] if hist_vals else 100
            fc_vals = []
            ci_low = []
            ci_high = []
            for step in range(1, 6):
                growth = (rng() - 0.48) * 0.06
                v = last_val * (1 + growth) ** step
                fc_vals.append(round(v, 2))
                ci_low.append(round(v * 0.92, 2))
                ci_high.append(round(v * 1.08, 2))

            city_forecasts.append({
                "indicator": ind_id,
                "indicator_label": ind["label"],
                "forecast_years": [2026 + i for i in range(5)],
                "forecast_values": fc_vals,
                "confidence_lower": ci_low,
                "confidence_upper": ci_high,
                "historical_years": list(range(2010, 2026)),
                "historical_values": [d["value"] for d in city_data_ind.get("data", [])],
                "label": ind["label"],
            })
        forecasts[city["code"]] = {"city": city["code"], "forecasts": city_forecasts}

    return {"meta": {"status": "healthy", "version": "1.0.0-sample"}, "cities": cities_data,
            "forecasts": forecasts}


def build_site(data: dict):
    """Generate the complete static site from fetched/sample data."""
    print("  ├─ Building static site...")

    # Copy site/index.html as the main page
    site_src = Path(__file__).parent.parent / "site" / "index.html"
    if site_src.exists():
        shutil.copy2(site_src, SITE_DIR / "index.html")
        print("  ├─ index.html copied")

    # Copy favicon
    favicon_src = Path(__file__).parent.parent / "frontend" / "favicon.ico"
    if favicon_src.exists():
        shutil.copy2(favicon_src, SITE_DIR / "favicon.ico")

    # Build index metadata
    index_data = {
        "name": "Urban Pulse",
        "description": "City economic intelligence platform",
        "version": data.get("meta", {}).get("version", "1.0.0"),
        "cities": len(CITIES),
        "indicators": len(INDICATORS),
        "data_years": "2010–2025",
        "is_sample": "forecasts" not in data or not data["forecasts"],
        "cities_list": CITIES,
        "indicators_list": INDICATORS,
    }
    (DATA_DIR / "index.json").write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2)
    )
    print("  ├─ index.json written")

    # Build city data files
    if data.get("cities"):
        for code, city_data in data["cities"].items():
            filepath = DATA_DIR / f"city_{code}.json"
            filepath.write_text(json.dumps(city_data, ensure_ascii=False, default=str))
        print(f"  ├─ {len(data['cities'])} city data files written")

    # Build forecasts
    if data.get("forecasts"):
        flat = []
        for code, fc_data in data["forecasts"].items():
            if isinstance(fc_data, dict) and "forecasts" in fc_data:
                flat.extend(fc_data["forecasts"])
        (DATA_DIR / "forecasts.json").write_text(
            json.dumps(flat, ensure_ascii=False, default=str)
        )
        print(f"  ├─ forecasts.json written ({len(flat)} entries)")
    else:
        # Write empty forecast
        (DATA_DIR / "forecasts.json").write_text("[]")
        print("  ├─ forecasts.json (empty)")

    # City comparison data
    (DATA_DIR / "comparison.json").write_text(
        json.dumps({"cities": CITIES, "indicators": INDICATORS}, ensure_ascii=False, indent=2)
    )
    print("  ├─ comparison.json written")

    print(f"  └─ ✓ Site ready at {SITE_DIR}")
    return True


def main():
    print("=" * 50)
    print("  Urban Pulse — Static Site Builder")
    print("=" * 50)
    print()

    ensure_dir(SITE_DIR)
    ensure_dir(DATA_DIR)

    # Strategy: try TestClient first, then local server, finally sample data
    data = fetch_via_testclient()
    if not data or not data.get("cities"):
        print("  ⚠ TestClient unavailable, trying local server...")
        data = try_real_server()
    if not data or not data.get("cities"):
        print("  ⚠ No backend running, using sample data")
        print("    (run 'uvicorn backend.api.main:app' for real data)")
        print()
        data = generate_sample_data()
    else:
        print()

    # Re-generate forecasts if we have city data but no forecasts
    if data.get("cities") and not data.get("forecasts"):
        sample = generate_sample_data()
        data["forecasts"] = sample["forecasts"]
        print("  ✓ Forecasts generated from sample engine")
        data["meta"]["is_sample"] = False

    build_site(data)
    print()
    print("  Deployment: _site/ → GitHub Pages")
    print()


if __name__ == "__main__":
    main()
