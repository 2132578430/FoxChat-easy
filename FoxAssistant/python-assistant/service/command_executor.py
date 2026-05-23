"""
命令执行器

执行各类本地命令：
- 音乐播放（QQ音乐 subprocess）
- 天气查询（wttr.in HTTP API）
- 时间查询（系统时间）
"""

import subprocess
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from config.command_rules import CommandType


class CommandExecutor:
    """命令执行器"""

    def __init__(self):
        self.weather_api = "https://wttr.in/?format=3"

    def execute(self, intent: str, text: str) -> Dict[str, Any]:
        """
        执行命令

        Args:
            intent: 命令意图
            text: 原始文本

        Returns:
            执行结果 {"command": intent, "result": output}
        """
        executor_map = {
            CommandType.PLAY_MUSIC: self._execute_music,
            CommandType.PAUSE_MUSIC: self._pause_music,
            CommandType.NEXT_SONG: self._next_song,
            CommandType.PREV_SONG: self._prev_song,
            CommandType.QUERY_TIME: self._query_time,
            CommandType.QUERY_WEATHER: self._query_weather,
            CommandType.SET_REMINDER: self._set_reminder,
            CommandType.SHUTDOWN: self._shutdown,
            CommandType.SLEEP: self._sleep,
        }

        executor = executor_map.get(intent)
        if executor:
            try:
                result = executor(text)
                return {"command": intent, "result": result, "success": True}
            except Exception as e:
                logger.error(f"【命令执行】执行失败: {intent} - {e}")
                return {"command": intent, "result": f"执行失败: {str(e)}", "success": False}

        return {"command": intent, "result": "未知命令，无法执行", "success": False}

    def _execute_music(self, text: str) -> str:
        """启动QQ音乐"""
        try:
            # Windows 下启动QQ音乐
            subprocess.Popen(
                ["start", "QQMusic"],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("【命令执行】启动QQ音乐")
            return "已启动QQ音乐"
        except Exception as e:
            logger.error(f"【命令执行】启动QQ音乐失败: {e}")
            return f"启动QQ音乐失败: {str(e)}"

    def _pause_music(self, text: str) -> str:
        """暂停音乐（模拟按键）"""
        logger.info("【命令执行】暂停音乐")
        return "暂停音乐（需要QQ音乐支持）"

    def _next_song(self, text: str) -> str:
        """下一首（模拟按键）"""
        logger.info("【命令执行】下一首")
        return "下一首（需要QQ音乐支持）"

    def _prev_song(self, text: str) -> str:
        """上一首（模拟按键）"""
        logger.info("【命令执行】上一首")
        return "上一首（需要QQ音乐支持）"

    def _query_time(self, text: str) -> str:
        """查询当前时间"""
        now = datetime.now()
        time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
        logger.info(f"【命令执行】查询时间: {time_str}")
        return f"现在是 {time_str}"

    def _query_weather(self, text: str) -> str:
        """查询天气（wttr.in）"""
        try:
            with httpx.Client() as client:
                response = client.get(self.weather_api, timeout=5.0)
                if response.status_code == 200:
                    weather = response.text.strip()
                    logger.info(f"【命令执行】查询天气: {weather}")
                    return f"当前天气: {weather}"
                else:
                    return "天气查询失败"
        except Exception as e:
            logger.error(f"【命令执行】天气查询失败: {e}")
            return f"天气查询失败: {str(e)}"

    def _set_reminder(self, text: str) -> str:
        """设置提醒（待实现）"""
        logger.info(f"【命令执行】设置提醒: {text}")
        return "提醒功能待实现"

    def _shutdown(self, text: str) -> str:
        """关机"""
        logger.warning("【命令执行】关机命令（未执行，需要确认）")
        return "关机命令已收到（需要二次确认）"

    def _sleep(self, text: str) -> str:
        """休眠"""
        logger.warning("【命令执行】休眠命令（未执行，需要确认）")
        return "休眠命令已收到（需要二次确认）"