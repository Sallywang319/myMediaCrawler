# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/2 11:05
# @Desc    : 本地缓存

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from cache.abs_cache import AbstractCache


class ExpiringLocalCache(AbstractCache):

    def __init__(self, cron_interval: int = 10):
        """
        初始化本地缓存
        :param cron_interval: 定时清楚cache的时间间隔
        :return:
        """
        self._cron_interval = cron_interval
        self._cache_container: Dict[str, Tuple[Any, float]] = {}
        self._cron_task: Optional[asyncio.Task] = None
        # 开启定时清理任务
        self._schedule_clear()

    def __del__(self):
        """
        析构函数，清理定时任务
        :return:
        """
        if self._cron_task is not None and not self._cron_task.done():
            try:
                self._cron_task.cancel()
            except Exception:
                pass

    async def cleanup(self):
        """
        清理资源，取消后台任务
        :return:
        """
        if self._cron_task is not None and not self._cron_task.done():
            self._cron_task.cancel()
            try:
                await self._cron_task
            except asyncio.CancelledError:
                pass

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取键的值
        :param key:
        :return:
        """
        value, expire_time = self._cache_container.get(key, (None, 0))
        if value is None:
            return None

        # 如果键已过期，则删除键并返回None
        if expire_time < time.time():
            del self._cache_container[key]
            return None

        return value

    def set(self, key: str, value: Any, expire_time: int) -> None:
        """
        将键的值设置到缓存中
        :param key:
        :param value:
        :param expire_time:
        :return:
        """
        self._cache_container[key] = (value, time.time() + expire_time)

    def keys(self, pattern: str) -> List[str]:
        """
        获取所有符合pattern的key
        :param pattern: 匹配模式
        :return:
        """
        if pattern == '*':
            return list(self._cache_container.keys())

        # 本地缓存通配符暂时将*替换为空
        if '*' in pattern:
            pattern = pattern.replace('*', '')

        return [key for key in self._cache_container.keys() if pattern in key]

    def _schedule_clear(self):
        """
        开启定时清理任务,
        :return:
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 如果没有运行中的事件循环，尝试获取或创建
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # 如果事件循环已关闭，不创建任务
                return

        if loop.is_running():
            self._cron_task = loop.create_task(self._start_clear_cron())
        else:
            # 如果事件循环未运行，不创建任务
            self._cron_task = None

    def _clear(self):
        """
        根据过期时间清理缓存
        :return:
        """
        for key, (value, expire_time) in self._cache_container.items():
            if expire_time < time.time():
                del self._cache_container[key]

    async def _start_clear_cron(self):
        """
        开启定时清理任务
        :return:
        """
        while True:
            self._clear()
            await asyncio.sleep(self._cron_interval)


if __name__ == '__main__':
    cache = ExpiringLocalCache(cron_interval=2)
    cache.set('name', '程序员阿江-Relakkes', 3)
    print(cache.get('key'))
    print(cache.keys("*"))
    time.sleep(4)
    print(cache.get('key'))
    del cache
    time.sleep(1)
    print("done")
