# -*- coding: utf-8 -*-
# @Desc: AI Agent模块，用于关键词提取和相关性判断

import json
import os
from typing import Dict, List, Optional

import httpx
from tools import utils


class LLMAgent:
    """大语言模型Agent，用于关键词提取和相关性判断"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        timeout: int = 60,
    ):
        """
        初始化LLM Agent
        Args:
            api_key: API密钥，如果为None则从环境变量读取
            base_url: API基础URL，如果为None则使用默认值
            model: 模型名称
            timeout: 请求超时时间
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.timeout = timeout
        
        if not self.api_key:
            utils.logger.warning("[LLMAgent] 未设置API密钥，AI功能将不可用")
    
    async def extract_keywords(self, event_description: str, max_keywords: int = 5) -> List[str]:
        """
        从热点事件描述中提取搜索关键词
        Args:
            event_description: 热点事件描述
            max_keywords: 最大关键词数量
        Returns:
            关键词列表
        """
        if not self.api_key:
            utils.logger.warning("[LLMAgent.extract_keywords] API密钥未设置，返回默认关键词")
            # 简单分词作为fallback
            return event_description.split()[:max_keywords]
        
        prompt = f"""你是一个信息检索专家。请从以下热点事件描述中提取{max_keywords}个最有效的搜索关键词，这些关键词应该能够帮助在社交媒体平台上找到与该事件相关的内容。

事件描述：
{event_description}

要求：
1. 提取的关键词应该简洁、准确，适合在微博、B站、知乎等平台搜索
2. 关键词应该涵盖事件的核心要素（人物、地点、时间、事件类型等）
3. 每个关键词长度控制在2-10个字符
4. 优先选择具有区分度的关键词

请以JSON格式返回，格式如下：
{{
    "keywords": ["关键词1", "关键词2", "关键词3", ...]
}}

只返回JSON，不要包含其他文字说明。"""

        try:
            response = await self._call_llm(prompt)
            # 尝试解析JSON响应
            if isinstance(response, str):
                # 尝试提取JSON部分
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()
                
                try:
                    result = json.loads(response)
                    keywords = result.get("keywords", [])
                    if keywords:
                        utils.logger.info(f"[LLMAgent.extract_keywords] 提取的关键词: {keywords}")
                        return keywords[:max_keywords]
                except json.JSONDecodeError:
                    utils.logger.warning(f"[LLMAgent.extract_keywords] JSON解析失败，响应: {response}")
            
            # Fallback: 简单分词
            keywords = event_description.replace("，", ",").replace("。", ".").split(",")
            keywords = [k.strip() for k in keywords if k.strip()][:max_keywords]
            utils.logger.info(f"[LLMAgent.extract_keywords] 使用fallback关键词: {keywords}")
            return keywords
            
        except Exception as e:
            utils.logger.error(f"[LLMAgent.extract_keywords] 提取关键词失败: {e}")
            # Fallback: 简单分词
            keywords = event_description.replace("，", ",").replace("。", ".").split(",")
            keywords = [k.strip() for k in keywords if k.strip()][:max_keywords]
            return keywords
    
    async def judge_relevance(
        self,
        content: Dict,
        event_description: str,
        platform: str = "unknown"
    ) -> Dict[str, any]:
        """
        判断内容是否与事件相关
        Args:
            content: 内容字典，包含title/content等字段
            event_description: 事件描述
            platform: 平台名称（weibo/bilibili/zhihu）
        Returns:
            包含is_relevant(是否相关)和reason(原因)的字典
        """
        if not self.api_key:
            utils.logger.warning("[LLMAgent.judge_relevance] API密钥未设置，默认返回相关")
            return {"is_relevant": True, "reason": "API未配置，默认相关", "score": 0.5}
        
        # 提取内容文本
        content_text = ""
        if platform == "weibo":
            content_text = content.get("content", "") or content.get("text", "")
        elif platform == "bilibili":
            content_text = content.get("title", "") + " " + content.get("desc", "")
        elif platform == "zhihu":
            content_text = content.get("title", "") + " " + content.get("content", "")
        else:
            content_text = str(content.get("title", "")) + " " + str(content.get("content", ""))
        
        if not content_text or len(content_text.strip()) < 10:
            return {"is_relevant": False, "reason": "内容文本过短", "score": 0.0}
        
        # 限制内容长度，避免token过多
        if len(content_text) > 1000:
            content_text = content_text[:1000] + "..."
        
        prompt = f"""你是一个内容相关性判断专家。请判断以下社交媒体内容是否与给定的事件描述相关。

事件描述：
{event_description}

内容（来自{platform}平台）：
{content_text}

要求：
1. 判断内容是否与事件描述相关（直接相关、间接相关、不相关）
2. 相关性评分范围0-1，0.5以上认为相关
3. 简要说明判断理由

请以JSON格式返回，格式如下：
{{
    "is_relevant": true/false,
    "score": 0.0-1.0,
    "reason": "判断理由"
}}

只返回JSON，不要包含其他文字说明。"""

        try:
            response = await self._call_llm(prompt)
            
            # 尝试解析JSON响应
            if isinstance(response, str):
                # 尝试提取JSON部分
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()
                
                try:
                    result = json.loads(response)
                    is_relevant = result.get("is_relevant", False)
                    score = result.get("score", 0.0)
                    reason = result.get("reason", "未提供理由")
                    
                    utils.logger.info(
                        f"[LLMAgent.judge_relevance] 相关性判断: {is_relevant}, "
                        f"评分: {score}, 理由: {reason}"
                    )
                    return {
                        "is_relevant": is_relevant,
                        "score": score,
                        "reason": reason
                    }
                except json.JSONDecodeError:
                    utils.logger.warning(f"[LLMAgent.judge_relevance] JSON解析失败，响应: {response}")
            
            # Fallback: 简单关键词匹配
            return self._simple_relevance_check(content_text, event_description)
            
        except Exception as e:
            utils.logger.error(f"[LLMAgent.judge_relevance] 相关性判断失败: {e}")
            # Fallback: 简单关键词匹配
            return self._simple_relevance_check(content_text, event_description)
    
    def _simple_relevance_check(self, content_text: str, event_description: str) -> Dict:
        """简单的关键词匹配作为fallback"""
        # 提取事件描述中的关键词
        event_keywords = set(event_description.replace("，", ",").replace("。", ".").split())
        content_words = set(content_text.split())
        
        # 计算交集比例
        intersection = event_keywords & content_words
        if len(event_keywords) > 0:
            score = len(intersection) / len(event_keywords)
        else:
            score = 0.0
        
        is_relevant = score > 0.2  # 简单的阈值
        
        return {
            "is_relevant": is_relevant,
            "score": min(score, 1.0),
            "reason": f"关键词匹配度: {len(intersection)}/{len(event_keywords)}"
        }
    
    async def _call_llm(self, prompt: str) -> str:
        """
        调用LLM API
        Args:
            prompt: 提示词
        Returns:
            LLM响应文本
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的信息检索和分析助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

