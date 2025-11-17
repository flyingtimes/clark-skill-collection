#!/usr/bin/env python3
"""
智谱搜索引擎工具
根据用户查询进行网络搜索
"""

import os
import json
import sys
from datetime import datetime, timedelta
from zai import ZhipuAiClient
from dotenv import load_dotenv
load_dotenv()
# 设置控制台编码为UTF-8，解决Windows下中文显示问题
if sys.platform == 'win32':
    import locale
    import codecs
    # 尝试设置控制台编码
    try:
        # 重新配置标准输出流
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def safe_print(text):
    """安全打印函数，确保中文正确显示"""
    try:
        print(text)
    except UnicodeEncodeError:
        # 如果出现编码错误，尝试使用其他编码
        try:
            print(text.encode('gbk', errors='ignore').decode('gbk'))
        except:
            # 最后的选择：移除非ASCII字符
            safe_text = ''.join(char if ord(char) < 128 else '?' for char in str(text))
            print(safe_text)

def get_current_date():
    """获取当前日期"""
    return datetime.now()

def analyze_time_query(query):
    """分析查询中的时间关键词，转换为具体日期"""
    current_date = get_current_date()
    query_lower = query.lower()

    # 时间关键词映射
    time_keywords = {
        '今天': current_date.strftime('%Y年%m月%d日'),
        '昨天': (current_date - timedelta(days=1)).strftime('%Y年%m月%d日'),
        '明天': (current_date + timedelta(days=1)).strftime('%Y年%m月%d日'),
        '本周': current_date.strftime('%Y年第%W周'),
        '上周': (current_date - timedelta(weeks=1)).strftime('%Y年第%W周'),
        '本月': current_date.strftime('%Y年%m月'),
        '上月': (current_date - timedelta(days=current_date.day)).strftime('%Y年%m月'),
    }

    # 替换时间关键词
    modified_query = query
    for keyword, replacement in time_keywords.items():
        if keyword in query_lower:
            modified_query = modified_query.replace(keyword, replacement)
            safe_print(f"检测到时间关键词 '{keyword}'，转换为: {replacement}")
            break

    return modified_query

def search_news(query):
    """搜索新闻"""
    try:
        # 从环境变量获取API key
        api_key = os.getenv('zhipu_search_apikey')
        if not api_key:
            # 尝试从.env文件读取
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            if os.path.exists(env_file):
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('zhipu_search_apikey='):
                            api_key = line.split('=', 1)[1].strip()
                            break

        if not api_key:
            safe_print("错误：未找到智谱搜索API密钥")
            safe_print("请在.env文件中设置 zhipu_search_apikey=your_api_key")
            return None

        # 分析时间查询
        modified_query = analyze_time_query(query)
        safe_print(f"原始查询: {query}")
        safe_print(f"修改后查询: {modified_query}")

        # 创建客户端
        client = ZhipuAiClient(api_key=api_key)

        # 执行搜索
        response = client.web_search.web_search(
            search_engine="search_pro",
            search_query=modified_query,
            count=10,
            search_recency_filter="noLimit",
            content_size="high"
        )

        return response

    except Exception as e:
        safe_print(f"搜索过程中发生错误: {e}")
        return None

def format_search_results(response):
    """格式化搜索结果"""
    if not response:
        return "搜索失败，未获取到结果"

    try:
        results = []

        # 解析搜索结果
        if hasattr(response, 'search_result') and response.search_result:
            for i, item in enumerate(response.search_result, 1):
                title = getattr(item, 'title', '无标题')
                content = getattr(item, 'content', '无内容')
                link = getattr(item, 'link', '无链接')
                media = getattr(item, 'media', '未知媒体')
                publish_date = getattr(item, 'publish_date', '未知日期')

                result = f"""
### {i}. {title}

**来源:** {media}
**发布时间:** {publish_date}
**链接:** {link}

**内容摘要:**
{content[:300]}{'...' if len(content) > 300 else ''}

---
"""
                results.append(result)

        if results:
            return f"## 📰 搜索结果 ({len(results)}条)\n\n" + "".join(results)
        else:
            return "未找到相关搜索结果"

    except Exception as e:
        return f"格式化搜索结果时发生错误: {e}"

def main():
    """主函数"""
    if len(sys.argv) < 2:
        safe_print("使用方法: python zhipu_searcher.py '搜索查询'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    safe_print(f"开始搜索: {query}")
    safe_print("=" * 50)

    # 创建输出目录
    root_dir = os.getenv('root_dir')
    if root_dir:
        output_dir = os.path.join(root_dir, 'output')
    else:
        # 如果环境变量不存在，使用默认路径
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)

    # 执行搜索
    response = search_news(query)

    # 格式化结果
    formatted_results = format_search_results(response)

    # 输出结果
    safe_print(formatted_results)

    # 保存结果到文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'search_results_{timestamp}.txt')

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"搜索查询: {query}\n")
            f.write(f"搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            f.write(formatted_results)

        safe_print(f"\n搜索结果已保存到: {output_file}")
    except Exception as e:
        safe_print(f"保存搜索结果时发生错误: {e}")

if __name__ == "__main__":
    main()