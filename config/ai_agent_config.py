# -*- coding: utf-8 -*-
# AI Agent配置

# LLM API配置
# 支持OpenAI兼容的API（如OpenAI、Azure OpenAI、其他兼容服务）
LLM_API_KEY = "sk-bb7d300e671f4237acc88ee011ed9204"  # 如果为空，将从环境变量 OPENAI_API_KEY 或 LLM_API_KEY 读取
LLM_BASE_URL = (
    "https://api.deepseek.com/v1"  # 如果为空，将使用默认值 https://api.openai.com/v1
)
LLM_MODEL = "deepseek-chat"  # 模型名称，如 gpt-4o-mini, gpt-4, gpt-3.5-turbo 等

# 关键词提取配置
MAX_KEYWORDS_PER_EVENT = 5  # 每个事件最多提取的关键词数量

# 相关性判断配置
RELEVANCE_SCORE_THRESHOLD = 0.5  # 相关性评分阈值，超过此值认为相关
ENABLE_RELEVANCE_FILTER = True  # 是否启用相关性过滤

# 是否在判断相关性时显示详细信息
VERBOSE_RELEVANCE_JUDGMENT = True
