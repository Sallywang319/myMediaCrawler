# -*- coding: utf-8 -*-
# @Desc: 数据后处理Pipeline
# 功能：
# 1. 利用大模型相关性判断，将所有相关的条目存储在一个单独的json文件中
# 2. 将评论文件中（以search_comments_*.json或detail_comments_*.json为文件名）集成到原始的条目数据中
# 3. 支持自动去重

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import config
from ai_agent import LLMAgent
from media_platform.weibo import WeiboCrawler
from tools import utils
from cookies import WB_cookie


class DataPostProcessor:
    """数据后处理器"""

    def __init__(self, event_description: str):
        """
        初始化数据后处理器
        Args:
            event_description: 热点事件描述
        """
        self.event_description = event_description
        self.llm_agent = LLMAgent(
            api_key=config.LLM_API_KEY or None,
            base_url=config.LLM_BASE_URL or None,
            model=config.LLM_MODEL,
        )
        # 缓存已加载的数据，避免重复读取
        self._cached_data: Dict[str, Dict[str, Dict]] = {
            "weibo": {},
            "bilibili": {},
            "zhihu": {}
        }
        self.relevant_ids: Dict[str, List[str]] = {
            "weibo": [],
            "bilibili": [],
            "zhihu": []
        }

    def convert_ids_to_string(self, data):
        """
        将数据中的所有ID字段转换为字符串类型
        """
        if isinstance(data, list):
            for item in data:
                self.convert_ids_to_string(item)
        elif isinstance(data, dict):
            # 转换各种ID字段
            id_fields = ['note_id', 'comment_id', 'user_id', 'video_id',
                         'content_id', 'url', 'content_url']
            for field in id_fields:
                if field in data and data[field] is not None:
                    data[field] = str(data[field])

    async def load_all_platform_data(self) -> Dict[str, List[Dict]]:
        """一次性加载所有平台的数据"""
        utils.logger.info("[DataPostProcessor] 开始加载所有平台的数据...")

        weibo_data = await self._load_weibo_data()
        bilibili_data = await self._load_bilibili_data()
        zhihu_data = await self._load_zhihu_data()

        utils.logger.info(
            f"[DataPostProcessor] 数据加载完成 - 微博: {len(weibo_data)}, "
            f"B站: {len(bilibili_data)}, 知乎: {len(zhihu_data)}")

        return {
            "weibo": weibo_data,
            "bilibili": bilibili_data,
            "zhihu": zhihu_data
        }

    async def _load_weibo_data(self) -> List[Dict]:
        """加载所有已存储的微博数据"""
        all_data = []
        try:
            json_dir = Path("data/weibo/json")
            if json_dir.exists():
                for json_file in json_dir.glob("search_contents_*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                all_data.extend(data)
                    except Exception as e:
                        utils.logger.error(
                            f"[DataPostProcessor] 读取JSON文件 {json_file} 失败: {e}")

            # 去重：使用note_id作为唯一标识，并缓存数据
            seen_ids = set()
            unique_data = []
            for item in all_data:
                note_id = item.get("note_id")
                if note_id and note_id not in seen_ids:
                    seen_ids.add(note_id)
                    unique_data.append(item)
                    # 缓存数据，以note_id为key
                    self._cached_data["weibo"][str(note_id)] = item

            utils.logger.info(
                f"[DataPostProcessor] 加载微博数据: {len(unique_data)} 条（去重后）")
            return unique_data
        except Exception as e:
            utils.logger.error(
                f"[DataPostProcessor._load_weibo_data] 加载数据失败: {e}")
            return []

    async def _load_bilibili_data(self) -> List[Dict]:
        """加载所有已存储的B站数据"""
        all_data = []
        try:
            json_dir = Path("data/bilibili/json")
            if json_dir.exists():
                for json_file in json_dir.glob("search_contents_*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                all_data.extend(data)
                    except Exception as e:
                        utils.logger.error(
                            f"[DataPostProcessor] 读取JSON文件 {json_file} 失败: {e}")

            # 去重：使用video_id作为唯一标识，并缓存数据
            seen_ids = set()
            unique_data = []
            for item in all_data:
                video_id = item.get("video_id")
                if video_id and video_id not in seen_ids:
                    seen_ids.add(video_id)
                    unique_data.append(item)
                    # 缓存数据，以video_id为key
                    self._cached_data["bilibili"][str(video_id)] = item

            utils.logger.info(
                f"[DataPostProcessor] 加载B站数据: {len(unique_data)} 条（去重后）")
            return unique_data
        except Exception as e:
            utils.logger.error(
                f"[DataPostProcessor._load_bilibili_data] 加载数据失败: {e}")
            return []

    async def _load_zhihu_data(self) -> List[Dict]:
        """加载所有已存储的知乎数据"""
        all_data = []
        try:
            json_dir = Path("data/zhihu/json")
            if json_dir.exists():
                for json_file in json_dir.glob("search_contents_*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                all_data.extend(data)
                    except Exception as e:
                        utils.logger.error(
                            f"[DataPostProcessor] 读取JSON文件 {json_file} 失败: {e}")

            # 去重：使用url/content_url/content_id作为唯一标识，并缓存数据
            seen_ids = set()
            unique_data = []
            for item in all_data:
                content_id = item.get("url") or item.get(
                    "content_url") or item.get("content_id")
                if content_id and content_id not in seen_ids:
                    seen_ids.add(content_id)
                    unique_data.append(item)
                    # 缓存数据，以content_id为key
                    self._cached_data["zhihu"][str(content_id)] = item

            utils.logger.info(
                f"[DataPostProcessor] 加载知乎数据: {len(unique_data)} 条（去重后）")
            return unique_data
        except Exception as e:
            utils.logger.error(
                f"[DataPostProcessor._load_zhihu_data] 加载数据失败: {e}")
            return []

    async def judge_relevance(self, all_data: Dict[str, List[Dict]]):
        """对所有数据进行相关性判断"""
        utils.logger.info("[DataPostProcessor] 开始对所有数据进行相关性判断...")

        # 对微博数据进行相关性判断
        utils.logger.info("[DataPostProcessor] 开始对微博数据进行相关性判断...")
        relevant_weibo_ids = []
        for item in all_data["weibo"]:
            try:
                note_id = item.get("note_id")
                if not note_id:
                    continue

                content = item.get("content", "")
                relevance = await self.llm_agent.judge_relevance(
                    {"content": content, "note_id": note_id},
                    self.event_description,
                    platform="weibo"
                )

                if relevance["is_relevant"] or not config.ENABLE_RELEVANCE_FILTER:
                    relevant_weibo_ids.append(str(note_id))
                    utils.logger.info(
                        f"[DataPostProcessor] 微博 {note_id} 相关 "
                        f"(评分: {relevance['score']:.2f}, 理由: {relevance['reason']})"
                    )
                else:
                    utils.logger.debug(
                        f"[DataPostProcessor] 微博 {note_id} 不相关 "
                        f"(评分: {relevance['score']:.2f})"
                    )
                await asyncio.sleep(0.3)  # 短暂延迟，避免API调用过快
            except Exception as e:
                utils.logger.error(f"[DataPostProcessor] 处理微博数据时出错: {e}")
                continue

        # 对B站数据进行相关性判断
        utils.logger.info("[DataPostProcessor] 开始对B站数据进行相关性判断...")
        relevant_bilibili_ids = []
        for item in all_data["bilibili"]:
            try:
                video_id = item.get("video_id")
                if not video_id:
                    continue

                title = item.get("title", "")
                desc = item.get("desc", "")
                relevance = await self.llm_agent.judge_relevance(
                    {"title": title, "desc": desc, "video_id": video_id},
                    self.event_description,
                    platform="bilibili"
                )

                if relevance["is_relevant"] or not config.ENABLE_RELEVANCE_FILTER:
                    relevant_bilibili_ids.append(str(video_id))
                    utils.logger.info(
                        f"[DataPostProcessor] B站视频 {video_id} 相关 "
                        f"(评分: {relevance['score']:.2f}, 理由: {relevance['reason']})"
                    )
                else:
                    utils.logger.debug(
                        f"[DataPostProcessor] B站视频 {video_id} 不相关 "
                        f"(评分: {relevance['score']:.2f})"
                    )
                await asyncio.sleep(0.3)
            except Exception as e:
                utils.logger.error(f"[DataPostProcessor] 处理B站数据时出错: {e}")
                continue

        # 对知乎数据进行相关性判断
        utils.logger.info("[DataPostProcessor] 开始对知乎数据进行相关性判断...")
        relevant_zhihu_ids = []
        for item in all_data["zhihu"]:
            try:
                content_id = item.get("url") or item.get(
                    "content_url") or item.get("content_id")
                if not content_id:
                    continue

                title = item.get("title", "")
                content = item.get("content", "")
                relevance = await self.llm_agent.judge_relevance(
                    {"url": content_id, "title": title, "content": content},
                    self.event_description,
                    platform="zhihu"
                )

                if relevance["is_relevant"] or not config.ENABLE_RELEVANCE_FILTER:
                    relevant_zhihu_ids.append(str(content_id))
                    utils.logger.info(
                        f"[DataPostProcessor] 知乎内容 {content_id} 相关 "
                        f"(评分: {relevance['score']:.2f}, 理由: {relevance['reason']})"
                    )
                else:
                    utils.logger.debug(
                        f"[DataPostProcessor] 知乎内容 {content_id} 不相关 "
                        f"(评分: {relevance['score']:.2f})"
                    )
                await asyncio.sleep(0.3)
            except Exception as e:
                utils.logger.error(f"[DataPostProcessor] 处理知乎数据时出错: {e}")
                continue

        # 保存相关性判断结果
        self.relevant_ids["weibo"] = relevant_weibo_ids
        self.relevant_ids["bilibili"] = relevant_bilibili_ids
        self.relevant_ids["zhihu"] = relevant_zhihu_ids

        utils.logger.info(
            f"[DataPostProcessor] 相关性判断完成 - 微博: {len(relevant_weibo_ids)}/{len(all_data['weibo'])}, "
            f"B站: {len(relevant_bilibili_ids)}/{len(all_data['bilibili'])}, "
            f"知乎: {len(relevant_zhihu_ids)}/{len(all_data['zhihu'])}")

    async def get_weibo_detail_content(self):
        """
        对相关的微博使用detail模式获取完整内容，并更新缓存数据
        """
        if not self.relevant_ids["weibo"]:
            utils.logger.info("[DataPostProcessor] 没有相关的微博数据，跳过detail模式获取")
            return

        utils.logger.info(
            f"[DataPostProcessor] 开始对 {len(self.relevant_ids['weibo'])} 个相关微博使用detail模式获取完整内容...")

        # 保存原始配置
        original_platform = config.PLATFORM
        original_cookies = config.COOKIES
        original_crawler_type = config.CRAWLER_TYPE
        original_headless = config.HEADLESS
        original_enable_comments = config.ENABLE_GET_COMMENTS
        original_weibo_specified_id_list = getattr(
            config, 'WEIBO_SPECIFIED_ID_LIST', [])[:]

        try:
            # 设置微博配置为detail模式
            config.PLATFORM = "wb"
            config.COOKIES = WB_cookie
            config.CRAWLER_TYPE = "detail"
            config.WEIBO_SPECIFIED_ID_LIST = self.relevant_ids["weibo"]
            config.HEADLESS = True
            config.ENABLE_GET_COMMENTS = True

            # 使用detail模式再次爬取
            weibo_crawler_detail = WeiboCrawler()
            await weibo_crawler_detail.start()
            utils.logger.info("[DataPostProcessor] 微博detail模式爬取完成，已获取完整内容")

            # 从detail模式的结果中读取完整内容，更新缓存数据
            await self._update_weibo_content_from_detail()

        finally:
            # 恢复原始配置
            config.PLATFORM = original_platform
            config.COOKIES = original_cookies
            config.CRAWLER_TYPE = original_crawler_type
            config.HEADLESS = original_headless
            config.ENABLE_GET_COMMENTS = original_enable_comments
            if hasattr(config, 'WEIBO_SPECIFIED_ID_LIST'):
                config.WEIBO_SPECIFIED_ID_LIST[:] = original_weibo_specified_id_list

    async def _update_weibo_content_from_detail(self):
        """
        从detail模式的结果中读取完整内容，更新缓存数据中的content字段
        """
        utils.logger.info("[DataPostProcessor] 开始更新微博完整内容...")

        updated_count = 0
        json_dir = Path("data/weibo/json")

        if not json_dir.exists():
            utils.logger.warning("[DataPostProcessor] 微博JSON目录不存在，跳过内容更新")
            return

        # 查找detail模式生成的文件
        detail_files = list(json_dir.glob("detail_contents_*.json"))

        if not detail_files:
            utils.logger.warning("[DataPostProcessor] 未找到detail模式生成的文件，跳过内容更新")
            return

        for detail_file in detail_files:
            try:
                with open(detail_file, 'r', encoding='utf-8') as f:
                    detail_data = json.load(f)

                # 统一ID为字符串
                self.convert_ids_to_string(detail_data)

                # 处理可能是dict格式的数据
                if isinstance(detail_data, dict):
                    for key, value in detail_data.items():
                        if isinstance(value, list) and value:
                            detail_data = value
                            break

                if isinstance(detail_data, list):
                    for detail_item in detail_data:
                        note_id = detail_item.get("note_id")
                        content = detail_item.get("content", "")

                        if note_id and content:
                            note_id_str = str(note_id)
                            # 更新缓存数据中的content
                            if note_id_str in self._cached_data["weibo"]:
                                original_content = self._cached_data["weibo"][note_id_str].get(
                                    "content", "")
                                if content != original_content:
                                    self._cached_data["weibo"][note_id_str]["content"] = content
                                    updated_count += 1
                                    utils.logger.debug(
                                        f"[DataPostProcessor] 已更新微博 {note_id_str} 的完整内容")

                utils.logger.info(
                    f"[DataPostProcessor] 从 {detail_file.name} 更新了微博内容")

            except Exception as e:
                utils.logger.error(
                    f"[DataPostProcessor] 读取detail文件 {detail_file} 失败: {e}")
                continue

        utils.logger.info(
            f"[DataPostProcessor] 微博内容更新完成，共更新 {updated_count} 条微博的完整内容")

    def load_comments(self) -> Dict[str, Dict[str, List[Dict]]]:
        """
        加载所有评论文件
        返回格式: {platform: {item_id: [comments]}}
        """
        utils.logger.info("[DataPostProcessor] 开始加载评论文件...")
        comments_data = {
            "weibo": defaultdict(list),
            "bilibili": defaultdict(list),
            "zhihu": defaultdict(list)
        }

        # 加载微博评论
        weibo_comments_dir = Path("data/weibo/json")
        if weibo_comments_dir.exists():
            for comments_file in weibo_comments_dir.glob("*comments_*.json"):
                try:
                    with open(comments_file, 'r', encoding='utf-8') as f:
                        comments = json.load(f)

                    # 统一ID为字符串
                    self.convert_ids_to_string(comments)

                    # 处理可能是dict格式的数据
                    if isinstance(comments, dict):
                        for key, value in comments.items():
                            if isinstance(value, list) and value:
                                comments = value
                                break

                    if isinstance(comments, list):
                        for comment in comments:
                            note_id = comment.get("note_id")
                            if note_id:
                                comments_data["weibo"][str(
                                    note_id)].append(comment)

                    utils.logger.info(
                        f"[DataPostProcessor] 从 {comments_file.name} 加载了评论")
                except Exception as e:
                    utils.logger.error(
                        f"[DataPostProcessor] 读取评论文件 {comments_file} 失败: {e}")

        # 加载B站评论（如果有）
        bilibili_comments_dir = Path("data/bilibili/json")
        if bilibili_comments_dir.exists():
            for comments_file in bilibili_comments_dir.glob("*comments_*.json"):
                try:
                    with open(comments_file, 'r', encoding='utf-8') as f:
                        comments = json.load(f)

                    self.convert_ids_to_string(comments)

                    if isinstance(comments, dict):
                        for key, value in comments.items():
                            if isinstance(value, list) and value:
                                comments = value
                                break

                    if isinstance(comments, list):
                        for comment in comments:
                            video_id = comment.get(
                                "video_id") or comment.get("bvid")
                            if video_id:
                                comments_data["bilibili"][str(
                                    video_id)].append(comment)

                    utils.logger.info(
                        f"[DataPostProcessor] 从 {comments_file.name} 加载了评论")
                except Exception as e:
                    utils.logger.error(
                        f"[DataPostProcessor] 读取评论文件 {comments_file} 失败: {e}")

        # 加载知乎评论（如果有）
        zhihu_comments_dir = Path("data/zhihu/json")
        if zhihu_comments_dir.exists():
            for comments_file in zhihu_comments_dir.glob("*comments_*.json"):
                try:
                    with open(comments_file, 'r', encoding='utf-8') as f:
                        comments = json.load(f)

                    self.convert_ids_to_string(comments)

                    if isinstance(comments, dict):
                        for key, value in comments.items():
                            if isinstance(value, list) and value:
                                comments = value
                                break

                    if isinstance(comments, list):
                        for comment in comments:
                            content_id = comment.get("url") or comment.get(
                                "content_url") or comment.get("content_id")
                            if content_id:
                                comments_data["zhihu"][str(
                                    content_id)].append(comment)

                    utils.logger.info(
                        f"[DataPostProcessor] 从 {comments_file.name} 加载了评论")
                except Exception as e:
                    utils.logger.error(
                        f"[DataPostProcessor] 读取评论文件 {comments_file} 失败: {e}")

        total_comments = sum(len(comments) for platform_comments in comments_data.values()
                             for comments in platform_comments.values())
        utils.logger.info(
            f"[DataPostProcessor] 评论加载完成，共加载 {total_comments} 条评论")

        return comments_data

    def merge_comments_to_data(self, all_data: Dict[str, List[Dict]],
                               comments_data: Dict[str, Dict[str, List[Dict]]]):
        """
        将评论集成到原始数据中
        """
        utils.logger.info("[DataPostProcessor] 开始集成评论到原始数据...")

        # 为微博数据添加评论
        for item in all_data["weibo"]:
            note_id = str(item.get("note_id", ""))
            if note_id in comments_data["weibo"]:
                item["comments"] = comments_data["weibo"][note_id]
            else:
                item["comments"] = []

        # 为B站数据添加评论
        for item in all_data["bilibili"]:
            video_id = str(item.get("video_id", ""))
            if video_id in comments_data["bilibili"]:
                item["comments"] = comments_data["bilibili"][video_id]
            else:
                item["comments"] = []

        # 为知乎数据添加评论
        for item in all_data["zhihu"]:
            content_id = str(item.get("url") or item.get(
                "content_url") or item.get("content_id", ""))
            if content_id in comments_data["zhihu"]:
                item["comments"] = comments_data["zhihu"][content_id]
            else:
                item["comments"] = []

        weibo_with_comments = sum(
            1 for item in all_data["weibo"] if item.get("comments"))
        bilibili_with_comments = sum(
            1 for item in all_data["bilibili"] if item.get("comments"))
        zhihu_with_comments = sum(
            1 for item in all_data["zhihu"] if item.get("comments"))

        utils.logger.info(
            f"[DataPostProcessor] 评论集成完成 - 微博: {weibo_with_comments}, "
            f"B站: {bilibili_with_comments}, 知乎: {zhihu_with_comments}")

    async def save_relevant_data(self, all_data: Dict[str, List[Dict]]):
        """
        将所有平台的相关数据收集并存储到一个JSON文件中，支持去重
        """
        utils.logger.info("[DataPostProcessor] 开始收集并存储所有平台的相关数据...")

        try:
            # 用于去重的集合，使用(platform, id)作为唯一标识
            seen_ids = set()
            all_relevant_data = []

            # 收集微博相关数据
            for note_id in self.relevant_ids["weibo"]:
                unique_key = ("weibo", note_id)
                if unique_key not in seen_ids:
                    seen_ids.add(unique_key)
                    if note_id in self._cached_data["weibo"]:
                        note_data = self._cached_data["weibo"][note_id].copy()
                        note_data["platform"] = "weibo"
                        note_data["relevance_id"] = note_id
                        all_relevant_data.append(note_data)

            # 收集B站相关数据
            for video_id in self.relevant_ids["bilibili"]:
                unique_key = ("bilibili", video_id)
                if unique_key not in seen_ids:
                    seen_ids.add(unique_key)
                    if video_id in self._cached_data["bilibili"]:
                        video_data = self._cached_data["bilibili"][video_id].copy(
                        )
                        video_data["platform"] = "bilibili"
                        video_data["relevance_id"] = video_id
                        all_relevant_data.append(video_data)

            # 收集知乎相关数据
            for content_id in self.relevant_ids["zhihu"]:
                unique_key = ("zhihu", content_id)
                if unique_key not in seen_ids:
                    seen_ids.add(unique_key)
                    if content_id in self._cached_data["zhihu"]:
                        zhihu_data = self._cached_data["zhihu"][content_id].copy(
                        )
                        zhihu_data["platform"] = "zhihu"
                        zhihu_data["relevance_id"] = content_id
                        all_relevant_data.append(zhihu_data)

            # 统一ID为字符串
            self.convert_ids_to_string(all_relevant_data)

            # 保存到JSON文件
            if all_relevant_data:
                # 创建输出目录
                output_dir = Path("data/relevant")
                output_dir.mkdir(parents=True, exist_ok=True)

                # 生成文件名（包含时间戳）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = output_dir / f"relevant_data_{timestamp}.json"

                # 保存数据
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_relevant_data, f,
                              ensure_ascii=False, indent=2)

                utils.logger.info(
                    f"[DataPostProcessor] 已保存 {len(all_relevant_data)} 条相关数据到 {output_file}")

                # 同时保存一个latest文件，方便查看最新数据
                latest_file = output_dir / "relevant_data_latest.json"
                with open(latest_file, 'w', encoding='utf-8') as f:
                    json.dump(all_relevant_data, f,
                              ensure_ascii=False, indent=2)
                utils.logger.info(
                    f"[DataPostProcessor] 已更新最新数据文件: {latest_file}")
            else:
                utils.logger.warning("[DataPostProcessor] 没有找到相关数据，跳过保存")

        except Exception as e:
            utils.logger.error(
                f"[DataPostProcessor.save_relevant_data] 保存相关数据失败: {e}")

    async def process(self):
        """执行完整的数据后处理流程"""
        utils.logger.info("[DataPostProcessor] 开始数据后处理流程...")

        # 第一步：加载所有平台的数据
        all_data = await self.load_all_platform_data()

        # 第二步：相关性判断
        await self.judge_relevance(all_data)

        # 第三步：对相关的微博使用detail模式获取完整内容
        await self.get_weibo_detail_content()

        # 第四步：加载评论数据
        comments_data = self.load_comments()

        # 第五步：将评论集成到原始数据中
        self.merge_comments_to_data(all_data, comments_data)

        # 第六步：保存相关数据（只保存相关的数据）
        await self.save_relevant_data(all_data)

        utils.logger.info("[DataPostProcessor] 数据后处理流程完成")
        utils.logger.info(
            f"[DataPostProcessor] 最终结果 - 微博相关内容: {len(self.relevant_ids['weibo'])}")
        utils.logger.info(
            f"[DataPostProcessor] 最终结果 - B站相关视频: {len(self.relevant_ids['bilibili'])}")
        utils.logger.info(
            f"[DataPostProcessor] 最终结果 - 知乎相关内容: {len(self.relevant_ids['zhihu'])}")


async def main():
    """主函数"""
    # 从命令行参数或环境变量获取事件描述
    if len(sys.argv) > 1:
        event_description = " ".join(sys.argv[1:])
    else:
        event_description = os.getenv("EVENT_DESCRIPTION", "")
        if not event_description:
            print("请提供热点事件描述作为参数，或设置环境变量 EVENT_DESCRIPTION")
            print("示例: python data_postprocessor.py '某热点事件的具体描述'")
            return

    # 创建数据后处理器
    processor = DataPostProcessor(event_description)

    try:
        # 执行后处理
        await processor.process()
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
            utils.logger.info(f"[DataPostProcessor] 清理 {len(tasks)} 个待处理任务...")
            # 取消所有待处理的任务
            for task in tasks:
                task.cancel()

            # 等待所有任务完成取消
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        utils.logger.debug(f"[DataPostProcessor] 清理任务时出错: {e}")


if __name__ == "__main__":
    asyncio.run(main())
