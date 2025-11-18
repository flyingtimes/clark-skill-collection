"""
RunningHub API文件上传工具
用于上传数字人相关文件到RunningHub服务
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class RunningHubAPI:
    """RunningHub API客户端"""

    def __init__(self, api_key: str = None, base_url: str = "https://www.runninghub.cn"):
        """
        初始化API客户端

        Args:
            api_key: API密钥，如果为None则从环境变量获取
            base_url: API基础URL
        """
        self.api_key = api_key if api_key else get_api_key()
        self.base_url = base_url
        self.upload_url = f"{base_url}/task/openapi/upload"
        self.generate_url = f"{base_url}/task/openapi/ai-app/run"
        self.status_url = f"{base_url}/task/openapi/outputs"

    def upload_file(self, file_path: str, file_type: str = "input") -> Optional[str]:
        """
        上传单个文件到RunningHub

        Args:
            file_path: 要上传的文件路径
            file_type: 文件类型，默认为"input"

        Returns:
            Optional[str]: 上传成功返回文件名，失败返回None
        """
        try:
            if not os.path.exists(file_path):
                print(f"错误: 文件 {file_path} 不存在")
                return None

            # 准备上传数据
            files = {'file': open(file_path, 'rb')}
            data = {
                'apiKey': self.api_key,
                'fileType': file_type
            }

            print(f"正在上传文件: {file_path}")

            # 发送请求
            response = requests.post(self.upload_url, files=files, data=data)
            files['file'].close()

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    file_name = result.get('data', {}).get('fileName')
                    print(f"[OK] 上传成功: {file_name}")
                    return file_name
                else:
                    print(f"[ERROR] 上传失败: {result.get('msg', '未知错误')}")
                    return None
            else:
                print(f"[ERROR] 请求失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            print(f"[ERROR] 上传文件时发生异常: {str(e)}")
            return None

    def load_reference_json(self, character_dir: str) -> Optional[Dict[str, str]]:
        """
        加载reference.json文件

        Args:
            character_dir: 数字人目录路径

        Returns:
            Optional[Dict[str, str]]: 加载成功返回配置字典，失败返回None
        """
        reference_file = Path(character_dir) / "reference.json"

        if reference_file.exists():
            try:
                with open(reference_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[OK] 已加载reference.json文件")
                    return config
            except Exception as e:
                print(f"[ERROR] 读取reference.json文件失败: {str(e)}")
                return None
        else:
            print(f"[INFO] reference.json文件不存在，需要重新上传")
            return None

    def save_reference_json(self, character_dir: str, config: Dict[str, str]) -> bool:
        """
        保存reference.json文件

        Args:
            character_dir: 数字人目录路径
            config: 配置字典

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            reference_file = Path(character_dir) / "reference.json"
            with open(reference_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            print(f"[OK] 已保存reference.json文件到: {reference_file}")
            return True
        except Exception as e:
            print(f"[ERROR] 保存reference.json文件失败: {str(e)}")
            return False

    def process_character_files(self, character_dir: str, character_name: str) -> bool:
        """
        处理数字人文件上传

        Args:
            character_dir: 数字人目录路径
            character_name: 数字人名称

        Returns:
            bool: 处理成功返回True，失败返回False
        """
        print(f"\n{'='*50}")
        print(f"处理数字人: {character_name}")
        print(f"目录: {character_dir}")
        print('='*50)

        # 首先检查是否已存在reference.json
        existing_config = self.load_reference_json(character_dir)
        if existing_config:
            print("[OK] 数字人文件已上传，无需重复处理")
            return True

        # 定义需要上传的文件类型和对应文件名
        file_mappings = {
            'voice_id': 'reference.mp3',
            'landscape_id': 'landscape.png',
            'portrait_id': 'portrait.png',
            'short_id': 'short.png'
        }

        config = {}
        character_path = Path(character_dir)

        # 逐个上传文件
        for config_key, filename in file_mappings.items():
            file_path = character_path / filename

            if not file_path.exists():
                print(f"[ERROR] 文件不存在: {file_path}")
                continue

            # 上传文件
            uploaded_filename = self.upload_file(str(file_path))
            if uploaded_filename:
                config[config_key] = uploaded_filename
            else:
                print(f"[ERROR] 上传文件失败: {filename}")
                return False

        # 检查是否所有文件都上传成功
        if len(config) != len(file_mappings):
            print(f"[ERROR] 文件上传不完整: {len(config)}/{len(file_mappings)}")
            return False

        # 保存配置到reference.json
        if self.save_reference_json(character_dir, config):
            print(f"[OK] 数字人 {character_name} 处理完成")
            return True
        else:
            print(f"[ERROR] 保存配置文件失败")
            return False

    def gen_audio(self, reference_audio: str, text: str) -> Optional[str]:
        """
        生成音频

        Args:
            reference_audio: 音频文件名（已上传到RunningHub的文件名）
            text: 要生成的文本内容

        Returns:
            Optional[str]: 成功返回任务ID，失败返回None
        """
        try:
            # 获取对应模式的webappId
            webapp_id = get_webapp_id("audio")
            print(webapp_id)
            # 构建请求数据
            data = {
                "webappId": webapp_id,
                "apiKey": self.api_key,
                "nodeInfoList": [
                    {
                        "nodeId": "6",
                        "fieldName": "text",
                        "fieldValue": text,
                        "description": "text"
                    },
                    {
                        "nodeId": "17",
                        "fieldName": "text",
                        "fieldValue": "害羞的",
                        "description": "text"
                    },
                    {
                        "nodeId": "9",
                        "fieldName": "audio",
                        "fieldValue": reference_audio,
                        "description": "audio"
                    }
                ]
            }

            print(f"正在生成音频...")
            print(f"WebApp ID: {webapp_id}")
            print(f"音频文件: {reference_audio}")
            print(f"文本内容: {text}")

            # 发送请求
            response = requests.post(
                self.generate_url,
                headers={'Content-Type': 'application/json'},
                json=data
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    task_id = result.get('data', {}).get('taskId')
                    print(f"[OK] 生成任务创建成功: {task_id}")
                    return task_id
                else:
                    print(f"[ERROR] 生成失败: {result.get('msg', '未知错误')}")
                    return None
            else:
                print(f"[ERROR] 请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None

        except Exception as e:
            print(f"[ERROR] 生成任务时发生异常: {str(e)}")
            return None

    def check_task_status(self, task_id: str) -> Optional[Dict]:
        """
        查询任务状态

        Args:
            task_id: 任务ID

        Returns:
            Optional[Dict]: 成功返回任务状态数据，失败返回None
        """
        try:
            data = {
                "apiKey": self.api_key,
                "taskId": task_id
            }

            response = requests.post(
                self.status_url,
                headers={'Content-Type': 'application/json'},
                json=data
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return result
                else:
                    # 返回包含错误信息的结果，让调用方处理
                    return result
            else:
                print(f"[ERROR] 请求失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            print(f"[ERROR] 查询任务状态时发生异常: {str(e)}")
            return None

    def download(self, file_url: str, output_path: str) -> bool:
        """
        下载文件

        Args:
            file_url: 文件URL
            output_path: 输出文件路径

        Returns:
            bool: 下载成功返回True，失败返回False
        """
        import time

        max_retries = 10
        retry_interval = 30  # 秒

        for attempt in range(max_retries):
            try:
                print(f"正在下载: {file_url}")
                if attempt > 0:
                    print(f"第 {attempt + 1} 次尝试下载...")

                response = requests.get(file_url, stream=True, timeout=30)

                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"[OK] 下载成功: {output_path}")
                    return True
                else:
                    print(f"[ERROR] 下载失败，状态码: {response.status_code}")
                    if attempt < max_retries - 1:
                        print(f"[WAIT] {retry_interval}秒后重试...")
                        time.sleep(retry_interval)
                    continue

            except Exception as e:
                print(f"[ERROR] 下载时发生异常: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"[WAIT] {retry_interval}秒后重试...")
                    time.sleep(retry_interval)
                continue

        print(f"[ERROR] 下载失败，已达到最大重试次数 ({max_retries})")
        return False

def get_webapp_id(mode: str) -> str:
    """
    从环境变量中获取指定模式的webappId

    Args:
        mode: 模式类型，可以是"short", "portrait", "landscape"

    Returns:
        str: 对应的webappId
    """
    env_key_map = {
        "short": "short_webappId",
        "portrait": "portrait_webappId",
        "landscape": "landscape_webappId",
        "audio": "audio_webappId"
    }

    if mode not in env_key_map:
        raise ValueError(f"不支持的mode: {mode}，支持的类型: {list(env_key_map.keys())}")

    env_key = env_key_map[mode]
    webapp_id = os.getenv(env_key)

    if not webapp_id:
        raise ValueError(f"未找到{env_key}，请在.env文件中配置")

    return webapp_id


def get_api_key() -> str:
    """
    从环境变量中获取API密钥

    Returns:
        str: API密钥
    """
    api_key = os.getenv('RUNNINGHUB_API_KEY')

    if not api_key:
        raise ValueError("未找到RUNNINGHUB_API_KEY，请在.env文件中配置")

    return api_key


def main():
    """主函数，用于单独测试"""
    if len(os.sys.argv) < 2:
        print("用法: python runninghub_api.py <数字人名称> [输入文本文件] [输出文件路径]")
        print("示例: python runninghub_api.py man input.txt output.mp3")
        print("      python runninghub_api.py man input.txt (使用默认输出路径)")
        os.sys.exit(1)

    character_name = os.sys.argv[1]
    input_text_file = os.sys.argv[2] if len(os.sys.argv) > 2 else None
    output_file_path = os.sys.argv[3] if len(os.sys.argv) > 3 else None
    characters_dir = Path("characters")
    character_dir = characters_dir / character_name

    if not character_dir.exists():
        print(f"错误: 数字人目录 {character_dir} 不存在")
        os.sys.exit(1)

    # 检查输入文本文件是否存在（如果提供了）
    input_text = "今天天气真好啊"  # 默认文本
    if input_text_file:
        if not Path(input_text_file).exists():
            print(f"错误: 输入文本文件 {input_text_file} 不存在")
            os.sys.exit(1)
        try:
            with open(input_text_file, 'r', encoding='utf-8') as f:
                input_text = f.read().strip()
            print(f"[OK] 已读取输入文本文件: {input_text_file}")
        except Exception as e:
            print(f"错误: 读取输入文本文件失败: {str(e)}")
            os.sys.exit(1)

    try:
        api = RunningHubAPI()
        success = api.process_character_files(str(character_dir), character_name)
        config = api.load_reference_json(character_dir)
        if config:
            print(f"准备生成音频，文本内容: {input_text}")
            taskid = api.gen_audio(config['voice_id'], input_text)
            while taskid:
                result = api.check_task_status(taskid)
                if result['code']==0:
                    fileUrl=result['data'][0]['fileUrl']

                    # 确定输出路径
                    if output_file_path:
                        # 使用指定的输出路径
                        output_path = Path(output_file_path)
                        # 确保父目录存在
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                    else:
                        # 使用默认输出目录
                        output_dir = Path("output")
                        output_dir.mkdir(exist_ok=True)
                        # 从URL中提取文件名
                        filename = fileUrl.split('/')[-1] if '/' in fileUrl else f"audio_{taskid}.mp3"
                        output_path = output_dir / filename

                    print(f"正在下载生成的音频文件...")
                    if api.download(fileUrl, str(output_path)):
                        print(f"[OK] 音频文件已保存到: {output_path}")
                        break
                    else:
                        print(f"[ERROR] 下载失败，继续等待...")
                        time.sleep(15)
                else:
                    time.sleep(15)

        else:
            print("无法加载配置文件")
        os.sys.exit(0 if success else 1)

    except Exception as e:
        print(f"错误: {str(e)}")
        os.sys.exit(1)


if __name__ == "__main__":
    main()



