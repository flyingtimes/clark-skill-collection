#!/usr/bin/env python3
"""
文章内容提取器
从 The Atlantic 文章的 HTML 文件中提取正文内容
"""

import os
import re
from bs4 import BeautifulSoup
import glob
from pathlib import Path

def extract_article_content(html_file_path):
    """
    从 HTML 文件中提取文章正文内容

    Args:
        html_file_path: HTML 文件路径

    Returns:
        dict: 包含标题、内容和文件名的字典
    """
    try:
        # 读取 HTML 文件
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取文章标题
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "未找到标题"

        # 移除 " - The Atlantic" 后缀
        if title.endswith(' - The Atlantic'):
            title = title[:-15]

        # 使用CSS选择器查找文章正文
        article_content = soup.select_one('.article-content-body')

        if article_content:
            # 获取正文文本
            content_text = article_content.get_text(separator='\n', strip=True)

            # 清理文本：移除多余的空行和空白字符
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = re.sub(r'^\s+|\s+$', '', content_text)

            return {
                'filename': os.path.basename(html_file_path),
                'title': title,
                'content': content_text,
                'status': 'success'
            }
        else:
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

                    return {
                        'filename': os.path.basename(html_file_path),
                        'title': title,
                        'content': content_text,
                        'status': f'fallback_used ({selector})'
                    }

            return {
                'filename': os.path.basename(html_file_path),
                'title': title,
                'content': '',
                'status': 'no_content_found'
            }

    except Exception as e:
        return {
            'filename': os.path.basename(html_file_path),
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
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 生成安全的文件名
    safe_title = re.sub(r'[^\w\s-]', '', article_data['title'])
    safe_title = re.sub(r'\s+', '_', safe_title)
    filename = f"{safe_title}.txt"
    filepath = os.path.join(output_dir, filename)

    # 保存内容
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(f"标题: {article_data['title']}\n")
        file.write(f"来源文件: {article_data['filename']}\n")
        file.write(f"提取状态: {article_data['status']}\n")
        file.write(f"{'='*50}\n\n")
        file.write(article_data['content'])

    return filepath

def main():
    """主函数"""
    print("开始提取文章内容...")
    root_dir = os.getenv("root_dir")
    full_path = os.path.join(root_dir, "output/articles")
    os.makedirs(full_path, exist_ok=True)
    html_path = os.path.join(root_dir, "output/html/*.txt")
    # 查找所有文章文件
    article_files = glob.glob(html_path)

    if not article_files:
        print("未找到文章文件!")
        return

    print(f"找到 {len(article_files)} 个文章文件")

    results = []
    success_count = 0

    for file_path in article_files:
        print(f"正在处理: {os.path.basename(file_path)}")

        # 提取内容
        article_data = extract_article_content(file_path)
        results.append(article_data)

        # 保存提取的内容
        if article_data['content']:
            saved_path = save_extracted_content(article_data, output_dir=os.path.join(root_dir, "output/extracted_articles"))
            print(f"  [成功] 内容已保存到: {saved_path}")
            success_count += 1
        else:
            print(f"  [失败] 未能提取到内容: {article_data['status']}")

    # 生成报告
    print(f"\n{'='*50}")
    print("提取完成!")
    print(f"总文件数: {len(article_files)}")
    print(f"成功提取: {success_count}")
    print(f"失败数量: {len(article_files) - success_count}")

    # 显示详细结果
    print(f"\n{'='*50}")
    print("详细结果:")
    for result in results:
        status_symbol = "[成功]" if result['content'] else "[失败]"
        print(f"{status_symbol} {result['filename']}")
        print(f"   标题: {result['title']}")
        print(f"   状态: {result['status']}")
        if result['content']:
            content_preview = result['content'][:200].replace('\n', ' ')
            print(f"   预览: {content_preview}...")
        print()

if __name__ == "__main__":
    main()