"""
FoxAssistant Python 配置管理

读取和保存 config.json
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class OrbPosition:
    """Orb 窗口位置"""
    x: int = 0
    y: int = 0


@dataclass
class AppConfig:
    """应用配置"""
    enable_orb: bool = True
    orb_position: OrbPosition = field(default_factory=OrbPosition)
    orb_size: int = 120
    wakeup_phrase: str = "wakeup"
    idle_timeout: int = 30


def find_config_path() -> Optional[Path]:
    """查找 config.json 路径"""
    candidates = [
        Path(__file__).parent.parent.parent.parent.parent / "config.json",
        Path(__file__).parent.parent / "config.json",
        Path.cwd() / "config.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_config() -> AppConfig:
    """加载配置"""
    config_path = find_config_path()

    if config_path is None:
        logger.info("[Config] config.json 不存在，使用默认值")
        return AppConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        position = OrbPosition(
            x=data.get("orb_position", {}).get("x", 0),
            y=data.get("orb_position", {}).get("y", 0)
        )

        config = AppConfig(
            enable_orb=data.get("enable_orb", True),
            orb_position=position,
            orb_size=data.get("orb_size", 120),
            wakeup_phrase=data.get("wakeup_phrase", "你好狐狸"),
            idle_timeout=data.get("idle_timeout", 30)
        )

        logger.info(f"[Config] 配置加载成功: orb={config.enable_orb}")
        return config

    except Exception as e:
        logger.error(f"[Config] 配置加载失败: {e}")
        return AppConfig()


def save_config(config: AppConfig) -> bool:
    """保存配置"""
    config_path = find_config_path()

    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent.parent / "config.json"

    try:
        data = {
            "enable_orb": config.enable_orb,
            "orb_position": {"x": config.orb_position.x, "y": config.orb_position.y},
            "orb_size": config.orb_size,
            "wakeup_phrase": config.wakeup_phrase,
            "idle_timeout": config.idle_timeout
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"[Config] 配置已保存: {config_path}")
        return True

    except Exception as e:
        logger.error(f"[Config] 配置保存失败: {e}")
        return False