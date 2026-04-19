"""
从配置文件生成视频草稿
使用方法：python generate_draft_from_config.py
"""
import json
import os
import requests
import shutil
import subprocess

BASE_URL = "http://localhost:9001"

def load_config(config_file="draft_config.json"):
    """加载配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_draft(config):
    """创建草稿的主函数"""
    print("🎬 根据配置文件生成草稿")
    print("=" * 60)
    print(f"项目: {config['project_name']}")
    print(f"描述: {config['description']}")
    print()

    # 创建新草稿
    print("📝 创建新草稿...")
    create_response = requests.post(f"{BASE_URL}/create_draft", json={
        "width": config['canvas']['width'],
        "height": config['canvas']['height']
    })

    if not create_response.json().get('success'):
        print("❌ 创建草稿失败")
        return None

    draft_id = create_response.json()['output']['draft_id']
    print(f"✅ 草稿创建成功: {draft_id}")

    # 计算时间线
    video_duration = config['videos']['duration_per_video']
    num_videos = len(config['videos']['files'])
    total_duration = video_duration * num_videos

    # 1. 添加视频
    print(f"\n📹 添加{num_videos}个视频...")
    video_folder = config['videos']['folder_path']

    for i, video_file in enumerate(config['videos']['files'], 1):
        video_path = os.path.join(video_folder, video_file)
        start_time = (i - 1) * video_duration

        print(f"  视频{i}: {video_file} ({start_time}s-{start_time + video_duration}s)")

        response = requests.post(f"{BASE_URL}/add_video", json={
            "video_url": video_path,
            "draft_id": draft_id,
            "start": 0,
            "end": float(video_duration),
            "target_start": float(start_time),
            "width": config['canvas']['width'],
            "height": config['canvas']['height'],
            "track_name": "main"
        })

        if response.json().get('success'):
            print(f"  ✅ 添加成功")
        else:
            print(f"  ❌ 添加失败")

    # 2. 添加配音
    print(f"\n🎤 添加{len(config['voiceovers']['files'])}个配音...")
    audio_folder = config['voiceovers']['folder_path']

    for i, audio_file in enumerate(config['voiceovers']['files'], 1):
        audio_path = os.path.join(audio_folder, audio_file)
        start_time = (i - 1) * video_duration

        print(f"  配音{i}: {audio_file} (从{start_time}s开始)")

        # 获取音频时长
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
            ], capture_output=True, text=True, timeout=5)
            audio_duration = float(result.stdout.strip())
        except:
            audio_duration = 2.0

        response = requests.post(f"{BASE_URL}/add_audio", json={
            "audio_url": audio_path,
            "draft_id": draft_id,
            "start": 0,
            "end": audio_duration,
            "target_start": float(start_time),
            "track_name": "voiceover"
        })

        if response.json().get('success'):
            print(f"  ✅ 添加成功")

    # 3. 添加字幕
    print(f"\n📝 添加{len(config['subtitles']['items'])}个字幕...")
    sub_config = config['subtitles']

    for i, subtitle in enumerate(sub_config['items'], 1):
        print(f"  字幕{i}: {subtitle['text']} ({subtitle['start']}s-{subtitle['end']}s)")

        response = requests.post(f"{BASE_URL}/add_text", json={
            "draft_id": draft_id,
            "text": subtitle['text'],
            "start": subtitle['start'],
            "end": subtitle['end'],
            "font": sub_config['font'],
            "font_size": sub_config['font_size'],
            "font_color": sub_config['font_color'],
            "background_color": sub_config['background_color'],
            "background_alpha": sub_config['background_alpha'],
            "track_name": "subtitles",
            "transform_x": sub_config['position']['x'],
            "transform_y": sub_config['position']['y'],
            "width": config['canvas']['width'],
            "height": config['canvas']['height']
        })

        if response.json().get('success'):
            print(f"  ✅ 添加成功")

    # 4. 添加序号标题
    print(f"\n🔢 添加{len(config['number_titles']['items'])}个序号标题...")
    num_config = config['number_titles']

    for i, number in enumerate(num_config['items'], 1):
        # 像素坐标转换为相对坐标
        relative_x = num_config['position_x_pixel'] / config['canvas']['width']
        relative_y = number['y_pixel'] / config['canvas']['height']

        print(f"  序号{i}: {number['text']} (x={relative_x:.4f}, y={relative_y:.4f}, 颜色:{number['color']})")

        response = requests.post(f"{BASE_URL}/add_text", json={
            "draft_id": draft_id,
            "text": number['text'],
            "start": 0,
            "end": total_duration,
            "font": num_config['font'],
            "font_size": num_config['font_size'],
            "font_color": number['color'],
            "transform_x": relative_x,
            "transform_y": relative_y,
            "shadow_enabled": num_config['shadow_enabled'],
            "shadow_color": num_config['shadow_color'],
            "shadow_alpha": num_config['shadow_alpha'],
            "shadow_smoothing": num_config['shadow_smoothing'],
            "track_name": f"number_{i}",
            "width": config['canvas']['width'],
            "height": config['canvas']['height']
        })

        if response.json().get('success'):
            print(f"  ✅ 添加成功")

    # 5. 添加描述标题
    print(f"\n📄 添加{len(config['description_titles']['items'])}个描述标题...")
    desc_config = config['description_titles']

    for i, desc in enumerate(desc_config['items'], 1):
        # 像素坐标转换为相对坐标
        relative_x = desc_config['position_x_pixel'] / config['canvas']['width']
        relative_y = desc['y_pixel'] / config['canvas']['height']

        print(f"  描述{i}: {desc['text']} ({desc['start']}s-{desc['end']}s, x={relative_x:.4f}, y={relative_y:.4f})")

        response = requests.post(f"{BASE_URL}/add_text", json={
            "draft_id": draft_id,
            "text": desc['text'],
            "start": desc['start'],
            "end": desc['end'],
            "font": desc_config['font'],
            "font_size": desc_config['font_size'],
            "font_color": desc_config['font_color'],
            "border_color": desc_config['border_color'],
            "border_width": desc_config['border_width'],
            "border_alpha": desc_config['border_alpha'],
            "transform_x": relative_x,
            "transform_y": relative_y,
            "track_name": f"desc_{i}",
            "width": config['canvas']['width'],
            "height": config['canvas']['height']
        })

        if response.json().get('success'):
            print(f"  ✅ 添加成功")

    # 6. 保存并同步草稿
    print(f"\n💾 保存草稿...")
    response = requests.post(f"{BASE_URL}/save_draft", json={
        "draft_id": draft_id,
        "draft_folder": config['output']['draft_folder']
    })

    api_path = os.path.join(os.getcwd(), draft_id)
    capcut_path = os.path.join(config['output']['draft_folder'], draft_id)

    # 修复路径
    if os.path.exists(api_path):
        json_file = os.path.join(api_path, "draft_info.json")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 修复视频路径
        videos_data = data.get('materials', {}).get('videos', [])
        for video in videos_data:
            old_path = video.get('path', '')
            if not os.path.isabs(old_path):
                filename = os.path.basename(old_path)
                new_path = os.path.join(capcut_path, "assets", "video", filename)
                video['path'] = new_path
            remote_url = video.get('remote_url', '')
            if remote_url and not remote_url.startswith('http'):
                video['remote_url'] = ''

        # 修复音频路径
        audios_data = data.get('materials', {}).get('audios', [])
        for audio in audios_data:
            old_path = audio.get('path', '')
            if not os.path.isabs(old_path):
                filename = os.path.basename(old_path)
                new_path = os.path.join(capcut_path, "assets", "audio", filename)
                audio['path'] = new_path

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 复制到剪映目录
    if os.path.exists(capcut_path):
        shutil.rmtree(capcut_path)

    if os.path.exists(api_path):
        shutil.move(api_path, capcut_path)
        print(f"✅ 草稿已保存到剪映目录")
    else:
        print(f"❌ 本地草稿不存在")
        return None

    # 自定义草稿名称
    custom_name = config.get('draft_name', '').strip()
    if custom_name:
        old_path = capcut_path
        new_path = os.path.join(config['output']['draft_folder'], custom_name)

        if os.path.exists(new_path):
            print(f"⚠️  目标名称已存在，将覆盖")
            shutil.rmtree(new_path)

        shutil.move(old_path, new_path)
        print(f"✅ 草稿已重命名为: {custom_name}")
        return custom_name

    return draft_id

def main():
    """主函数"""
    # 加载配置
    config = load_config()

    # 生成草稿
    draft_id = create_draft(config)

    if draft_id:
        print(f"\n" + "=" * 60)
        print("🎉 草稿生成完成！")
        print(f"🆔 草稿ID: {draft_id}")
        print(f"📂 位置: {config['output']['draft_folder']}/{draft_id}")
        print(f"\n📋 统计信息:")
        print(f"  📹 视频: {len(config['videos']['files'])} 个")
        print(f"  🎤 配音: {len(config['voiceovers']['files'])} 个")
        print(f"  📝 字幕: {len(config['subtitles']['items'])} 个")
        print(f"  🔢 序号: {len(config['number_titles']['items'])} 个")
        print(f"  📄 描述: {len(config['description_titles']['items'])} 个")
        print(f"  ⏱️ 总时长: {len(config['videos']['files']) * config['videos']['duration_per_video']}秒")
        print(f"\n✅ 请在剪映中打开查看")
        print("=" * 60)
    else:
        print("❌ 草稿生成失败")

if __name__ == "__main__":
    main()
