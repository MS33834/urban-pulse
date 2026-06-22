"""
预测快照存档（Phase 5 — Community validation dashboard）

保存每一次预测结果，并在真实数据公布后回填 actual_value，
为后续的预测准确率追踪与社区验证提供数据基础。
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_ARCHIVE_DIR = Path(__file__).parents[2] / "data" / "forecasts"


@dataclass
class ForecastSnapshot:
    """单次预测快照。"""

    model: str
    city_code: str
    indicator: str
    forecast_date: str
    target_year: int
    predicted_value: float
    forecast_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    plugin_type: str = "forecaster"
    confidence_interval: tuple[float, float] | None = None
    actual_value: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["predicted_value"] = float(self.predicted_value)
        if self.actual_value is not None:
            data["actual_value"] = float(self.actual_value)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastSnapshot:
        ci = data.get("confidence_interval")
        if isinstance(ci, list) and len(ci) == 2:
            ci = tuple(ci)
        return cls(
            forecast_id=data.get("forecast_id", uuid.uuid4().hex[:12]),
            model=data["model"],
            city_code=data["city_code"],
            indicator=data["indicator"],
            forecast_date=data["forecast_date"],
            target_year=int(data["target_year"]),
            predicted_value=float(data["predicted_value"]),
            plugin_type=data.get("plugin_type", "forecaster"),
            confidence_interval=ci,
            actual_value=float(data["actual_value"]) if data.get("actual_value") is not None else None,
            metadata=data.get("metadata", {}),
        )


class ForecastArchive:
    """预测存档管理器。"""

    def __init__(self, archive_dir: Path | str | None = None) -> None:
        self.archive_dir = Path(archive_dir) if archive_dir else DEFAULT_ARCHIVE_DIR
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._archive_file = self.archive_dir / "forecast_archive.jsonl"

    def save(self, snapshot: ForecastSnapshot) -> str:
        """保存预测快照，返回 forecast_id。"""
        with self._archive_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")
        logger.debug(f"预测已存档: {snapshot.forecast_id}")
        return snapshot.forecast_id

    def list_all(self) -> list[ForecastSnapshot]:
        """列出所有存档预测。"""
        if not self._archive_file.exists():
            return []
        snapshots: list[ForecastSnapshot] = []
        with self._archive_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    snapshots.append(ForecastSnapshot.from_dict(json.loads(line)))
                except Exception as exc:
                    logger.warning(f"解析预测存档行失败: {exc}")
        return snapshots

    def find_pending(self) -> list[ForecastSnapshot]:
        """列出尚未回填 actual_value 的预测。"""
        return [s for s in self.list_all() if s.actual_value is None]

    def find_by_id(self, forecast_id: str) -> ForecastSnapshot | None:
        """按 ID 查找预测。"""
        for snapshot in self.list_all():
            if snapshot.forecast_id == forecast_id:
                return snapshot
        return None

    def update_actual(self, forecast_id: str, actual_value: float) -> bool:
        """回填真实值。返回是否成功。"""
        snapshots = self.list_all()
        updated = False
        for snapshot in snapshots:
            if snapshot.forecast_id == forecast_id:
                snapshot.actual_value = float(actual_value)
                updated = True
                break
        if not updated:
            return False
        self._rewrite(snapshots)
        logger.debug(f"预测已回填真实值: {forecast_id} = {actual_value}")
        return True

    def update_actual_by_match(
        self,
        model: str,
        city_code: str,
        indicator: str,
        target_year: int,
        actual_value: float,
    ) -> int:
        """
        按 model + city_code + indicator + target_year 匹配并回填真实值。

        返回成功回填的记录数。
        """
        snapshots = self.list_all()
        count = 0
        for snapshot in snapshots:
            if (
                snapshot.model == model
                and snapshot.city_code == city_code
                and snapshot.indicator == indicator
                and snapshot.target_year == target_year
                and snapshot.actual_value is None
            ):
                snapshot.actual_value = float(actual_value)
                count += 1
        if count > 0:
            self._rewrite(snapshots)
            logger.debug(f"按匹配条件回填 {count} 条预测真实值")
        return count

    def _rewrite(self, snapshots: list[ForecastSnapshot]) -> None:
        """重写整个存档文件。"""
        with self._archive_file.open("w", encoding="utf-8") as f:
            for snapshot in snapshots:
                f.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")

    def to_dataframe(self) -> pd.DataFrame:
        """导出为 DataFrame。"""
        records = [s.to_dict() for s in self.list_all()]
        return pd.DataFrame(records)

    def clear(self) -> None:
        """清空存档（主要用于测试）。"""
        if self._archive_file.exists():
            self._archive_file.unlink()
