#!/usr/bin/env python3
"""
飞书多维表格数据读取工具
用于从飞书表格读取ranking主题和制作数据
使用飞书官方 SDK (lark-oapi)
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from lark_oapi.api.bitable.v1 import *
from lark_oapi import Client

class FeishuBitableReader:
    """飞书多维表格读取器 - 使用官方 SDK"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        # 创建客户端
        self.client = Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .build()

    def read_table_data(self, app_id: str, table_id: str, view_id: str = '', page_size: int = 100) -> List[Dict[str, Any]]:
        """读取多维表格数据（支持分页）- 使用官方 SDK"""
        all_records = []
        page_token = None

        while True:
            # 构建 request body
            body_builder = SearchAppTableRecordRequestBody.builder()
            if view_id:
                body_builder.view_id(view_id)

            # 构建请求 - app_token 对于 wiki 就是 app_id
            request_builder = SearchAppTableRecordRequest.builder() \
                .app_token(app_id) \
                .table_id(table_id) \
                .page_size(page_size) \
                .request_body(body_builder.build())

            if page_token:
                request_builder.page_token(page_token)

            request = request_builder.build()

            # 调用 API
            response = self.client.bitable.v1.app_table_record.search(request)

            if not response.success():
                raise Exception(f"读取表格失败: {response.code} - {response.msg}")

            # 获取数据
            items = response.data.items
            if not items:
                break

            # 转换为字典格式
            for item in items:
                all_records.append({
                    'record_id': item.record_id,
                    'fields': item.fields.__dict__ if hasattr(item.fields, '__dict__') else item.fields,
                    'created_time': item.created_time,
                    'last_modified_time': item.last_modified_time
                })

            # 获取下一页
            page_token = response.data.page_token
            if not page_token:
                break

        return all_records

    def parse_table_url(self, url: str) -> tuple[str, str, str]:
        """解析表格URL，返回(app_id, table_id, view_id)"""
        # URL格式: https://my.feishu.cn/wiki/{app_id}?table={table_id}&view={view_id}
        try:
            if 'table=' in url:
                parts = url.split('table=')
                table_part = parts[1].split('&')[0]
                app_id = url.split('/wiki/')[1].split('?')[0]

                # 提取view_id
                view_id = ''
                if 'view=' in url:
                    view_parts = url.split('view=')
                    view_id = view_parts[1].split('&')[0]

                return app_id, table_part, view_id
        except Exception as e:
            raise ValueError(f"无法解析URL: {url}, 错误: {e}")


def get_text_value(field) -> Optional[str]:
    """从飞书富文本字段中提取文本值"""
    if field is None:
        return None
    if isinstance(field, list) and len(field) > 0:
        return field[0].get('text', '')
    return str(field) if field else None


def read_feishu_credentials(credentials_file: str = ".feishu_credentials.json") -> Dict[str, Any]:
    """读取飞书凭证和配置 - 支持两种格式"""
    # 优先使用.feishu_config.json
    config_file = ".feishu_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        result = {
            'app_id': config.get('app_id', ''),
            'app_secret': config.get('app_secret', '')
        }
        # 添加表格配置
        if 'ranking_topic_table' in config:
            result['ranking_topic_table'] = config['ranking_topic_table']
        if 'ranking_make_table' in config:
            result['ranking_make_table'] = config['ranking_make_table']
        return result

    # 回退到旧格式
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"未找到凭证文件: {credentials_file} 或 {config_file}")

    with open(credentials_file, 'r') as f:
        return json.load(f)


def read_topic_table(credentials_file: str = ".feishu_credentials.json",
                     topic_url: str = None) -> List[Dict[str, Any]]:
    """读取ranking主题表格"""
    print("📊 读取ranking主题表格...")

    creds = read_feishu_credentials(credentials_file)

    # 优先使用配置文件中的表格配置
    if 'ranking_topic_table' in creds:
        table_config = creds['ranking_topic_table']
        app_id = table_config.get('app_id', '')
        table_id = table_config.get('table_id', '')
        view_id = table_config.get('view_id', '')
    elif topic_url:
        reader = FeishuBitableReader(creds['app_id'], creds['app_secret'])
        app_id, table_id, view_id = reader.parse_table_url(topic_url)
    else:
        raise ValueError("未找到飞书表格配置，请在 .feishu_config.json 中配置 ranking_topic_table")

    reader = FeishuBitableReader(creds['app_id'], creds['app_secret'])

    records = reader.read_table_data(app_id, table_id, view_id)

    # 筛选待处理记录：创建草稿时间为空且添加时间不为空
    pending_records = []
    for record in records:
        fields = record.get('fields', {})
        create_time = get_text_value(fields.get('创建草稿时间'))
        add_time = get_text_value(fields.get('添加时间'))

        if (not create_time or create_time == '') and (add_time and add_time != ''):
            pending_records.append({
                'record_id': record.get('record_id'),
                '大标题': get_text_value(fields.get('大标题')) or '',
                '编号': get_text_value(fields.get('编号')) or '',
                'fields': fields
            })

    print(f"✅ 找到 {len(pending_records)} 条待处理记录")
    return pending_records


def read_production_table(credentials_file: str = ".feishu_credentials.json",
                         prod_url: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """读取ranking制作表格"""
    print("📊 读取ranking制作表格...")

    creds = read_feishu_credentials(credentials_file)

    # 优先使用配置文件中的表格配置
    if 'ranking_make_table' in creds:
        table_config = creds['ranking_make_table']
        app_id = table_config.get('app_id', '')
        table_id = table_config.get('table_id', '')
        view_id = table_config.get('view_id', '')
    elif prod_url:
        reader = FeishuBitableReader(creds['app_id'], creds['app_secret'])
        app_id, table_id, view_id = reader.parse_table_url(prod_url)
    else:
        raise ValueError("未找到飞书表格配置，请在 .feishu_config.json 中配置 ranking_make_table")

    reader = FeishuBitableReader(creds['app_id'], creds['app_secret'])

    records = reader.read_table_data(app_id, table_id, view_id)

    # 构建"编号"到制作记录的映射
    prod_map = {}
    for record in records:
        fields = record.get('fields', {})
        编号 = get_text_value(fields.get('编号'))

        if 编号:
            if 编号 not in prod_map:
                prod_map[编号] = []

            prod_map[编号].append({
                '视频顺序编号': get_text_value(fields.get('视频顺序编号')) or '',
                '视频文件名': get_text_value(fields.get('视频文件名')) or '',
                '小标题': get_text_value(fields.get('小标题')) or '',
                '字幕': get_text_value(fields.get('字幕')) or '',
                'fields': fields
            })

    print(f"✅ 加载 {len(records)} 条制作记录，关联 {len(prod_map)} 个编号")
    return prod_map


def find_video_file(video_name: str,
                    base_folder: str = "/Users/frank/Downloads/magic/02-选标/1111-200") -> Optional[str]:
    """查找视频文件"""
    import glob

    # 先尝试直接匹配
    direct_pattern = os.path.join(base_folder, f"{video_name}.*")
    matches = glob.glob(direct_pattern)

    if matches:
        return matches[0]

    # 递归搜索子文件夹
    recursive_pattern = os.path.join(base_folder, "**", f"{video_name}.*")
    matches = glob.glob(recursive_pattern, recursive=True)

    if matches:
        return matches[0]

    # 尝试匹配前面有空格的文件名
    space_pattern = os.path.join(base_folder, "**", f"*{video_name}.*")
    matches = glob.glob(space_pattern, recursive=True)

    if matches:
        return matches[0]

    return None


def find_audio_file(sequence_id: str,
                    base_folder: str = "/Users/frank/Downloads/magic/08-配音") -> Optional[str]:
    """查找配音文件"""
    import glob

    # 使用通配符匹配
    pattern = os.path.join(base_folder, f"{sequence_id}*.mp3")
    matches = glob.glob(pattern)

    if matches:
        return matches[0]

    return None


if __name__ == "__main__":
    # 测试代码
    try:
        # 读取主题表格
        pending = read_topic_table()
        print(f"\n待处理记录: {len(pending)}")

        # 读取制作表格
        prod_map = read_production_table()
        print(f"关联编号数: {len(prod_map)}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)




def update_feishu_record(record_id: str, create_time: str,
                         credentials_file: str = ".feishu_credentials.json",
                         topic_url: str = None) -> bool:
    """更新飞书表格中的创建草稿时间"""
    import requests

    creds = read_feishu_credentials(credentials_file)

    # 优先使用配置文件中的表格配置
    if 'ranking_topic_table' in creds:
        table_config = creds['ranking_topic_table']
        app_id = table_config.get('app_id', '')
        table_id = table_config.get('table_id', '')
        view_id = table_config.get('view_id', '')
    elif topic_url:
        reader = FeishuBitableReader(creds['app_id'], creds['app_secret'])
        app_id, table_id, view_id = reader.parse_table_url(topic_url)
    else:
        raise ValueError("未找到飞书表格配置，请在 .feishu_config.json 中配置 ranking_topic_table")

    try:
        # 获取tenant_access_token
        token_response = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={
                "app_id": creds['app_id'],
                "app_secret": creds['app_secret']
            }
        )
        
        if token_response.status_code != 200:
            print(f"❌ 获取token失败: {token_response.status_code}")
            return False
        
        tenant_access_token = token_response.json().get('tenant_access_token')
        
        # 使用batch_update API更新
        update_data = {
            "records": [{
                "record_id": record_id,
                "fields": {
                    "创建草稿时间": create_time
                }
            }]
        }
        
        response = requests.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_id}/tables/{table_id}/records/batch_update",
            headers={
                "Authorization": f"Bearer {tenant_access_token}",
                "Content-Type": "application/json"
            },
            json=update_data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                return True
            else:
                print(f"❌ 更新失败: {result.get('msg')}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 更新异常: {e}")
        return False
