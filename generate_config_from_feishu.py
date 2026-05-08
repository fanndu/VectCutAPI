#!/usr/bin/env python3
"""
从飞书数据生成视频草稿配置
"""

import json
import os
import glob
from datetime import datetime
from typing import List, Dict, Any

try:
    from feishu_reader import (
        read_feishu_credentials,
        read_topic_table,
        read_production_table,
        find_video_file,
        find_audio_file
    )
except ImportError:
    print("❌ 请确保 feishu_reader.py 存在")
    exit(1)


class FeishuConfigGenerator:
    """飞书配置生成器"""

    def __init__(self,
                 video_folder: str = "/Users/frank/Downloads/magic/02-选标/1111-200",
                 audio_folder: str = "/Users/frank/Downloads/magic/08-配音"):
        self.video_folder = video_folder
        self.audio_folder = audio_folder

    def generate_config(self, pending_records: List[Dict], prod_map: Dict[str, List[Dict]]) -> Dict:
        """从飞书数据生成草稿配置"""

        if not pending_records:
            raise ValueError("没有待处理的记录")

        # 处理第一条记录
        pending = pending_records[0]
        编号 = pending['编号']
        大标题 = pending['大标题']

        # 在第二个单词后面添加换行，并生成对应的文本样式
        words = 大标题.split()
        text_styles = []

        if len(words) >= 2:
            # 构建换行后的文本
            大标题 = ' '.join(words[:2]) + '\n' + ' '.join(words[2:])

            # 计算字符位置
            pos = 0
            # 第一个单词: Ranking (0-6)
            word1_end = len(words[0])
            text_styles.append({
                'start': 0,
                'end': word1_end,
                'color': '#ffffff'
            })
            pos = word1_end  # 7 (空格位置)

            # 第二个单词 + 换行: 7-16
            word2_with_space_and_newline = words[1]  # Funniest
            word2_start = pos
            word2_end = pos + len(' ') + len(words[1]) + len('\n')
            text_styles.append({
                'start': word2_start,
                'end': word2_end,
                'color': '#fff800'
            })
            pos = word2_end

            # 第三个单词: Unexpected
            if len(words) >= 3:
                word3_start = pos
                word3_end = pos + len(words[2])
                text_styles.append({
                    'start': word3_start,
                    'end': word3_end,
                    'color': '#2b9eff'
                })
                pos = word3_end

                # 其余单词
                if len(words) > 3:
                    rest_start = pos
                    rest_end = len(大标题)
                    text_styles.append({
                        'start': rest_start,
                        'end': rest_end,
                        'color': '#ffffff'
                    })

        # 生成时间戳
        now = datetime.now()
        timestamp_str = now.strftime('%Y_%m_%d_%H_%M_%S')

        # 草稿名称: 编号-大标题-时间
        safe_title = 大标题.replace(' ', '_').replace('/', '_').replace('\n', '_')
        draft_name = f"{编号}-{safe_title}_{timestamp_str}"

        print(f"📝 生成草稿: {draft_name}")

        # 收集视频和音频文件
        video_files = []
        audio_files = []
        subtitles = []
        description_titles = []

        # 尝试匹配制作记录
        prod_records = None
        match_key = 编号

        # 直接匹配
        if 编号 in prod_map:
            prod_records = prod_map[编号]
        else:
            # 尝试不同的格式（0v-025 -> 0x-025）
            alternate_formats = []
            if 编号.startswith('0v-'):
                alternate_formats.append(编号.replace('0v-', '0x-'))
            elif 编号.startswith('0x-'):
                alternate_formats.append(编号.replace('0x-', '0v-'))

            # 尝试只使用数字部分（0v-025 -> 025）
            if '-' in 编号:
                num_part = 编号.split('-')[1]
                alternate_formats.append(f'0v-{num_part}')
                alternate_formats.append(f'0x-{num_part}')

            for alt_format in alternate_formats:
                if alt_format in prod_map:
                    prod_records = prod_map[alt_format]
                    match_key = alt_format
                    print(f"  ℹ️  使用匹配编号: {alt_format}")
                    break

        if prod_records:
            for idx, prod in enumerate(prod_records):
                视频顺序编号 = prod['视频顺序编号']
                视频文件名 = prod['视频文件名']
                小标题 = prod['小标题']
                字幕文本 = prod['字幕']

                # 查找视频文件
                video_path = find_video_file(视频文件名, self.video_folder)
                if video_path:
                    # 保存相对于 VIDEO_FOLDER 的完整路径（包含子目录）
                    relative_path = os.path.relpath(video_path, self.video_folder)
                    video_files.append(relative_path)
                    print(f"  ✅ 视频{idx+1}: {relative_path}")
                else:
                    print(f"  ⚠️  视频{idx+1}未找到: {视频文件名}")

                # 查找配音文件（使用原始编号）
                audio_path = find_audio_file(f"{编号}-{idx+1}", self.audio_folder)
                if audio_path:
                    audio_files.append(os.path.basename(audio_path))
                    print(f"  ✅ 配音{idx+1}: {os.path.basename(audio_path)}")

                # 添加字幕 - 从对应视频片段首帧开始
                if 字幕文本:
                    start_time = idx * 4  # 第i个视频片段的开始时间
                    end_time = start_time + 4  # 持续4秒
                    subtitles.append({
                        'text': 字幕文本,
                        'start': start_time,
                        'end': end_time
                    })

                # 添加小标题（描述标题）- 时长先设置为占位值，后续统一修改
                if 小标题:
                    description_titles.append({
                        'text': 小标题,
                        'start': 0,
                        'end': 0,  # 占位值，后面会设置为总时长
                        'y_pixel': 0  # 将使用固定位置
                    })
        else:
            print(f"  ⚠️  未找到编号 '{编号}' 的制作记录")
            print(f"  ℹ️  草稿将只包含大标题，没有视频内容")

        # 计算视频总时长（用于设置小标题结束时间）
        # 简化计算：使用视频数量 * 默认时长4秒
        # 实际使用时会在生成草稿时重新计算
        estimated_total_duration = len(video_files) * 4

        # 生成序号标题（固定位置和颜色）
        number_colors = ['#fff800', '#2b9eff', '#ff0000', '#ffffff', '#ffffff', '#ffffff']
        number_y_positions = [767, 405, 64, -286, -646, -991]

        number_titles = []
        for idx in range(len(video_files)):
            color = number_colors[idx] if idx < len(number_colors) else '#ffffff'
            y_pixel = number_y_positions[idx] if idx < len(number_y_positions) else 0
            number_titles.append({
                'text': f"{idx+1}.",
                'y_pixel': y_pixel,
                'color': color
            })

        # 为小标题设置固定位置（与序号对应）和统一时长
        # 倒序位置：第1个和第6个互换，第2个和第5个互换，第3个和第4个互换
        description_y_positions = [-991, -646, -286, 64, 405, 767]
        for idx, desc in enumerate(description_titles):
            if idx < len(description_y_positions):
                desc['y_pixel'] = description_y_positions[idx]
            # 设置小标题从视频开始到整体结束
            desc['start'] = 0
            desc['end'] = estimated_total_duration

        # 生成完整配置
        config = {
            "project_name": f"Ranking视频 - {编号}",
            "description": f"从飞书表格生成 - {大标题}",
            "draft_name": draft_name,

            "canvas": {
                "width": 1080,
                "height": 1920
            },

            "videos": {
                "folder_path": self.video_folder,
                "use_actual_duration": True,
                "duration_per_video": 4,
                "files": video_files
            },

            "voiceovers": {
                "folder_path": self.audio_folder,
                "files": audio_files
            },

            "sound_effects": {
                "file": "/Users/frank/Downloads/magic/06-音乐库/02-ranking/Ding Sound Effect.mp3",
                "start": 0.0
            },

            "background_music": {
                "file": "/Users/frank/Downloads/magic/06-音乐库/QKThr 搞笑背景.mp4",
                "start": 0.0,
                "end": None
            },

            "video_sound_effects": {
                "file": "/Users/frank/Downloads/magic/06-音乐库/唰.mp3",
                "add_to_each_segment": True  # 为每个视频片段添加
            },

            "timeline_images": [
                {
                    "file": "/Users/frank/Downloads/magic/02-选标/0x-排名/背景.png",
                    "x": 0,
                    "y": 3149
                },
                {
                    "file": "/Users/frank/Downloads/magic/02-选标/0x-排名/背景.png",
                    "x": 0,
                    "y": -3557
                }
            ],

            "subtitles": {
                "font": "Exo",
                "font_size": 15,
                "font_color": "#FFFFFF",
                "background_color": "#000000",
                "background_alpha": 0.7,
                "alignment": "left",
                "position": {"x": -0.45, "y": 0.75},
                "items": subtitles
            },

            "main_title": {
                "enabled": True,
                "text": 大标题,
                "font": "Exo",
                "font_size": 13,
                "font_color": "#FFFFFF",
                "position": {
                    "x_pixel": 0,
                    "y_pixel": 1400
                },
                "text_styles": text_styles,
                "intro_animation": "向右露出",
                "intro_duration": 0.1
            },

            "number_titles": {
                "font": "Exo",
                "font_size": 13,
                "shadow_enabled": True,
                "shadow_color": "#000000",
                "shadow_alpha": 0.8,
                "shadow_smoothing": 0.3,
                "position_x_pixel": -911,
                "intro_animation": "向右露出",
                "intro_duration": 0.1,
                "items": number_titles
            },

            "description_titles": {
                "font": "Exo",
                "font_size": 9,
                "font_color": "#FFFFFF",
                "border_color": "#000000",
                "border_width": 50.0,
                "border_alpha": 1.0,
                "position_x_pixel": -500,
                "intro_animation": "向右露出",
                "intro_duration": 0.1,
                "items": description_titles
            },

            "output": {
                "draft_folder": "/Users/frank/Movies/JianyingPro/User Data/Projects/com.lveditor.draft",
                "api_base_url": "http://localhost:8080"
            }
        }

        return config


def main():
    """主函数"""
    print("🚀 飞书数据读取与配置生成")

    try:
        # 读取飞书数据
        pending_records = read_topic_table()
        prod_map = read_production_table()

        if not pending_records:
            print("ℹ️  没有待处理的记录")
            return

        # 生成配置
        generator = FeishuConfigGenerator()
        config = generator.generate_config(pending_records, prod_map)

        # 保存配置
        config_file = 'draft_config_feishu.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 配置文件已生成: {config_file}")
        print(f"   可以运行: cp {config_file} draft_config.json")
        print(f"   然后执行: python generate_draft_from_config.py")

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        print("请确保:")
        print("  1. 创建 .feishu_credentials.json 凭证文件")
        print("  2. 参考 .feishu_credentials.json.example")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()
