# AI辅助自动化爬取系统 - 实现总结

## 项目概述

本系统在MediaCrawler项目基础上，实现了AI agent辅助的自动化爬取功能，支持微博、B站、知乎三个平台的多模态数据采集。

## 创建的文件

### 1. AI Agent模块

#### `ai_agent/__init__.py`
- AI Agent模块的初始化文件
- 导出 `LLMAgent` 类

#### `ai_agent/llm_agent.py`
- **LLMAgent类**：大语言模型Agent的核心实现
- **功能**：
  - `extract_keywords()`: 从热点事件描述中提取搜索关键词
  - `judge_relevance()`: 判断内容是否与事件相关
  - `_call_llm()`: 调用LLM API的底层方法
  - `_simple_relevance_check()`: 简单的关键词匹配fallback方法

### 2. 配置文件

#### `config/ai_agent_config.py`
- AI Agent的配置选项
- 包括：
  - LLM API配置（API密钥、Base URL、模型名称）
  - 关键词提取配置
  - 相关性判断配置

### 3. 主程序

#### `ai_crawler.py`
- **AICrawlerManager类**：AI辅助爬虫管理器
- **主要方法**：
  - `extract_keywords()`: 提取搜索关键词
  - `crawl_weibo()`: 爬取微博数据（包含search->detail的特殊处理）
  - `crawl_bilibili()`: 爬取B站数据
  - `crawl_zhihu()`: 爬取知乎数据
  - `crawl_all_platforms()`: 并行爬取所有平台
- **辅助方法**：
  - `_search_weibo_and_collect_note_ids_with_crawler()`: 搜索微博并收集note_id
  - `_get_weibo_note_content()`: 获取微博内容用于相关性判断
  - `_get_bilibili_video_ids_from_search()`: 从B站搜索结果提取视频ID
  - `_get_bilibili_video_content()`: 获取B站视频内容
  - `_get_zhihu_content_ids_from_search()`: 从知乎搜索结果提取内容ID
  - `_get_zhihu_content_data()`: 获取知乎内容

### 4. 文档和示例

#### `AI_CRAWLER_README.md`
- 详细的使用说明文档
- 包括安装、配置、使用方法等

#### `example_ai_crawler.py`
- 使用示例代码
- 包含三个示例：
  - 单个热点事件爬取
  - 自定义关键词爬取
  - 分步骤执行

## 核心特性

### 1. AI关键词提取
- 使用大语言模型从事件描述中智能提取搜索关键词
- 支持fallback机制，即使API不可用也能工作

### 2. AI相关性判断
- 对每个搜索结果进行智能相关性评分
- 可配置的阈值过滤
- 支持禁用相关性过滤（用于调试）

### 3. 微博特殊处理
- **问题**：微博search模式无法获取完整文本
- **解决方案**：
  1. 先使用search模式获取note_id列表
  2. 对每个note进行相关性判断
  3. 对相关note使用detail模式获取全文

### 4. 多平台支持
- **微博**：支持search和detail模式，自动处理全文获取
- **B站**：支持视频搜索和详情获取
- **知乎**：支持内容搜索和详情获取

### 5. 多模态数据
- 文本内容
- 图片（通过 `ENABLE_GET_MEIDAS` 配置）
- 视频（通过 `ENABLE_GET_MEIDAS` 配置）

### 6. 服务器运行支持
- 自动设置无头模式（`HEADLESS = True`）
- 支持CDP模式
- 资源自动清理

## 工作流程

```
1. 输入事件描述
   ↓
2. AI提取关键词
   ↓
3. 并行搜索三个平台
   ├─ 微博：search模式获取note_id
   ├─ B站：搜索视频
   └─ 知乎：搜索内容
   ↓
4. AI相关性判断
   ├─ 微博：判断每个note的相关性
   ├─ B站：判断每个视频的相关性
   └─ 知乎：判断每个内容的相关性
   ↓
5. 爬取相关内容详情
   ├─ 微博：detail模式获取全文
   ├─ B站：获取视频详情
   └─ 知乎：获取内容详情
   ↓
6. 保存多模态数据
```

## 配置要点

### 必须配置
1. **LLM API密钥**：在 `config/ai_agent_config.py` 或环境变量中设置
2. **无头模式**：`config/base_config.py` 中 `HEADLESS = True`
3. **媒体爬取**：`config/base_config.py` 中 `ENABLE_GET_MEIDAS = True`

### 可选配置
1. **相关性阈值**：`config/ai_agent_config.py` 中 `RELEVANCE_SCORE_THRESHOLD`
2. **关键词数量**：`config/ai_agent_config.py` 中 `MAX_KEYWORDS_PER_EVENT`
3. **数据保存方式**：`config/base_config.py` 中 `SAVE_DATA_OPTION`

## 使用示例

### 基本使用
```bash
python ai_crawler.py "某热点事件的具体描述"
```

### 编程使用
```python
from ai_crawler import AICrawlerManager
import asyncio

async def main():
    manager = AICrawlerManager("事件描述")
    await manager.crawl_all_platforms()

asyncio.run(main())
```

## 注意事项

1. **API密钥**：确保正确配置LLM API密钥
2. **登录状态**：首次运行需要登录各平台
3. **请求频率**：系统已内置请求间隔
4. **资源清理**：系统会自动清理浏览器上下文
5. **错误处理**：包含完善的错误处理和日志记录

## 扩展性

系统设计具有良好的扩展性：
- 可以轻松添加新平台
- 可以自定义相关性判断逻辑
- 可以调整AI提示词
- 可以添加新的数据源

## 技术栈

- **Python 3.9+**
- **Playwright**：浏览器自动化
- **httpx**：HTTP客户端（用于LLM API）
- **asyncio**：异步编程
- **大语言模型API**：OpenAI兼容API

## 后续改进建议

1. 添加更多平台的支持
2. 优化相关性判断的准确性
3. 添加数据去重功能
4. 支持增量爬取
5. 添加数据分析和可视化功能

