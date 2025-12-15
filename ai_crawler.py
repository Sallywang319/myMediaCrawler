# -*- coding: utf-8 -*-
# @Desc: AI辅助的自动化爬取脚本
# 支持微博、B站、知乎三个平台的自动化爬取，使用AI进行关键词提取

import asyncio
import os
import sys
from typing import List

import config
from ai_agent import LLMAgent
from media_platform.bilibili import BilibiliCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.zhihu import ZhihuCrawler
from tools import utils

from cookies import WB_cookie, BILI_cookie, ZHIHU_cookie


class AICrawlerManager:
    """AI辅助的爬虫管理器 - 专注于关键词提取和数据爬取"""

    def __init__(self, event_description: str):
        """
        初始化AI爬虫管理器
        Args:
            event_description: 热点事件描述
        """
        self.event_description = event_description
        self.llm_agent = LLMAgent(
            api_key=config.LLM_API_KEY or None,
            base_url=config.LLM_BASE_URL or None,
            model=config.LLM_MODEL,
        )
        self.keywords: List[str] = []

    async def extract_keywords(self) -> List[str]:
        """提取搜索关键词"""
        utils.logger.info(
            f"[AICrawlerManager] 开始提取关键词，事件描述: {self.event_description}")
        self.keywords = await self.llm_agent.extract_keywords(
            self.event_description,
            max_keywords=config.MAX_KEYWORDS_PER_EVENT
        )
        utils.logger.info(f"[AICrawlerManager] 提取的关键词: {self.keywords}")
        return self.keywords

    async def crawl_weibo(self):
        """
        爬取微博数据（只做搜索和存储，不做相关性判断）
        """
        utils.logger.info("[AICrawlerManager] 开始爬取微博数据...")

        # 保存原始配置
        original_platform = config.PLATFORM
        original_keywords = config.KEYWORDS
        original_cookies = config.COOKIES
        original_crawler_type = config.CRAWLER_TYPE
        original_headless = config.HEADLESS
        original_enable_comments = config.ENABLE_GET_COMMENTS

        try:
            # 设置微博配置
            config.PLATFORM = "wb"
            config.KEYWORDS = ",".join(self.keywords)
            config.COOKIES = WB_cookie
            config.CRAWLER_TYPE = "search"
            config.HEADLESS = True
            config.ENABLE_GET_COMMENTS = True

            # 使用WeiboCrawler进行搜索和数据保存
            utils.logger.info("[AICrawlerManager] 使用WeiboCrawler进行搜索和数据保存...")
            weibo_crawler = WeiboCrawler()
            await weibo_crawler.start()

            utils.logger.info(
                "[AICrawlerManager] 微博搜索和数据保存完成，数据已保存到 data/weibo/ 目录")

        finally:
            # 恢复原始配置
            config.PLATFORM = original_platform
            config.KEYWORDS = original_keywords
            config.COOKIES = original_cookies
            config.CRAWLER_TYPE = original_crawler_type
            config.HEADLESS = original_headless
            config.ENABLE_GET_COMMENTS = original_enable_comments

    async def crawl_bilibili(self):
        """
        爬取B站数据（只做搜索和存储，不做相关性判断）
        """
        utils.logger.info("[AICrawlerManager] 开始爬取B站数据...")

        # 保存原始配置
        original_platform = config.PLATFORM
        original_keywords = config.KEYWORDS
        original_cookies = config.COOKIES
        original_crawler_type = config.CRAWLER_TYPE
        original_headless = config.HEADLESS

        try:
            # 设置B站配置
            config.PLATFORM = "bili"
            config.KEYWORDS = ",".join(self.keywords)
            config.COOKIES = BILI_cookie
            config.CRAWLER_TYPE = "search"
            config.HEADLESS = True

            # 使用BilibiliCrawler进行搜索和数据保存
            utils.logger.info(
                "[AICrawlerManager] 使用BilibiliCrawler进行搜索和数据保存...")
            bili_crawler = BilibiliCrawler()
            await bili_crawler.start()

            utils.logger.info(
                "[AICrawlerManager] B站搜索和数据保存完成，数据已保存到 data/bilibili/ 目录")

        finally:
            # 恢复原始配置
            config.PLATFORM = original_platform
            config.KEYWORDS = original_keywords
            config.COOKIES = original_cookies
            config.CRAWLER_TYPE = original_crawler_type
            config.HEADLESS = original_headless

    async def crawl_zhihu(self):
        """
        爬取知乎数据（只做搜索和存储，不做相关性判断）
        """
        utils.logger.info("[AICrawlerManager] 开始爬取知乎数据...")

        # 保存原始配置
        original_platform = config.PLATFORM
        original_keywords = config.KEYWORDS
        original_cookies = config.COOKIES
        original_crawler_type = config.CRAWLER_TYPE
        original_headless = config.HEADLESS
        original_enable_comments = config.ENABLE_GET_COMMENTS

        try:
            # 设置知乎配置
            config.PLATFORM = "zhihu"
            config.KEYWORDS = ",".join(self.keywords)
            config.COOKIES = ZHIHU_cookie
            config.CRAWLER_TYPE = "search"
            config.HEADLESS = True
            config.ENABLE_GET_COMMENTS = False

            # 使用ZhihuCrawler进行搜索和数据保存
            utils.logger.info("[AICrawlerManager] 使用ZhihuCrawler进行搜索和数据保存...")
            zhihu_crawler = ZhihuCrawler()
            await zhihu_crawler.start()

            utils.logger.info(
                "[AICrawlerManager] 知乎搜索和数据保存完成，数据已保存到 data/zhihu/ 目录")

        finally:
            # 恢复原始配置
            config.PLATFORM = original_platform
            config.KEYWORDS = original_keywords
            config.COOKIES = original_cookies
            config.CRAWLER_TYPE = original_crawler_type
            config.HEADLESS = original_headless
            config.ENABLE_GET_COMMENTS = original_enable_comments

    async def crawl_all_platforms(self):
        """爬取所有平台的数据"""
        utils.logger.info("[AICrawlerManager] 开始爬取所有平台数据...")

        # 提取关键词
        await self.extract_keywords()

        # 并行爬取三个平台（只做搜索和存储，不做相关性判断）
        utils.logger.info("[AICrawlerManager] 开始并行爬取所有平台数据...")
        await asyncio.gather(
            # self.crawl_weibo(),
            # self.crawl_bilibili(),
            self.crawl_zhihu(),
            return_exceptions=True
        )

        utils.logger.info("[AICrawlerManager] 所有平台爬取完成，数据已保存到data目录")
        utils.logger.info(
            "[AICrawlerManager] 请运行 data_postprocessor.py 进行数据后处理（相关性判断、评论集成等）")


async def main():
    """主函数"""
    # 从命令行参数或环境变量获取事件描述
    if len(sys.argv) > 1:
        event_description = " ".join(sys.argv[1:])
    else:
        event_description = os.getenv("EVENT_DESCRIPTION", "")
        if not event_description:
            print("请提供热点事件描述作为参数，或设置环境变量 EVENT_DESCRIPTION")
            print("示例: python ai_crawler.py '某热点事件的具体描述'")
            return

    # 创建AI爬虫管理器
    manager = AICrawlerManager(event_description)

    try:
        # 执行爬取
        await manager.crawl_all_platforms()
    finally:
        # 清理所有待处理的任务
        await _cleanup_tasks()


async def _cleanup_tasks():
    """
    清理所有待处理的异步任务
    """
    try:
        # 获取当前事件循环中所有待处理的任务
        loop = asyncio.get_running_loop()
        current_task = asyncio.current_task()
        tasks = [task for task in asyncio.all_tasks(loop)
                 if not task.done() and task != current_task]

        if tasks:
            utils.logger.info(f"[AICrawlerManager] 清理 {len(tasks)} 个待处理任务...")
            # 取消所有待处理的任务
            for task in tasks:
                task.cancel()

            # 等待所有任务完成取消
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        utils.logger.debug(f"[AICrawlerManager] 清理任务时出错: {e}")


if __name__ == "__main__":
    asyncio.run(main())
