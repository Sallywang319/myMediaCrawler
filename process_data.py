import os
import json

def merge_json_files(base_dir, output_file):
    seen_note_ids = set()
    seen_video_ids = set()
    merged_data = []

    # 三个平台文件夹
    platforms = ["weibo", "bilibili"]

    for platform in platforms:
        input_dir = os.path.join(base_dir, platform, "json")
        if not os.path.exists(input_dir):
            print(f"跳过：未找到目录 {input_dir}")
            continue

        print(f"正在处理平台：{platform}")
        for filename in os.listdir(input_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(input_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                        # 保证 data 是列表形式
                        if isinstance(data, dict):
                            data = [data]

                        for item in data:
                            note_id = item.get("note_id")
                            video_id = item.get("video_id")
                            if note_id is not None and note_id not in seen_note_ids:
                                seen_note_ids.add(note_id)
                                # 增加来源平台信息
                                item["platform_name"] = platform
                                merged_data.append(item)
                            elif video_id is not None and video_id not in seen_video_ids:
                                seen_video_ids.add(video_id)
                                # 增加来源平台信息
                                item["platform_name"] = platform
                                merged_data.append(item)
                except Exception as e:
                    print(f"读取文件 {file_path} 时出错: {e}")

    # 写入合并后的 JSON 文件
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print(f"\n合并完成！共写入 {len(merged_data)} 条数据至 {output_file}")

if __name__ == "__main__":
    base_dir = "data"
    output_file = os.path.join(base_dir, "merged.json")
    merge_json_files(base_dir, output_file)
