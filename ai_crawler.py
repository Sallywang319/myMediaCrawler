# -*- coding: utf-8 -*-
# @Desc: AI辅助的自动化爬取脚本
# 支持微博、B站、知乎三个平台的自动化爬取，使用AI进行关键词提取和相关性判断

import asyncio
import os
import sys
from typing import Dict, List, Optional

import config
from ai_agent import LLMAgent
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.zhihu import ZhihuCrawler
from tools import utils

from cookies import WB_cookie, BILI_cookie, ZHIHU_cookie, XHS_cookie


class AICrawlerManager:
    """AI辅助的爬虫管理器"""

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
        self.relevant_note_ids: Dict[str, List[str]] = {
            "weibo": [],
            "bilibili": [],
            "zhihu": []
        }
        # 临时存储的浏览器上下文（用于微博爬取）
        self._temp_wb_client = None
        self._temp_browser_context = None
        self._temp_context_page = None

    async def extract_keywords(self) -> List[str]:
        """提取搜索关键词"""
        utils.logger.info(f"[AICrawlerManager] 开始提取关键词，事件描述: {self.event_description}")
        self.keywords = await self.llm_agent.extract_keywords(
            self.event_description,
            max_keywords=config.MAX_KEYWORDS_PER_EVENT
        )
        utils.logger.info(f"[AICrawlerManager] 提取的关键词: {self.keywords}")
        return self.keywords

    async def crawl_weibo(self) -> List[str]:
        """
        爬取微博数据（使用原始的WeiboCrawler方式，稳定可靠）
        Returns:
            相关的note_id列表
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
            config.HEADLESS = True  # 服务器运行，使用无头模式
            config.ENABLE_GET_COMMENTS = True  # 开启评论爬取

            # 直接使用原始的WeiboCrawler，稳定可靠
            utils.logger.info("[AICrawlerManager] 使用原始WeiboCrawler进行搜索和数据保存...")
            weibo_crawler = WeiboCrawler()
            await weibo_crawler.start()
            
            utils.logger.info("[AICrawlerManager] 微博搜索和数据保存完成")
            utils.logger.info("[AICrawlerManager] 注意：微博数据已保存到 data/weibo/ 目录")
            utils.logger.info("[AICrawlerManager] 注意：暂时未实现相关性判断和detail模式，后续可添加")

            # 从已保存的数据中读取note_id（用于返回）
            note_ids = await self._get_weibo_note_ids_from_saved_data()
            self.relevant_note_ids["weibo"] = note_ids
            return note_ids

        finally:
            # 恢复原始配置
            config.PLATFORM = original_platform
            config.KEYWORDS = original_keywords
            config.COOKIES = original_cookies
            config.CRAWLER_TYPE = original_crawler_type
            config.HEADLESS = original_headless
            config.ENABLE_GET_COMMENTS = original_enable_comments
    
    async def _get_weibo_note_ids_from_saved_data(self) -> List[str]:
        """从已保存的数据中读取note_id列表"""
        note_ids = []
        try:
            import json
            import os
            from pathlib import Path
            
            # 从JSON文件读取
            json_dir = Path("data/weibo/json")
            if json_dir.exists():
                for json_file in json_dir.glob("search_contents_*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    note_id = item.get("note_id")
                                    if note_id and note_id not in note_ids:
                                        note_ids.append(note_id)
                    except Exception as e:
                        utils.logger.error(f"[AICrawlerManager] 读取JSON文件 {json_file} 失败: {e}")
            
            # 从CSV文件读取
            csv_dir = Path("data/weibo/csv")
            if csv_dir.exists():
                import csv
                for csv_file in csv_dir.glob("search_contents_*.csv"):
                    try:
                        with open(csv_file, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                note_id = row.get("note_id")
                                if note_id and note_id not in note_ids:
                                    note_ids.append(note_id)
                    except Exception as e:
                        utils.logger.error(f"[AICrawlerManager] 读取CSV文件 {csv_file} 失败: {e}")
            
            utils.logger.info(f"[AICrawlerManager] 从已保存数据中读取到 {len(note_ids)} 个微博note_id")
        except Exception as e:
            utils.logger.error(f"[AICrawlerManager._get_weibo_note_ids_from_saved_data] 读取数据失败: {e}")
        
        return note_ids

    async def _search_weibo_and_collect_note_ids_with_crawler_OLD(self) -> List[str]:
        """使用爬虫搜索微博并收集note_id（完整流程）"""
        # 先执行一次search模式，但我们需要访问搜索结果
        # 由于WeiboCrawler的search方法不返回note_id列表，我们需要修改它
        # 或者，我们可以从存储的数据中读取

        # 更实用的方法：创建一个临时的WeiboCrawler，执行search，然后从JSON/CSV中读取note_id
        # 或者，我们可以修改WeiboCrawler来返回note_id列表

        # 这里我们采用一个workaround：直接调用client的搜索API
        from playwright.async_api import async_playwright
        from proxy.proxy_ip_pool import create_ip_pool
        from media_platform.weibo.field import SearchType
        from media_platform.weibo.help import filter_search_result_card
        from media_platform.weibo.login import WeiboLogin

        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        all_note_ids = []
        weibo_limit_count = 10

        async with async_playwright() as playwright:
            # 初始化浏览器
            if config.ENABLE_CDP_MODE:
                browser_context = await WeiboCrawler().launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    utils.get_mobile_user_agent(),
                    headless=config.CDP_HEADLESS,
                )
            else:
                chromium = playwright.chromium
                browser_context = await WeiboCrawler().launch_browser(
                    chromium, None, utils.get_mobile_user_agent(), headless=config.HEADLESS
                )

            await browser_context.add_init_script(path="libs/stealth.min.js")
            context_page = await browser_context.new_page()
            await context_page.goto("https://m.weibo.cn")

            # 创建客户端
            from media_platform.weibo.client import WeiboClient
            cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
            wb_client = WeiboClient(
                proxy=httpx_proxy_format,
                headers={
                    "User-Agent": utils.get_mobile_user_agent(),
                    "Cookie": cookie_str,
                    "Origin": "https://m.weibo.cn",
                    "Referer": "https://m.weibo.cn",
                    "Content-Type": "application/json;charset=UTF-8",
                },
                playwright_page=context_page,
                cookie_dict=cookie_dict,
            )

            # 检查登录状态
            if not await wb_client.pong():
                login_obj = WeiboLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",
                    browser_context=browser_context,
                    context_page=context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await context_page.goto("https://m.weibo.cn")
                await asyncio.sleep(2)
                await wb_client.update_cookies(browser_context=browser_context)

            # 执行搜索
            search_type = SearchType.REAL_TIME if config.WEIBO_SEARCH_TYPE == "real_time" else SearchType.DEFAULT

            for keyword in self.keywords:
                utils.logger.info(f"[AICrawlerManager] 搜索微博关键词: {keyword}")
                page = 1
                max_pages = (config.CRAWLER_MAX_NOTES_COUNT // weibo_limit_count) + 1

                while page <= max_pages:
                    try:
                        search_res = await wb_client.get_note_by_keyword(
                            keyword=keyword,
                            page=page,
                            search_type=search_type
                        )
                        note_list = filter_search_result_card(search_res.get("cards", []))

                        if not note_list:
                            utils.logger.info(f"[AICrawlerManager] 关键词 {keyword} 第 {page} 页无结果，停止搜索")
                            break

                        for note_item in note_list:
                            if note_item:
                                mblog = note_item.get("mblog")
                                if mblog:
                                    note_id = mblog.get("id")
                                    if note_id and note_id not in all_note_ids:
                                        all_note_ids.append(note_id)
                                        # 立即保存搜索到的数据（即使后续可能被过滤，也先保存作为备份）
                                        try:
                                            from store import weibo as weibo_store
                                            from var import source_keyword_var
                                            source_keyword_var.set(keyword)  # 设置当前关键词
                                            await weibo_store.update_weibo_note(note_item)
                                            # 如果开启了媒体爬取，也保存图片
                                            if config.ENABLE_GET_MEIDAS:
                                                from media_platform.weibo.core import WeiboCrawler
                                                temp_crawler = WeiboCrawler()
                                                temp_crawler.wb_client = wb_client
                                                await temp_crawler.get_note_images(mblog)
                                            utils.logger.info(f"[AICrawlerManager] 已保存微博note: {note_id} (搜索阶段)")
                                        except Exception as e:
                                            utils.logger.error(f"[AICrawlerManager] 保存微博note {note_id} 时出错: {e}")

                        page += 1
                        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                    except Exception as e:
                        utils.logger.error(f"[AICrawlerManager] 搜索关键词 {keyword} 第 {page} 页时出错: {e}")
                        break

            # 保存wb_client供后续使用
            self._temp_wb_client = wb_client
            self._temp_browser_context = browser_context
            self._temp_context_page = context_page

            utils.logger.info(f"[AICrawlerManager] 共收集到 {len(all_note_ids)} 个微博note_id")
            return all_note_ids

    async def _get_weibo_note_content(self, crawler: Optional[WeiboCrawler], note_id: str) -> Optional[Dict]:
        """获取微博内容用于相关性判断"""
        try:
            # 使用临时保存的client或传入的crawler
            if hasattr(self, '_temp_wb_client'):
                wb_client = self._temp_wb_client
            elif crawler and hasattr(crawler, 'wb_client'):
                wb_client = crawler.wb_client
            else:
                utils.logger.error("[AICrawlerManager._get_weibo_note_content] 无法获取wb_client")
                return None

            note_info = await wb_client.get_note_info_by_id(note_id)
            if note_info:
                mblog = note_info.get("mblog", {})
                return {
                    "content": mblog.get("text", ""),
                    "note_id": note_id
                }
        except Exception as e:
            utils.logger.error(f"[AICrawlerManager._get_weibo_note_content] 获取内容失败: {e}")
        return None

    async def crawl_bilibili(self) -> List[str]:
        """
        爬取B站数据（使用原始的BilibiliCrawler方式，稳定可靠）
        Returns:
            相关的视频ID列表
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

            # 直接使用原始的BilibiliCrawler，稳定可靠
            utils.logger.info("[AICrawlerManager] 使用原始BilibiliCrawler进行搜索和数据保存...")
            bili_crawler = BilibiliCrawler()
            await bili_crawler.start()
            
            utils.logger.info("[AICrawlerManager] B站搜索和数据保存完成")
            utils.logger.info("[AICrawlerManager] 注意：B站数据已保存到 data/bilibili/ 目录")

            # 从已保存的数据中读取video_id并进行相关性判断
            video_ids = await self._get_bilibili_video_ids_from_saved_data()
            
            utils.logger.info(f"[AICrawlerManager] 从已保存数据中读取到 {len(video_ids)} 个B站视频，开始进行相关性判断...")
            
            relevant_video_ids = []
            for video_id in video_ids:
                try:
                    video_content = await self._get_bilibili_video_content_from_saved_data(video_id)
                    if video_content:
                        relevance = await self.llm_agent.judge_relevance(
                            video_content,
                            self.event_description,
                            platform="bilibili"
                        )

                        if relevance["is_relevant"] or not config.ENABLE_RELEVANCE_FILTER:
                            relevant_video_ids.append(video_id)
                            utils.logger.info(
                                f"[AICrawlerManager] B站视频 {video_id} 相关 "
                                f"(评分: {relevance['score']:.2f}, 理由: {relevance['reason']})"
                            )
                        else:
                            utils.logger.info(
                                f"[AICrawlerManager] B站视频 {video_id} 不相关 "
                                f"(评分: {relevance['score']:.2f}, 理由: {relevance['reason']})"
                            )
                    await asyncio.sleep(0.5)  # 短暂延迟，避免API调用过快
                except Exception as e:
                    utils.logger.error(f"[AICrawlerManager] 处理B站视频 {video_id} 时出错: {e}")
                    continue

            self.relevant_note_ids["bilibili"] = relevant_video_ids
            utils.logger.info(f"[AICrawlerManager] B站相关性判断完成，相关视频: {len(relevant_video_ids)}/{len(video_ids)}")
            return relevant_video_ids

        finally:
            # 恢复原始配置
            config.PLATFORM = original_platform
            config.KEYWORDS = original_keywords
            config.COOKIES = original_cookies
            config.CRAWLER_TYPE = original_crawler_type
            config.HEADLESS = original_headless

    async def _get_bilibili_video_ids_from_saved_data(self) -> List[str]:
        """从已保存的数据中读取video_id列表"""
        video_ids = []
        try:
            import json
            import os
            from pathlib import Path
            
            # 从JSON文件读取
            json_dir = Path("data/bilibili/json")
            if json_dir.exists():
                for json_file in json_dir.glob("search_contents_*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    video_id = item.get("video_id")
                                    if video_id and video_id not in video_ids:
                                        video_ids.append(video_id)
                    except Exception as e:
                        utils.logger.error(f"[AICrawlerManager] 读取JSON文件 {json_file} 失败: {e}")
            
            # 从CSV文件读取
            csv_dir = Path("data/bilibili/csv")
            if csv_dir.exists():
                import csv
                for csv_file in csv_dir.glob("search_contents_*.csv"):
                    try:
                        with open(csv_file, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                video_id = row.get("video_id")
                                if video_id and video_id not in video_ids:
                                    video_ids.append(video_id)
                    except Exception as e:
                        utils.logger.error(f"[AICrawlerManager] 读取CSV文件 {csv_file} 失败: {e}")
            
            utils.logger.info(f"[AICrawlerManager] 从已保存数据中读取到 {len(video_ids)} 个B站video_id")
        except Exception as e:
            utils.logger.error(f"[AICrawlerManager._get_bilibili_video_ids_from_saved_data] 读取数据失败: {e}")
        
        return video_ids

    async def _get_bilibili_video_content_from_saved_data(self, video_id: str) -> Optional[Dict]:
        """从已保存的数据中读取视频内容用于相关性判断"""
        try:
            import json
            from pathlib import Path
            
            # 从JSON文件读取
            json_dir = Path("data/bilibili/json")
            if json_dir.exists():
                for json_file in json_dir.glob("search_contents_*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    if item.get("video_id") == video_id:
                                        return {
                                            "title": item.get("title", ""),
                                            "desc": item.get("desc", ""),
                                            "video_id": video_id
                                        }
                    except Exception as e:
                        utils.logger.error(f"[AICrawlerManager] 读取JSON文件 {json_file} 失败: {e}")
            
            # 从CSV文件读取
            csv_dir = Path("data/bilibili/csv")
            if csv_dir.exists():
                import csv
                for csv_file in csv_dir.glob("search_contents_*.csv"):
                    try:
                        with open(csv_file, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if row.get("video_id") == video_id:
                                    return {
                                        "title": row.get("title", ""),
                                        "desc": row.get("desc", ""),
                                        "video_id": video_id
                                    }
                    except Exception as e:
                        utils.logger.error(f"[AICrawlerManager] 读取CSV文件 {csv_file} 失败: {e}")
        except Exception as e:
            utils.logger.error(f"[AICrawlerManager._get_bilibili_video_content_from_saved_data] 获取内容失败: {e}")
        return None

    async def crawl_zhihu(self) -> List[str]:
        """
        爬取知乎数据
        Returns:
            相关的内容ID列表
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

            # 创建爬虫并执行搜索
            zhihu_crawler = ZhihuCrawler()
            await zhihu_crawler.start()

            # 获取搜索结果并进行相关性判断
            content_ids = await self._get_zhihu_content_ids_from_search(zhihu_crawler)

            relevant_content_ids = []
            for content_id in content_ids:
                content_data = await self._get_zhihu_content_data(zhihu_crawler, content_id)
                if content_data:
                    relevance = await self.llm_agent.judge_relevance(
                        content_data,
                        self.event_description,
                        platform="zhihu"
                    )

                    if relevance["is_relevant"] or not config.ENABLE_RELEVANCE_FILTER:
                        relevant_content_ids.append(content_id)
                        utils.logger.info(
                            f"[AICrawlerManager] 知乎内容 {content_id} 相关 "
                            f"(评分: {relevance['score']:.2f}, 理由: {relevance['reason']})"
                        )
                    else:
                        utils.logger.info(
                            f"[AICrawlerManager] 知乎内容 {content_id} 不相关 "
                            f"(评分: {relevance['score']:.2f}, 理由: {relevance['reason']})"
                        )

            self.relevant_note_ids["zhihu"] = relevant_content_ids
            return relevant_content_ids

        finally:
            # 恢复原始配置
            config.PLATFORM = original_platform
            config.KEYWORDS = original_keywords
            config.COOKIES = original_cookies
            config.CRAWLER_TYPE = original_crawler_type
            config.HEADLESS = original_headless
            config.ENABLE_GET_COMMENTS = original_enable_comments
            config.COOKIES = original_cookies
            
    async def _get_zhihu_content_ids_from_search(self, crawler: ZhihuCrawler) -> List[str]:
        """从搜索结果中提取内容ID"""
        content_ids = []
        try:
            from media_platform.zhihu.field import SearchSort, SearchType, SearchTime

            for keyword in self.keywords:
                for page in range(1, (config.CRAWLER_MAX_NOTES_COUNT // 20) + 2):
                    contents = await crawler.zhihu_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=20,
                        sort=SearchSort.DEFAULT,
                        note_type=SearchType.DEFAULT,
                        search_time=SearchTime.DEFAULT
                    )

                    for content in contents:
                        content_id = content.url
                        if content_id and content_id not in content_ids:
                            content_ids.append(content_id)

                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
        except Exception as e:
            utils.logger.error(f"[AICrawlerManager._get_zhihu_content_ids_from_search] 获取内容ID失败: {e}")
        return content_ids

    async def _get_zhihu_content_data(self, crawler: ZhihuCrawler, content_url: str) -> Optional[Dict]:
        """获取知乎内容用于相关性判断"""
        try:
            # 知乎的内容在搜索时已经包含了基本信息
            # 这里可以进一步获取详细内容，但为了效率，我们使用搜索返回的基本信息
            return {
                "url": content_url,
                "title": content_url.split("/")[-1]  # 简化处理
            }
        except Exception as e:
            utils.logger.error(f"[AICrawlerManager._get_zhihu_content_data] 获取内容失败: {e}")
        return None

    async def crawl_all_platforms(self):
        """爬取所有平台的数据"""
        utils.logger.info("[AICrawlerManager] 开始爬取所有平台数据...")

        # 提取关键词
        await self.extract_keywords()

        # 并行爬取三个平台
        results = await asyncio.gather(
            self.crawl_weibo(),
            self.crawl_bilibili(),
            # self.crawl_zhihu(),
            return_exceptions=True
        )

        utils.logger.info("[AICrawlerManager] 所有平台爬取完成")
        utils.logger.info(f"[AICrawlerManager] 微博相关内容: {len(self.relevant_note_ids['weibo'])}")
        utils.logger.info(f"[AICrawlerManager] B站相关视频: {len(self.relevant_note_ids['bilibili'])}")
        utils.logger.info(f"[AICrawlerManager] 知乎相关内容: {len(self.relevant_note_ids['zhihu'])}")

        return results


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
    
    # 执行爬取
    await manager.crawl_all_platforms()


if __name__ == "__main__":
    asyncio.run(main())
