# 数据存储问题快速修复说明

## 问题原因

在AI辅助爬取系统中，数据存储发生在以下时机：

1. **微博平台**：
   - ✅ **搜索阶段**：已修复，现在会立即保存每个搜索到的note
   - ⚠️ **相关性判断阶段**：不保存数据，只判断
   - ✅ **Detail阶段**：更新已保存的数据，获取完整文本

2. **B站/知乎平台**：
   - ✅ **搜索阶段**：使用原始爬虫逻辑，会自动保存
   - ⚠️ **相关性判断阶段**：不保存数据，只判断

## 已修复的问题

### 微博搜索阶段立即保存
在 `ai_crawler.py` 的 `_search_weibo_and_collect_note_ids_with_crawler()` 方法中，现在会：
- 每搜索到一个note，立即调用 `weibo_store.update_weibo_note()` 保存
- 如果开启了媒体爬取，也会保存图片
- 立即写入磁盘（JSON/CSV）或数据库

## 数据存储位置

根据 `config/base_config.py` 中的 `SAVE_DATA_OPTION`：

- **json**: `data/{platform}/json/` 目录
- **csv**: `data/{platform}/csv/` 目录  
- **sqlite/db**: 数据库文件

## 如果程序中断

### 中断在搜索阶段
- ✅ **微博**：已保存的数据在 `data/weibo/json/` 或 `data/weibo/csv/` 目录
- ✅ **B站/知乎**：已保存的数据在对应目录
- ⚠️ **注意**：微博数据可能不完整（缺少完整文本），需要运行Detail模式

### 中断在相关性判断阶段
- ✅ 搜索阶段的数据已保存
- ⚠️ 可能包含不相关内容（未经过AI过滤）

### 中断在Detail阶段
- ✅ 搜索阶段的数据已保存
- ⚠️ 微博数据可能缺少完整文本

## 验证数据是否保存

### 方法1：检查文件
```bash
# 检查JSON文件
ls -lh data/weibo/json/
ls -lh data/bilibili/json/
ls -lh data/zhihu/json/

# 检查CSV文件
ls -lh data/weibo/csv/
```

### 方法2：查看日志
日志中会显示：
```
[AICrawlerManager] 已保存微博note: {note_id} (搜索阶段)
[store.weibo.update_weibo_note] weibo note id:xxx, title:xxx ...
```

### 方法3：检查数据库
如果使用数据库存储：
```python
# SQLite
sqlite3 data/mediacrawler.db
SELECT COUNT(*) FROM weibo_note;

# MySQL
mysql -u user -p database_name
SELECT COUNT(*) FROM weibo_note;
```

## 建议

1. **使用数据库存储**：更安全，有事务保护
   ```python
   SAVE_DATA_OPTION = "sqlite"  # 推荐
   ```

2. **等待程序完成**：确保Detail模式执行完成，获取完整数据

3. **定期检查**：在程序运行过程中，定期检查 `data/` 目录

4. **查看日志**：关注日志中的保存信息，确认数据正在保存

## 如果数据没有保存

1. **检查配置**：确认 `SAVE_DATA_OPTION` 配置正确
2. **检查权限**：确认 `data/` 目录有写入权限
3. **查看日志**：检查是否有保存错误
4. **检查磁盘空间**：确认磁盘有足够空间

## 数据完整性说明

- **搜索阶段保存的数据**：包含基本信息，微博文本可能不完整
- **Detail阶段保存的数据**：包含完整文本和详细信息
- **建议**：等待程序完成，或手动运行Detail模式获取完整数据

