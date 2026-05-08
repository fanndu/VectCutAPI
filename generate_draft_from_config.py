"""
从配置文件生成视频草稿
使用方法：python generate_draft_from_config.py
"""
import json
import os
import requests
import shutil
import subprocess
from datetime import datetime

BASE_URL = "http://localhost:8080"

def format_srt_time(seconds):
    """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

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
    use_actual_duration = config['videos'].get('use_actual_duration', False)
    fixed_duration = config['videos'].get('duration_per_video', 4)
    video_files = config['videos']['files']

    # 1. 添加视频
    print(f"\n📹 添加{len(video_files)}个视频...")
    video_folder = config['videos']['folder_path']

    # 存储视频时长信息
    video_durations = []
    current_start_time = 0

    for i, video_file in enumerate(video_files, 1):
        video_path = os.path.join(video_folder, video_file)

        if use_actual_duration:
            # 使用ffprobe获取视频实际时长
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', video_path
                ], capture_output=True, text=True, timeout=10)
                actual_duration = float(result.stdout.strip())
                print(f"  视频{i}: {video_file} (实际时长: {actual_duration:.2f}秒)")
            except Exception:
                print(f"  ⚠️ 无法获取视频{i}的实际时长，使用默认值: {fixed_duration}秒")
                actual_duration = fixed_duration
        else:
            # 使用固定时长
            actual_duration = fixed_duration
            print(f"  视频{i}: {video_file} (固定时长: {actual_duration}秒)")

        video_durations.append(actual_duration)

        print(f"    时间位置: {current_start_time}s-{current_start_time + actual_duration}s")

        response = requests.post(f"{BASE_URL}/add_video", json={
            "video_url": video_path,
            "draft_id": draft_id,
            "start": 0,
            "end": float(actual_duration),
            "target_start": float(current_start_time),
            "width": config['canvas']['width'],
            "height": config['canvas']['height'],
            "track_name": "main"
        })

        if response.json().get('success'):
            print(f"  ✅ 添加成功")
        else:
            print(f"  ❌ 添加失败")

        # 更新下一个视频的起始时间
        current_start_time += actual_duration

    # 计算总时长
    total_duration = current_start_time
    print(f"\n⏱️ 视频总时长: {total_duration:.2f}秒")

    # 2. 添加配音
    print(f"\n🎤 添加{len(config['voiceovers']['files'])}个配音...")
    audio_folder = config['voiceovers']['folder_path']

    for i, audio_file in enumerate(config['voiceovers']['files'], 1):
        audio_path = os.path.join(audio_folder, audio_file)

        # 计算配音的起始时间（基于对应视频的起始时间）
        if i <= len(video_durations):
            # 计算第i个视频的起始时间
            start_time = sum(video_durations[:i-1])
        else:
            # 如果配音数量多于视频数量，使用固定间隔
            start_time = (i - 1) * fixed_duration

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

    # 2.5 添加音效
    if config.get('sound_effects') and config['sound_effects'].get('file'):
        print(f"\n🔔 添加音效...")
        sfx_path = config['sound_effects']['file']
        sfx_start = config['sound_effects'].get('start', 0.0)

        if os.path.exists(sfx_path):
            print(f"  音效文件: {os.path.basename(sfx_path)}")
            print(f"  开始时间: {sfx_start}s")

            # 获取音效时长
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', sfx_path
                ], capture_output=True, text=True, timeout=5)
                sfx_duration = float(result.stdout.strip())
                print(f"  时长: {sfx_duration:.2f}s")
            except:
                sfx_duration = 2.0
                print(f"  时长: 使用默认值2.0s")

            response = requests.post(f"{BASE_URL}/add_audio", json={
                "audio_url": sfx_path,
                "draft_id": draft_id,
                "start": 0,
                "end": sfx_duration,
                "target_start": float(sfx_start),
                "track_name": "sound_effect"
            })

            if response.json().get('success'):
                print(f"  ✅ 音效添加成功")
            else:
                print(f"  ❌ 音效添加失败")
        else:
            print(f"  ⚠️  音效文件不存在: {sfx_path}")


    # 2.5.5 添加背景音乐
    if config.get('background_music') and config['background_music'].get('file'):
        print(f"\n🎵 添加背景音乐...")
        bgm_path = config['background_music']['file']
        bgm_start = config['background_music'].get('start', 0.0)
        bgm_end = config['background_music'].get('end', None)  # None表示到视频结束

        if os.path.exists(bgm_path):
            print(f"  背景音乐: {os.path.basename(bgm_path)}")

            # 获取背景音乐时长
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', bgm_path
                ], capture_output=True, text=True, timeout=5)
                bgm_duration = float(result.stdout.strip())
                print(f"  时长: {bgm_duration:.2f}s")
            except:
                bgm_duration = total_duration
                print(f"  时长: 使用视频总时长 {total_duration:.2f}s")

            # 确定结束时间
            if bgm_end is None:
                bgm_end = total_duration
            elif bgm_end > bgm_duration:
                bgm_end = bgm_duration

            print(f"  播放时间: {bgm_start:.2f}s - {bgm_end:.2f}s (视频总时长: {total_duration:.2f}s)")

            response = requests.post(f"{BASE_URL}/add_audio", json={
                "audio_url": bgm_path,
                "draft_id": draft_id,
                "start": 0,
                "end": bgm_duration,
                "target_start": float(bgm_start),
                "target_end": float(total_duration),
                "track_name": "background_music"
            })

            if response.json().get('success'):
                print(f"  ✅ 背景音乐添加成功")
            else:
                print(f"  ❌ 背景音乐添加失败: {response.json().get('error')}")
        else:
            print(f"  ⚠️  背景音乐文件不存在: {bgm_path}")

    # 2.5.6 添加视频片段音效
    if config.get('video_sound_effects') and config['video_sound_effects'].get('file'):
        print(f"\n🎬 添加视频片段音效...")
        sfx_path = config['video_sound_effects']['file']
        add_to_each = config['video_sound_effects'].get('add_to_each_segment', False)

        if os.path.exists(sfx_path):
            print(f"  音效文件: {os.path.basename(sfx_path)}")

            # 获取音效时长
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', sfx_path
                ], capture_output=True, text=True, timeout=5)
                sfx_duration = float(result.stdout.strip())
                print(f"  时长: {sfx_duration:.2f}s")
            except:
                sfx_duration = 1.0
                print(f"  时长: 使用默认值1.0s")

            if add_to_each:
                # 为每个视频片段添加音效（使用同一音轨）
                print(f"  模式: 为每个视频片段添加（同一音轨）")
                for i, video_duration in enumerate(video_durations, 1):
                    # 计算第i个视频的起始时间
                    segment_start = sum(video_durations[:i-1])

                    print(f"  片段{i}: 在 {segment_start:.2f}s 位置添加音效")

                    response = requests.post(f"{BASE_URL}/add_audio", json={
                        "audio_url": sfx_path,
                        "draft_id": draft_id,
                        "start": 0,
                        "end": sfx_duration,
                        "target_start": float(segment_start),
                        "track_name": "video_sfx"
                    })

                    if response.json().get('success'):
                        print(f"  ✅ 片段{i}音效添加成功")
                    else:
                        print(f"  ❌ 片段{i}音效添加失败")
            else:
                print(f"  模式: 未启用'为每个片段添加'")
        else:
            print(f"  ⚠️  音效文件不存在: {sfx_path}")

    # 2.6 添加时间线图片
    if config.get('timeline_images'):
        print(f"\n🖼️  添加时间线图片...")
        for idx, img_config in enumerate(config['timeline_images'], 1):
            img_path = img_config['file']
            img_x = img_config['x']
            img_y = img_config['y']

            if os.path.exists(img_path):
                # 转换像素坐标为相对坐标（相对于画布尺寸）
                relative_x = img_x / config['canvas']['width']
                relative_y = img_y / config['canvas']['height']

                print(f"  图片{idx}: {os.path.basename(img_path)}")
                print(f"    坐标: x={img_x}px, y={img_y}px (相对: x={relative_x:.3f}, y={relative_y:.3f})")

                response = requests.post(f"{BASE_URL}/add_image", json={
                    "image_url": img_path,
                    "draft_id": draft_id,
                    "start": 0,
                    "end": total_duration,
                    "transform_x": relative_x,
                    "transform_y": relative_y,
                    "track_name": f"timeline_{idx}",
                    "width": config['canvas']['width'],
                    "height": config['canvas']['height'],
                    "draft_folder": config['output']['draft_folder']
                })

                if response.json().get('success'):
                    print(f"  ✅ 添加成功")
                else:
                    print(f"  ❌ 添加失败: {response.json().get('error', 'Unknown error')}")
            else:
                print(f"  ⚠️  图片文件不存在: {img_path}")

    # 3. 添加大标题
    if config.get('main_title', {}).get('enabled', False):
        print(f"\n🎯 添加大标题...")
        title_config = config['main_title']

        # 转换像素坐标为相对坐标
        relative_x = title_config['position']['x_pixel'] / config['canvas']['width']
        relative_y = title_config['position']['y_pixel'] / config['canvas']['height']

        print(f"  大标题: {title_config['text'].replace(chr(10), ' ')} (x={relative_x:.3f}, y={relative_y:.3f})")

        # 构建请求数据
        request_data = {
            "draft_id": draft_id,
            "text": title_config['text'],
            "start": 0,
            "end": total_duration,
            "font": title_config['font'],
            "font_size": title_config['font_size'],
            "font_color": title_config['font_color'],
            "transform_x": relative_x,
            "transform_y": relative_y,
            "track_name": "main_title",
            "width": config['canvas']['width'],
            "height": config['canvas']['height']
        }

        # 添加多样式颜色配置
        if 'text_styles' in title_config and title_config['text_styles']:
            request_data['text_styles'] = []
            for style in title_config['text_styles']:
                request_data['text_styles'].append({
                    'start': style['start'],
                    'end': style['end'],
                    'style': {
                        'color': style['color']
                    }
                })
            print(f"  多样式颜色: {len(title_config['text_styles'])}个样式")

        # 添加入场动画
        if 'intro_animation' in title_config:
            request_data['intro_animation'] = title_config['intro_animation']
            if 'intro_duration' in title_config:
                request_data['intro_duration'] = title_config['intro_duration']
            print(f"  入场动画: {title_config['intro_animation']} ({title_config['intro_duration']}s)")

        response = requests.post(f"{BASE_URL}/add_text", json=request_data)

        if response.json().get('success'):
            print(f"  ✅ 大标题添加成功")

    # 4. 添加字幕
    sub_config = config['subtitles']
    use_srt = sub_config.get('use_srt', False)
    srt_content = config.get('srt_content', None)

    if use_srt and srt_content:
        # 使用真正的字幕轨道（SRT格式）
        print(f"\n📝 添加字幕（字幕轨道，SRT格式）...")
        print(f"   SRT 字幕内容:")
        print("   " + "\n   ".join(srt_content.split('\n')[:12]))  # 显示前12行

        request_data = {
            "draft_id": draft_id,
            "srt": srt_content,
            "track_name": "subtitles",
            "font": sub_config['font'],
            "font_size": sub_config['font_size'],
            "font_color": sub_config['font_color'],
            "background_color": sub_config['background_color'],
            "background_alpha": sub_config['background_alpha'],
            "transform_x": sub_config.get('transform_x', 0.0),
            "transform_y": sub_config.get('transform_y', -0.75),
            "width": config['canvas']['width'],
            "height": config['canvas']['height']
        }

        response = requests.post(f"{BASE_URL}/add_subtitle", json=request_data)

        if response.json().get('success'):
            print(f"  ✅ 字幕轨道添加成功")
        else:
            print(f"  ❌ 字幕轨道添加失败: {response.json().get('error', 'Unknown error')}")
            print(f"  ℹ️  回退到文本轨道...")
            # 回退到文本轨道
            use_srt = False

    if not use_srt or not srt_content:
        # 使用文本轨道
        print(f"\n📝 添加{len(config['subtitles']['items'])}个字幕（文本轨道）...")

        alignment = sub_config.get('alignment', 'left')
        animation = sub_config.get('animation', None)
        animation_duration = sub_config.get('animation_duration', 0.1)

        for i, subtitle in enumerate(sub_config['items'], 1):
            # 计算该字幕对应的视频片段的实际时长
            # 第i个字幕对应第i个视频片段
            if i <= len(video_durations):
                video_start = sum(video_durations[:i-1])  # 前i-1个视频的总时长
                video_duration = video_durations[i-1]  # 第i个视频的时长
                sub_start = video_start
                sub_end = video_start + video_duration
            else:
                # 如果字幕数量多于视频数量，使用配置中的时间
                sub_start = subtitle['start']
                sub_end = subtitle['end']

            print(f"  字幕{i}: {subtitle['text']} ({sub_start:.2f}s-{sub_end:.2f}s)")

            request_data = {
                "draft_id": draft_id,
                "text": subtitle['text'],
                "start": sub_start,
                "end": sub_end,
                "font": sub_config['font'],
                "font_size": sub_config['font_size'],
                "font_color": sub_config['font_color'],
                "background_color": sub_config['background_color'],
                "background_alpha": sub_config['background_alpha'],
                "alignment": alignment,
                "track_name": "subtitles",
                "transform_x": sub_config['position']['x'],
                "transform_y": sub_config['position']['y'],
                "width": config['canvas']['width'],
                "height": config['canvas']['height']
            }

            if animation:
                request_data['intro_animation'] = animation
                request_data['intro_duration'] = animation_duration

            response = requests.post(f"{BASE_URL}/add_text", json=request_data)

            if response.json().get('success'):
                print(f"  ✅ 添加成功")
            else:
                print(f"  ❌ 添加失败: {response.json().get('error', 'Unknown error')}")

    # 5. 添加序号标题
    print(f"\n🔢 添加{len(config['number_titles']['items'])}个序号标题...")
    num_config = config['number_titles']

    for i, number in enumerate(num_config['items'], 1):
        # 像素坐标转换为相对坐标
        relative_x = num_config['position_x_pixel'] / config['canvas']['width']
        relative_y = number['y_pixel'] / config['canvas']['height']

        print(f"  序号{i}: {number['text']} (x={relative_x:.4f}, y={relative_y:.4f}, 颜色:{number['color']})")

        # 构建请求数据
        request_data = {
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
        }

        # 添加入场动画
        if 'intro_animation' in num_config:
            request_data['intro_animation'] = num_config['intro_animation']
            if 'intro_duration' in num_config:
                request_data['intro_duration'] = num_config['intro_duration']

        response = requests.post(f"{BASE_URL}/add_text", json=request_data)

        if response.json().get('success'):
            print(f"  ✅ 添加成功")

    # 6. 添加描述标题
    print(f"\n📄 添加{len(config['description_titles']['items'])}个描述标题...")
    desc_config = config['description_titles']

    for i, desc in enumerate(desc_config['items'], 1):
        # 像素坐标转换为相对坐标
        relative_x = desc_config['position_x_pixel'] / config['canvas']['width']
        relative_y = desc['y_pixel'] / config['canvas']['height']

        # 计算该小标题对应的视频段开始位置
        # 第i个小标题从第i个视频段的开始位置显示
        if i <= len(video_durations):
            desc_start = sum(video_durations[:i-1])  # 前i-1个视频的总时长
        else:
            desc_start = 0

        # 使用实际总时长作为结束时间
        desc_end = total_duration

        print(f"  描述{i}: {desc['text']} ({desc_start:.2f}s-{desc_end:.2f}s, x={relative_x:.4f}, y={relative_y:.4f})")

        # 构建请求数据
        request_data = {
            "draft_id": draft_id,
            "text": desc['text'],
            "start": desc_start,
            "end": desc_end,
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
        }

        # 添加阴影配置（如果启用）
        if desc_config.get('shadow_enabled', False):
            request_data['shadow_enabled'] = True
            request_data['shadow_color'] = desc_config.get('shadow_color', '#000000')
            request_data['shadow_alpha'] = desc_config.get('shadow_alpha', 0.8)
            request_data['shadow_smoothing'] = desc_config.get('shadow_smoothing', 0.3)

        # 添加入场动画
        if 'intro_animation' in desc_config:
            request_data['intro_animation'] = desc_config['intro_animation']
            if 'intro_duration' in desc_config:
                request_data['intro_duration'] = desc_config['intro_duration']

        response = requests.post(f"{BASE_URL}/add_text", json=request_data)

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

    # 复制到剪映目录
    if os.path.exists(capcut_path):
        shutil.rmtree(capcut_path)

    if os.path.exists(api_path):
        shutil.move(api_path, capcut_path)
        print(f"✅ 草稿已保存到剪映目录")
    else:
        print(f"❌ 本地草稿不存在")
        return None

    # 自定义草稿名称（支持时间戳占位符）
    custom_name = config.get('draft_name', '').strip()
    if '{timestamp}' in custom_name:
        # 生成时间戳格式：20240420_143025
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        custom_name = custom_name.replace('{timestamp}', timestamp)
        print(f"📅 草稿名称时间戳: {timestamp}")

    final_path = capcut_path  # 默认使用draft_id作为路径
    if custom_name:
        old_path = capcut_path
        final_path = os.path.join(config['output']['draft_folder'], custom_name)

        if os.path.exists(final_path):
            print(f"⚠️  目标名称已存在，将覆盖")
            shutil.rmtree(final_path)

        shutil.move(old_path, final_path)
        print(f"✅ 草稿已重命名为: {custom_name}")

    # 修复路径（在重命名之后）
    json_file = os.path.join(final_path, "draft_info.json")
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 修复视频路径 - 将旧的draft_id路径替换为新的final_path
        videos_data = data.get('materials', {}).get('videos', [])
        for video in videos_data:
            old_path = video.get('path', '')
            # 检查路径中是否包含旧的draft_id，如果有则替换
            if draft_id in old_path:
                filename = os.path.basename(old_path)
                new_path = os.path.join(final_path, "assets", "video", filename)
                video['path'] = new_path
            elif not os.path.isabs(old_path):
                filename = os.path.basename(old_path)
                new_path = os.path.join(final_path, "assets", "video", filename)
                video['path'] = new_path
            remote_url = video.get('remote_url', '')
            if remote_url and not remote_url.startswith('http'):
                video['remote_url'] = ''

        # 修复音频路径 - 将旧的draft_id路径替换为新的final_path
        audios_data = data.get('materials', {}).get('audios', [])
        for audio in audios_data:
            old_path = audio.get('path', '')
            # 检查路径中是否包含旧的draft_id，如果有则替换
            if draft_id in old_path:
                filename = os.path.basename(old_path)
                new_path = os.path.join(final_path, "assets", "audio", filename)
                audio['path'] = new_path
            elif not os.path.isabs(old_path):
                filename = os.path.basename(old_path)
                new_path = os.path.join(final_path, "assets", "audio", filename)
                audio['path'] = new_path

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 返回草稿ID和实际总时长
    if custom_name:
        return custom_name, total_duration
    else:
        return draft_id, total_duration

    return draft_id

def main():
    """主函数"""
    # 加载配置
    config = load_config()

    # 生成草稿
    result = create_draft(config)

    if result:
        draft_id, total_duration = result
        print(f"\n" + "=" * 60)
        print("🎉 草稿生成完成！")
        print(f"🆔 草稿ID: {draft_id}")
        print(f"📂 位置: {config['output']['draft_folder']}/{draft_id}")
        print(f"\n📋 统计信息:")
        print(f"  📹 视频: {len(config['videos']['files'])} 个")
        print(f"  🎤 配音: {len(config['voiceovers']['files'])} 个")
        print(f"  🎯 大标题: {1 if config.get('main_title', {}).get('enabled', False) else 0} 个")
        print(f"  📝 字幕: {len(config['subtitles']['items'])} 个")
        print(f"  🔢 序号: {len(config['number_titles']['items'])} 个")
        print(f"  📄 描述: {len(config['description_titles']['items'])} 个")
        print(f"  ⏱️ 总时长: {total_duration:.2f}秒")
        print(f"\n✅ 请在剪映中打开查看")
        print("=" * 60)
    else:
        print("❌ 草稿生成失败")

if __name__ == "__main__":
    main()
