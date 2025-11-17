#!/usr/bin/env python3
"""
图片分析工具 - 使用Zhipu AI分析图片内容
"""

import argparse
import base64
import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from PIL import Image
from zai._client import ZhipuAiClient


@dataclass
class Config:
    """配置类"""
    api_key_env: str = 'zhipu_search_apikey'
    model_name: str = 'glm-4.5v'

    def get_api_key(self) -> str:
        """获取API密钥"""
        load_dotenv()
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"未找到环境变量 {self.api_key_env}")
        return api_key


class ImageProcessor:
    """图像处理器"""

    @staticmethod
    def to_base64(file_input: Union[str, Path, Image.Image]) -> str:
        """将图像转换为base64格式"""
        if isinstance(file_input, (str, Path)):
            return ImageProcessor._file_to_base64(Path(file_input))
        elif isinstance(file_input, Image.Image):
            return ImageProcessor._pil_to_base64(file_input)
        else:
            raise TypeError("输入必须是文件路径或PIL.Image对象")

    @staticmethod
    def _file_to_base64(file_path: Path) -> str:
        """文件转base64"""
        if not file_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {file_path}")

        with file_path.open('rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    @staticmethod
    def _pil_to_base64(image: Image.Image) -> str:
        """PIL图像转base64"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


class VisionAnalyzer:
    """视觉分析器"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.client = ZhipuAiClient(api_key=self.config.get_api_key())

    def analyze(self, image_input: Union[str, Path, Image.Image], prompt: str):
        """分析图像内容"""
        img_base64 = ImageProcessor.to_base64(image_input)
        return self._call_api(img_base64, prompt)

    def _call_api(self, img_base64: str, prompt: str):
        """调用AI API"""
        print("正在分析图像...")
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_base64}},
                    {"type": "text", "text": prompt}
                ]
            }],
            thinking={"type": "enabled"}
        )
        return response.choices[0].message


class OutputHandler:
    """输出处理器"""

    @staticmethod
    def save_result(content: str, output_path: Union[str, Path] = None):
        """保存或显示结果"""
        if output_path:
            Path(output_path).write_text(content, encoding='utf-8')
            print(f"分析结果已保存到: {output_path}")
        else:
            print("\n" + "=" * 50)
            print("分析结果:")
            print("=" * 50)
            print(content)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="图片分析工具 - 使用Zhipu AI分析图片内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python vision_analyzer.py image.jpg "请描述这个图片"
  python vision_analyzer.py screenshot.png "这个界面有什么问题？"
  python vision_analyzer.py photo.jpg "识别图片中的文字内容" -o result.txt
        """
    )

    parser.add_argument("file_path", help="图片文件路径")
    parser.add_argument("prompt", help="分析需求描述")
    parser.add_argument("-o", "--output", help="结果保存路径")

    args = parser.parse_args()

    try:
        # 初始化分析器并执行分析
        analyzer = VisionAnalyzer()
        result = analyzer.analyze(args.file_path, args.prompt)

        # 处理输出
        content = getattr(result, 'content', str(result))
        OutputHandler.save_result(content, args.output)

    except (FileNotFoundError, ValueError, TypeError) as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"分析过程中出现异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()