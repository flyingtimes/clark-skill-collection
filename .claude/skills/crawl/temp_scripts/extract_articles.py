#!/usr/bin/env python3
"""
文章内容提取器
从 The Atlantic 文章的 HTML 文件中提取正文内容
"""

import os
import re
import sys
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import glob
from pathlib import Path

# =============================================================================
# Windows 平台 UTF-8 编码设置
# =============================================================================
# 在 Windows 系统中，控制台默认使用 GBK 编码，当输出包含中文字符时会出现乱码。
# 通过重新编码标准输出和错误输出流，强制使用 UTF-8 编码，确保中文字符正常显示。
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# =============================================================================
# 日志配置系统
# =============================================================================
def setup_logging():
    """
    设置日志配置系统

    功能说明：
    1. 从环境变量中读取项目根目录配置
    2. 在根目录下创建 logs 文件夹用于存储日志文件
    3. 按日期生成日志文件名（格式：extract_articles_YYYYMMDD.log）
    4. 配置日志同时输出到文件和控制台
    5. 返回配置好的日志记录器实例

    返回：
        logging.Logger: 配置好的日志记录器，用于记录程序运行信息
    """
    # 从环境变量获取项目根目录，如果未设置则使用当前工作目录
    from dotenv import load_dotenv
    load_dotenv()

    root_dir = os.getenv('root_dir')
    if not root_dir:
        root_dir = os.getcwd()  # 如果没有设置root_dir，使用当前目录

    # 在项目根目录下创建 logs 文件夹用于存储日志文件
    log_dir = os.path.join(root_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 生成按日期命名的日志文件名
    log_filename = f"extract_articles_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    # 清除已存在的日志处理器，防止重复运行时日志重复输出
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # 配置日志系统基本设置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # 文件处理器：将日志写入文件，使用 UTF-8 编码支持中文
            logging.FileHandler(log_filepath, encoding='utf-8'),
            # 控制台处理器：同时将日志输出到控制台，便于实时查看
            logging.StreamHandler()
        ]
    )

    # 创建并返回专用的日志记录器实例
    logger = logging.getLogger('extract_articles_skill')
    logger.info(f"日志系统初始化完成，日志文件路径: {log_filepath}")
    return logger

# 在模块级别初始化日志系统，确保整个程序都能使用日志功能
logger = setup_logging()

def extract_article_content(html_file_path):
    """
    从 HTML 文件中提取文章正文内容

    Args:
        html_file_path: HTML 文件路径

    Returns:
        dict: 包含标题、内容和文件名的字典
    """
    filename = os.path.basename(html_file_path)
    logger.info(f"开始提取文章内容: {filename}")

    try:
        # 读取 HTML 文件
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        logger.info(f"成功读取HTML文件: {filename}, 文件大小: {len(html_content)} 字符")

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取文章标题
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "未找到标题"

        # 移除 " - The Atlantic" 后缀
        if title.endswith(' - The Atlantic'):
            title = title[:-15]

        logger.info(f"提取到文章标题: {title}")

        # 使用CSS选择器查找文章正文
        article_content = soup.select_one('.article-content-body')

        if article_content:
            # 获取正文文本
            content_text = article_content.get_text(separator='\n', strip=True)

            # 清理文本：移除多余的空行和空白字符
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = re.sub(r'^\s+|\s+$', '', content_text)

            logger.info(f"成功提取文章内容: {filename}, 内容长度: {len(content_text)} 字符")

            return {
                'filename': filename,
                'title': title,
                'content': content_text,
                'status': 'success'
            }
        else:
            logger.warning(f"主要选择器未找到内容，尝试备用选择器: {filename}")

            # 如果没有找到主要内容区域，尝试其他选择器
            fallback_selectors = [
                'article',
                '.article-body',
                '.post-content',
                '.entry-content',
                '[data-event-surface="article"]'
            ]

            for selector in fallback_selectors:
                element = soup.select_one(selector)
                if element:
                    content_text = element.get_text(separator='\n', strip=True)
                    content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
                    content_text = re.sub(r'^\s+|\s+$', '', content_text)

                    logger.info(f"使用备用选择器成功提取内容: {filename}, 选择器: {selector}")

                    return {
                        'filename': filename,
                        'title': title,
                        'content': content_text,
                        'status': f'fallback_used ({selector})'
                    }

            logger.error(f"所有选择器都无法找到文章内容: {filename}")

            return {
                'filename': filename,
                'title': title,
                'content': '',
                'status': 'no_content_found'
            }

    except Exception as e:
        logger.error(f"解析HTML文件时发生错误: {filename}, 错误信息: {str(e)}")

        return {
            'filename': filename,
            'title': '解析错误',
            'content': '',
            'status': f'error: {str(e)}'
        }

def save_extracted_content(article_data, output_dir='output/articles'):
    """
    将提取的文章内容保存到文件

    Args:
        article_data: 文章数据字典
        output_dir: 输出目录

    Returns:
        str: 保存文件的路径，如果失败返回 None
    """
    filename = article_data['filename']
    title = article_data['title']

    logger.info(f"开始保存文章内容: {title}")
    logger.info(f"来源文件: {filename}, 提取状态: {article_data['status']}")

    try:
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"输出目录已准备: {output_dir}")

        # 生成安全的文件名
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        filename = f"{safe_title}.txt"
        filepath = os.path.join(output_dir, filename)

        logger.info(f"生成安全文件名: {filename}")

        # 保存内容
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(f"标题: {title}\n")
            file.write(f"来源文件: {filename}\n")
            file.write(f"提取状态: {article_data['status']}\n")
            file.write(f"{'='*50}\n\n")
            file.write(article_data['content'])

        logger.info(f"文章内容已成功保存到: {filepath}")
        logger.info(f"保存内容长度: {len(article_data['content'])} 字符")

        return filepath

    except Exception as e:
        logger.error(f"保存文章内容时发生错误: {title}, 错误信息: {str(e)}")
        return None

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("文章内容提取程序启动")
    logger.info("=" * 60)

    try:
        # 获取项目根目录
        root_dir = os.getenv("root_dir")
        if not root_dir:
            logger.warning("未找到 root_dir 环境变量，使用当前工作目录")
            root_dir = os.getcwd()

        logger.info(f"项目根目录: {root_dir}")

        # 准备输出目录
        full_path = os.path.join(root_dir, "output", "extracted_articles")
        os.makedirs(full_path, exist_ok=True)
        logger.info(f"输出目录已准备: {full_path}")

        # 查找所有文章文件
        html_path = os.path.join(root_dir, "output", "html", "*.txt")
        article_files = glob.glob(html_path)

        if not article_files:
            logger.error(f"未找到文章文件! 搜索路径: {html_path}")
            return

        logger.info(f"找到 {len(article_files)} 个文章文件")

        results = []
        success_count = 0
        error_count = 0

        # 处理每个文件
        for i, file_path in enumerate(article_files, 1):
            filename = os.path.basename(file_path)
            logger.info(f"[{i}/{len(article_files)}] 正在处理文件: {filename}")

            try:
                # 提取内容
                article_data = extract_article_content(file_path)
                results.append(article_data)

                # 保存提取的内容
                if article_data['content']:
                    saved_path = save_extracted_content(article_data, output_dir=full_path)
                    if saved_path:
                        logger.info(f"  ✓ 成功保存到: {saved_path}")
                        success_count += 1
                    else:
                        logger.error(f"  ✗ 保存失败: {filename}")
                        error_count += 1
                else:
                    logger.warning(f"  ✗ 未能提取到内容: {article_data['status']}")
                    error_count += 1

            except Exception as e:
                logger.error(f"  ✗ 处理文件时发生异常: {filename}, 错误: {str(e)}")
                error_count += 1
                # 添加错误结果到列表
                results.append({
                    'filename': filename,
                    'title': '处理错误',
                    'content': '',
                    'status': f'processing_error: {str(e)}'
                })

        # 生成最终报告
        logger.info("=" * 60)
        logger.info("文章内容提取完成!")
        logger.info(f"总文件数: {len(article_files)}")
        logger.info(f"成功提取: {success_count}")
        logger.info(f"提取失败: {error_count}")
        logger.info(f"成功率: {(success_count/len(article_files)*100):.1f}%")
        logger.info("=" * 60)

        # 显示详细结果
        logger.info("详细处理结果:")
        for result in results:
            if result['content']:
                logger.info(f"✓ 成功: {result['filename']}")
                logger.info(f"   标题: {result['title']}")
                logger.info(f"   状态: {result['status']}")
                if len(result['content']) > 0:
                    content_preview = result['content'][:100].replace('\n', ' ')
                    logger.info(f"   预览: {content_preview}...")
            else:
                logger.error(f"✗ 失败: {result['filename']}")
                logger.error(f"   标题: {result['title']}")
                logger.error(f"   状态: {result['status']}")
            logger.info("-" * 40)

    except Exception as e:
        logger.error(f"程序执行过程中发生严重错误: {str(e)}")
        logger.exception("详细错误信息:")
        raise

    logger.info("文章内容提取程序执行完毕")

if __name__ == "__main__":
    main()