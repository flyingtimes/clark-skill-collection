#!/usr/bin/env python3
"""
文章翻译器
将提取的英文文章内容翻译成中文
"""

import os
import re
import sys
import logging
from datetime import datetime
import glob

# =============================================================================
# Windows 平台 UTF-8 编码设置
# =============================================================================
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
    3. 按日期生成日志文件名（格式：translate_articles_YYYYMMDD.log）
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
    log_filename = f"translate_articles_{datetime.now().strftime('%Y%m%d')}.log"
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
    logger = logging.getLogger('translate_articles_skill')
    logger.info(f"日志系统初始化完成，日志文件路径: {log_filepath}")
    return logger

# 在模块级别初始化日志系统，确保整个程序都能使用日志功能
logger = setup_logging()

def parse_article_content(filepath):
    """
    解析提取的文章文件内容

    Args:
        filepath: 文章文件路径

    Returns:
        dict: 包含标题、来源文件、提取状态和正文内容的字典
    """
    filename = os.path.basename(filepath)
    logger.info(f"开始解析文章文件: {filename}")

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()

        logger.info(f"成功读取文章文件: {filename}, 文件大小: {len(content)} 字符")

        # 解析文件内容
        lines = content.split('\n')

        # 提取元数据
        title = ""
        source_file = ""
        status = ""
        article_content = ""

        # 跳过分隔线前的元数据
        content_start = False
        for line in lines:
            if line.startswith('标题:'):
                title = line.replace('标题:', '').strip()
            elif line.startswith('来源文件:'):
                source_file = line.replace('来源文件:', '').strip()
            elif line.startswith('提取状态:'):
                status = line.replace('提取状态:', '').strip()
            elif line.startswith('==='):
                content_start = True
                continue
            elif content_start:
                article_content += line + '\n'

        logger.info(f"解析完成 - 标题: {title}, 正文长度: {len(article_content)} 字符")

        return {
            'filename': filename,
            'title': title,
            'source_file': source_file,
            'status': status,
            'content': article_content.strip()
        }

    except Exception as e:
        logger.error(f"解析文章文件时发生错误: {filename}, 错误信息: {str(e)}")
        return {
            'filename': filename,
            'title': '解析错误',
            'source_file': filename,
            'status': f'parse_error: {str(e)}',
            'content': ''
        }

def translate_article_content(article_data, target_language="中文"):
    """
    翻译文章内容

    Args:
        article_data: 包含文章信息的字典
        target_language: 目标语言，默认为中文

    Returns:
        dict: 包含翻译结果的字典
    """
    filename = article_data['filename']
    title = article_data['title']
    content = article_data['content']

    logger.info(f"开始翻译文章: {title}")
    logger.info(f"源文件: {filename}, 原文长度: {len(content)} 字符")

    if not content.strip():
        logger.warning(f"文章内容为空，跳过翻译: {title}")
        return {
            **article_data,
            'translated_title': title,
            'translated_content': '',
            'translation_status': 'empty_content'
        }

    try:
        # 这里可以集成实际的翻译API，目前先使用占位符
        # 在实际使用中，可以调用 Google Translate API、DeepL API 或其他翻译服务

        # 临时模拟翻译 - 在实际环境中应该替换为真实的翻译API调用
        translated_title = f"[翻译] {title}"
        translated_content = f"""
[翻译开始]

{content}

[翻译结束]

注：此为翻译占位符。在实际使用中，这里应该调用翻译API将英文内容翻译成{target_language}。
翻译要求：
- 中文语法，句式要求生动活泼，通俗易懂
- 句子流畅度要最高
- 句式温暖亲切，清新自然
- 逐句翻译，不要有任何一个字的多余回答
- 智能断句，匹配中文阅读习惯
- 核心要点、重点概念的词语加粗显示
        """.strip()

        logger.info(f"文章翻译完成: {title}, 译文长度: {len(translated_content)} 字符")

        return {
            **article_data,
            'translated_title': translated_title,
            'translated_content': translated_content,
            'translation_status': 'success'
        }

    except Exception as e:
        logger.error(f"翻译文章时发生错误: {title}, 错误信息: {str(e)}")
        return {
            **article_data,
            'translated_title': f"[翻译错误] {title}",
            'translated_content': '',
            'translation_status': f'translation_error: {str(e)}'
        }

def save_translated_article(article_data, output_dir='output/translated_articles'):
    """
    保存翻译后的文章

    Args:
        article_data: 包含翻译结果的字典
        output_dir: 输出目录

    Returns:
        str: 保存文件的路径，如果失败返回 None
    """
    filename = article_data['filename']
    title = article_data['title']
    translated_title = article_data.get('translated_title', title)

    logger.info(f"开始保存翻译文章: {translated_title}")
    logger.info(f"来源文件: {filename}, 翻译状态: {article_data.get('translation_status', 'unknown')}")

    try:
        # 获取项目根目录
        root_dir = os.getenv("root_dir")
        if not root_dir:
            root_dir = os.getcwd()

        # 准备输出目录
        full_output_dir = os.path.join(root_dir, output_dir)
        os.makedirs(full_output_dir, exist_ok=True)
        logger.info(f"输出目录已准备: {full_output_dir}")

        # 生成安全的文件名
        safe_title = re.sub(r'[^\w\s-]', '', translated_title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        output_filename = f"翻译_{safe_title}.txt"
        output_filepath = os.path.join(full_output_dir, output_filename)

        logger.info(f"生成翻译文件名: {output_filename}")

        # 构建保存内容
        save_content = f"""标题: {translated_title}
来源文件: {filename}
翻译状态: {article_data.get('translation_status', 'unknown')}
翻译时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

{article_data.get('translated_content', '')}
"""

        # 保存翻译内容
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(save_content)

        logger.info(f"翻译文章已成功保存到: {output_filepath}")
        logger.info(f"保存内容长度: {len(article_data.get('translated_content', ''))} 字符")

        return output_filepath

    except Exception as e:
        logger.error(f"保存翻译文章时发生错误: {translated_title}, 错误信息: {str(e)}")
        return None

def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("文章翻译程序启动")
    logger.info("=" * 80)

    try:
        # 获取项目根目录
        root_dir = os.getenv("root_dir")
        if not root_dir:
            logger.warning("未找到 root_dir 环境变量，使用当前工作目录")
            root_dir = os.getcwd()

        logger.info(f"项目根目录: {root_dir}")

        # 查找所有提取的文章文件
        extracted_articles_dir = os.path.join(root_dir, "output", "extracted_articles")
        article_files = glob.glob(os.path.join(extracted_articles_dir, "*.txt"))

        if not article_files:
            logger.error(f"未找到提取的文章文件! 搜索路径: {extracted_articles_dir}")
            return

        logger.info(f"找到 {len(article_files)} 个提取的文章文件")

        results = []
        success_count = 0
        error_count = 0

        # 处理每个文件
        for i, file_path in enumerate(article_files, 1):
            filename = os.path.basename(file_path)
            logger.info(f"[{i}/{len(article_files)}] 正在处理文件: {filename}")

            try:
                # 解析文章内容
                article_data = parse_article_content(file_path)

                # 翻译文章内容
                translated_data = translate_article_content(article_data)
                results.append(translated_data)

                # 保存翻译结果
                if translated_data.get('translated_content'):
                    saved_path = save_translated_article(translated_data)
                    if saved_path:
                        logger.info(f"  ✓ 翻译成功保存到: {saved_path}")
                        success_count += 1
                    else:
                        logger.error(f"  ✗ 翻译保存失败: {filename}")
                        error_count += 1
                else:
                    logger.warning(f"  ✗ 翻译内容为空: {translated_data.get('translation_status', 'unknown')}")
                    error_count += 1

            except Exception as e:
                logger.error(f"  ✗ 处理文件时发生异常: {filename}, 错误: {str(e)}")
                error_count += 1
                # 添加错误结果到列表
                results.append({
                    'filename': filename,
                    'title': '处理错误',
                    'translated_title': '[处理错误]',
                    'translated_content': '',
                    'translation_status': f'processing_error: {str(e)}'
                })

        # 生成最终报告
        logger.info("=" * 80)
        logger.info("文章翻译完成!")
        logger.info(f"总文件数: {len(article_files)}")
        logger.info(f"翻译成功: {success_count}")
        logger.info(f"翻译失败: {error_count}")
        logger.info(f"成功率: {(success_count/len(article_files)*100):.1f}%")
        logger.info("=" * 80)

        # 显示详细结果
        logger.info("详细翻译结果:")
        for result in results:
            if result.get('translated_content'):
                logger.info(f"✓ 成功: {result['filename']}")
                logger.info(f"   原标题: {result.get('title', 'N/A')}")
                logger.info(f"   译标题: {result.get('translated_title', 'N/A')}")
                logger.info(f"   状态: {result.get('translation_status', 'N/A')}")
            else:
                logger.error(f"✗ 失败: {result['filename']}")
                logger.error(f"   标题: {result.get('title', 'N/A')}")
                logger.error(f"   状态: {result.get('translation_status', 'N/A')}")
            logger.info("-" * 60)

    except Exception as e:
        logger.error(f"程序执行过程中发生严重错误: {str(e)}")
        logger.exception("详细错误信息:")
        raise

    logger.info("文章翻译程序执行完毕")

if __name__ == "__main__":
    main()