# -*- coding: utf-8 -*-
# @Desc: AI辅助爬取系统使用示例

"""
这是一个简化的使用示例，展示如何使用AI辅助爬取系统
"""

import asyncio
from ai_crawler import AICrawlerManager


async def example_single_event():
    """示例1：爬取单个热点事件"""
    event_description = """
    某科技公司于2024年发布了一款新的智能手机产品，
    该产品采用了最新的AI芯片技术，引发了广泛的市场讨论和用户关注。
    请帮我收集相关的社交媒体讨论内容。
    """
    
    manager = AICrawlerManager(event_description)
    await manager.crawl_all_platforms()
    
    print(f"微博相关内容: {len(manager.relevant_note_ids['weibo'])}")
    print(f"B站相关视频: {len(manager.relevant_note_ids['bilibili'])}")
    print(f"知乎相关内容: {len(manager.relevant_note_ids['zhihu'])}")


async def example_custom_keywords():
    """示例2：使用自定义关键词（跳过AI提取）"""
    # 如果你已经有明确的关键词，可以直接设置
    event_description = "某热点事件"
    manager = AICrawlerManager(event_description)
    
    # 手动设置关键词，跳过AI提取
    manager.keywords = ["关键词1", "关键词2", "关键词3"]
    
    # 只爬取特定平台
    await manager.crawl_weibo()
    # await manager.crawl_bilibili()
    # await manager.crawl_zhihu()


async def example_step_by_step():
    """示例3：分步骤执行，便于调试"""
    event_description = "某热点事件描述"
    manager = AICrawlerManager(event_description)
    
    # 步骤1：提取关键词
    keywords = await manager.extract_keywords()
    print(f"提取的关键词: {keywords}")
    
    # 步骤2：爬取微博
    weibo_ids = await manager.crawl_weibo()
    print(f"微博相关ID: {weibo_ids}")
    
    # 步骤3：爬取B站
    bili_ids = await manager.crawl_bilibili()
    print(f"B站相关ID: {bili_ids}")
    
    # 步骤4：爬取知乎
    zhihu_ids = await manager.crawl_zhihu()
    print(f"知乎相关ID: {zhihu_ids}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_single_event())
    
    # 或者运行其他示例
    # asyncio.run(example_custom_keywords())
    # asyncio.run(example_step_by_step())

