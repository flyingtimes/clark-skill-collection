# =============================================================================
# 网页爬虫程序 - 抓取 The Atlantic 网站文章
# =============================================================================
#
# 程序功能概述：
# 该程序是一个智能化的网页爬虫系统，专门用于抓取 The Atlantic 网站的最新文章。
# 它结合了现代浏览器自动化技术和人工智能，能够智能地识别、提取并保存文章内容。
#
# 核心技术栈：
# - Stagehand: 基于 Playwright 的网页自动化框架，支持 AI 辅助的页面理解
# - 智谱AI GLM-4.6: 用于页面内容理解和结构化信息提取
# - Pydantic: 数据验证和模型定义，确保数据结构的完整性
# - 异步编程: 使用 asyncio 提高并发性能和抓取效率
#
# 工作流程：
# 1. 初始化浏览器环境和 AI 模型配置
# 2. 访问 The Atlantic 最新文章页面
# 3. 使用 AI 识别并提取最新文章列表
# 4. 逐篇访问文章页面，提取完整的标题、副标题、作者和正文内容
# 5. 清理和格式化文本内容，保存到本地文件
# 6. 完善的错误处理和日志记录机制
#
# 使用说明：
# - 确保 Chrome 浏览器在调试模式运行（端口 9222）
# - 配置正确的环境变量（API 密钥等）
# - 程序会自动创建 output 目录保存抓取的文章
# - 日志文件保存在 logs 目录，便于调试和监控
# =============================================================================

import asyncio          # 异步编程库：用于处理异步I/O操作，支持高并发的网络请求和页面操作
import os              # 操作系统接口：提供文件路径处理、环境变量访问、目录操作等系统级功能
import re              # 正则表达式库：用于字符串模式匹配、文本清理和文件名规范化
import sys             # 系统参数和函数：处理系统级别的操作，如编码设置、程序退出等
import logging         # 日志记录库：提供结构化的日志记录功能，支持多级别日志和文件输出

# =============================================================================
# Windows 平台 UTF-8 编码设置
# =============================================================================
# 问题描述：
# 在 Windows 系统中，控制台默认使用 GBK 编码，当输出包含中文字符时会出现乱码。
# 这会影响程序运行时的中文日志显示和错误信息输出。
#
# 解决方案：
# 通过重新编码标准输出和错误输出流，强制使用 UTF-8 编码，确保中文字符正常显示。
# 这对于包含中文内容的爬虫程序尤为重要，因为文章标题、内容等可能包含中文。
if sys.platform == "win32":
    import codecs
    # 将标准输出流重新编码为 UTF-8，解决中文显示问题
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    # 将错误输出流重新编码为 UTF-8，确保错误信息中的中文能正常显示
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# =============================================================================
# 第三方库导入
# =============================================================================

# 环境变量管理：从 .env 文件加载配置信息，包括 API 密钥、代理设置等敏感信息
# 避免在代码中硬编码配置，提高安全性和可维护性
from dotenv import load_dotenv

# Stagehand 网页自动化框架：
# - Stagehand: 主要的自动化类，提供页面操作和 AI 辅助功能
# - StagehandConfig: 配置类，用于设置浏览器选项、模型参数等
from stagehand import Stagehand, StagehandConfig

# Pydantic 数据验证和模型定义：
# - BaseModel: 所有数据模型的基类，提供数据验证和序列化功能
# - Field: 字段定义装饰器，用于描述字段的约束和说明
# - HttpUrl: URL 类型验证器，确保链接格式正确
from pydantic import BaseModel, Field, HttpUrl

def setup_logging():
    """
    设置日志配置系统

    功能说明：
    1. 从环境变量中读取项目根目录配置
    2. 在根目录下创建 logs 文件夹用于存储日志文件
    3. 按日期生成日志文件名（格式：crawl_YYYYMMDD.log）
    4. 配置日志同时输出到文件和控制台
    5. 返回配置好的日志记录器实例

    返回：
        logging.Logger: 配置好的日志记录器，用于记录程序运行信息
    """
    # 首先加载 .env 文件中的环境变量，确保能获取到 root_dir 配置
    load_dotenv()

    # 从环境变量获取项目根目录，如果未设置则使用当前工作目录
    root_dir = os.getenv('root_dir')
    if not root_dir:
        root_dir = os.getcwd()  # 如果没有设置root_dir，使用当前目录

    # 在项目根目录下创建 logs 文件夹用于存储日志文件
    # exist_ok=True 表示如果目录已存在不会抛出异常
    log_dir = os.path.join(root_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 生成按日期命名的日志文件名，便于管理和查找
    # 格式：crawl_YYYYMMDD.log，例如：crawl_20231121.log
    from datetime import datetime
    log_filename = f"crawl_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    # 清除已存在的日志处理器，防止重复运行时日志重复输出
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # 配置日志系统基本设置
    logging.basicConfig(
        level=logging.INFO,  # 设置日志级别为 INFO，记录 INFO 及以上级别的日志
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
        handlers=[
            # 文件处理器：将日志写入文件，使用 UTF-8 编码支持中文
            logging.FileHandler(log_filepath, encoding='utf-8'),
            # 控制台处理器：同时将日志输出到控制台，便于实时查看
            logging.StreamHandler()
        ]
    )

    # 创建并返回专用的日志记录器实例
    logger = logging.getLogger('crawl_skill')
    logger.info(f"日志系统初始化完成，日志文件路径: {log_filepath}")
    return logger

# 在模块级别初始化日志系统，确保整个程序都能使用日志功能
logger = setup_logging()

class EssayInfo(BaseModel):
    """
    文章信息数据模型 - 存储单篇完整文章的结构化信息

    模型说明：
    使用 Pydantic BaseModel 定义文章的完整数据结构，确保从网页提取的
    文章信息具有一致的格式和数据完整性。该模型作为AI提取的目标模式，
    指导AI准确识别和提取所需信息。

    字段设计：
    - title: 文章的主标题，用于识别和索引文章
    - subtitle: 文章的副标题或导语，通常包含文章的核心观点
    - content: 完整的正文内容，排除广告、导航等无关元素
    - author: 文章作者信息，用于内容溯源和版权管理

    使用场景：
    1. AI模型提取文章内容时的目标模式
    2. 数据验证和格式化
    3. 文件保存时的结构化数据
    """
    title: str = Field(..., description="文章主标题，用于识别和索引文章内容")
    subtitle: str = Field(..., description="文章副标题或摘要导语，通常包含核心观点")
    content: str = Field(..., description="完整正文内容，已过滤广告等无关元素")
    author: str = Field(..., description="文章作者姓名，用于内容溯源")

class EssayUrl(BaseModel):
    """
    文章链接数据模型 - 存储文章的基本信息和访问链接

    模型说明：
    该模型用于存储从文章列表页面提取的基本信息，包含文章标题
    和对应的访问链接。作为文章链接收集阶段的数据结构。

    字段设计：
    - title: 文章标题，用于用户识别和后续文件命名
    - href: 文章的完整URL地址，使用HttpUrl确保格式正确

    使用场景：
    1. 文章列表的信息提取
    2. 批量文章抓取的队列管理
    3. 文章链接有效性验证
    """
    title: str = Field(..., description="文章标题，用于识别和文件命名")
    href: HttpUrl = Field(..., description="文章的完整URL地址，支持自动验证")

class EssayUrls(BaseModel):
    """
    文章列表容器模型 - 存储多篇链接的集合

    模型说明：
    该模型作为文章链接列表的容器，用于AI批量提取时的结构化输出。
    支持多篇文章的统一管理，便于后续的批量处理。

    设计优势：
    1. 支持动态数量的文章链接
    2. 统一的数据验证和格式化
    3. 便于AI理解和生成结构化输出

    使用场景：
    1. 首页文章列表的批量提取
    2. 分页抓取的数据聚合
    3. 文章队列的数据管理
    """
    list_of_EssayUrl: list[EssayUrl] = Field(..., description="文章链接对象列表，包含所有待抓取的文章信息")

def sanitize_filename(title: str, index: int) -> str:
    """
    文件名清理函数 - 将文章标题转换为跨平台兼容的文件名

    功能背景：
    网页文章标题通常包含各种特殊字符（冒号、引号、斜杠等），这些字符
    在不同操作系统的文件系统中可能具有特殊含义或被禁止使用。为了确保
    生成的文件能在Windows、macOS、Linux等系统上正常使用，需要对标题
    进行清理和规范化。

    清理策略：
    1. 移除系统禁用字符：处理Windows、Unix系统的文件名限制
    2. 保留有意义字符：保留字母、数字、空格和基本标点
    3. 标准化分隔符：统一使用下划线替代各种空白字符
    4. 长度控制：防止文件名过长导致的系统问题
    5. 容错机制：确保在任何情况下都能生成有效文件名

    参数设计：
    - title: 原始文章标题，可能包含各种语言和特殊字符
    - index: 文章索引，用作后备文件名，确保唯一性

    返回保证：
    返回的文件名确保在主流操作系统上都能正常创建和使用，
    同时尽可能保持原文的可读性和识别性。

    参数：
        title (str): 原始文章标题字符串
        index (int): 文章在列表中的索引位置（从0开始）

    返回：
        str: 清理后的安全文件名字符串
    """
    # 第一步：移除Windows系统明确禁止的文件名字符
    # Windows禁用字符：< > : " / \ | ? *
    # 这些字符在Windows文件名中具有特殊含义或系统保留
    clean_title = re.sub(r'[<>:"/\\|?*]', '', title)

    # 第二步：移除可能导致问题的特殊字符
    # 保留字母、数字、空格、连字符和下划线，移除其他符号
    # \w 匹配：字母（a-z,A-Z）、数字（0-9）、下划线（_）
    # \s 匹配：各种空白字符（空格、制表符、换行符等）
    # - 匹配：连字符，常用于复合词
    clean_title = re.sub(r'[^\w\s-]', '', clean_title)

    # 第三步：标准化空白字符
    # 将所有连续的空白字符替换为单个下划线，提高文件名的可读性
    # 同时去除首尾空白，避免文件名以空格开头或结尾
    clean_title = re.sub(r'\s+', '_', clean_title.strip())

    # 第四步：长度限制
    # 大多数文件系统对文件名长度有限制（通常是255字符）
    # 限制为100字符确保在所有系统上都能正常工作，同时保留足够信息
    clean_title = clean_title[:100]

    # 第五步：容错处理
    # 如果清理后标题为空（比如原标题只包含特殊字符），
    # 使用基于索引的默认文件名，确保文件名不为空且唯一
    return clean_title or f"article_{index + 1}"

def save_article(content: str, filename: str) -> bool:
    """
    将文章内容保存到指定文件

    功能说明：
    1. 从环境变量获取项目根目录路径
    2. 构建完整的文件路径
    3. 确保目标目录存在（如果不存在则创建）
    4. 以 UTF-8 编码将内容写入文件
    5. 记录保存结果到日志

    参数：
        content (str): 要保存的文章内容
        filename (str): 相对于根目录的文件路径

    返回：
        bool: 保存成功返回 True，失败返回 False
    """
    # 从环境变量获取项目根目录，用于统一管理文件存储位置
    root_dir = os.getenv("root_dir")

    # 构建完整的文件路径：如果设置了根目录则拼接，否则使用相对路径
    full_path = os.path.join(root_dir, filename) if root_dir else filename

    try:
        # 确保文件的父目录存在，不存在则创建
        # dirname() 获取文件的目录部分，exist_ok=True 避免重复创建时报错
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # 以 UTF-8 编码打开文件并写入内容
        # UTF-8 编码确保中文等非 ASCII 字符能够正确保存
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 记录成功保存的信息到日志
        logger.info(f"文章已保存到: {full_path}")
        return True

    except Exception as e:
        # 捕获并记录文件写入过程中可能出现的任何异常
        logger.error(f"文件写入失败: {e}")
        return False

async def process_single_article(page, action, index: int) -> bool:
    """
    处理单篇文章的完整流程

    处理步骤：
    1. 点击文章链接，导航到文章页面
    2. 等待页面加载完成
    3. 提取文章的结构化信息（标题、副标题、作者、正文）
    4. 生成文件名并保存文章内容
    5. 安全返回到文章列表页面

    容错机制：
    - 内容提取失败时记录错误并返回 False
    - 处理过程中出现异常时截图保存现场
    - 无论成功与否都会尝试返回上一页

    参数：
        page: Stagehand/Playwright 页面对象
        action: 包含文章链接和描述信息的动作对象
        index (int): 当前文章的索引号，用于日志记录和默认命名

    返回：
        bool: 处理成功返回 True，失败返回 False
    """
    try:
        # 记录开始处理的文章信息
        logger.info(f"处理第 {index + 1} 篇文章: {action.title}")
        logger.info(action)  # 记录完整的动作对象信息，便于调试

        # 执行点击操作，导航到文章页面
        # 将HttpUrl对象转换为字符串，避免序列化错误
        await page.goto(str(action.href), timeout=60000)

        # 等待页面的 DOM 内容加载完成
        # domcontentloaded 比 load 更快，适合内容提取
        await page.wait_for_load_state("domcontentloaded")

        # 尝试从页面中提取结构化文章信息
        try:
            # 使用 AI 模型提取文章信息，按照 EssayInfo 模型结构化
            # 提示中明确要求排除广告内容，确保获取纯净的文章正文
            result = await page.extract(
                "提取文章的标题、副标题、作者名字、完整的正文内容，请注意正文可能被广告打断，请不要包含广告内容，而是获取整个页面中完整的文章正文内容",
                schema=EssayInfo
            )
            logger.info(result)  # 记录提取结果
        except Exception as e:
            # 内容提取失败的错误处理
            logger.error(f"文章内容提取失败: {e}")
            return False
        if result.content and len(result.content)>200:
            # 将文章标题转换为合法的文件名
            clean_title = sanitize_filename(result.title, index)

            # 构建输出文件路径，保存在 output/html 目录下
            filename = f"output/html/{clean_title}.txt"

            # 保存文章正文内容到文件
            save_article(result.content, filename)

            # 在控制台显示保存结果，提供用户反馈
            print(f"文章已保存到: {filename}")

            return True
        logger.error(f"无法正常提取第 {index + 1} 篇文章内容")
        return False

    except Exception as e:
        # 处理过程中出现任何异常时的错误处理
        logger.error(f"处理第 {index + 1} 篇文章时发生错误: {e}")

        # 获取项目根目录，用于保存错误截图
        root_dir = os.getenv("root_dir")

        # 在异常情况下，clean_title 可能未定义，需要使用默认名称
        error_title = getattr(locals(), 'clean_title', f"error_article_{index + 1}")
        screenshot_path = os.path.join(root_dir, "logs", f"{error_title}_error.png") if root_dir else f"{error_title}_error.png"

        # 截图保存当前页面状态，便于后续调试分析
        page.screenshot(path=screenshot_path, full_page=True)

        return False

async def initialize_stagehand() -> Stagehand:
    """
    初始化 Stagehand 配置和浏览器连接

    功能说明：
    1. 加载环境变量配置
    2. 验证必要的 API 密钥
    3. 配置 Stagehand 参数（使用智谱AI模型和本地浏览器）
    4. 初始化 Stagehand 实例并连接到浏览器

    配置详情：
    - 使用本地环境模式
    - 模型：智谱AI GLM-4.6
    - 浏览器：通过 CDP 连接到本地 Chrome 实例（端口9222）

    返回：
        Stagehand: 初始化完成的 Stagehand 实例，可用于网页自动化操作

    异常：
        ValueError: 当缺少必要的环境变量时抛出
    """
    # 加载 .env 文件中的环境变量
    load_dotenv()

    # 从环境变量中获取智谱AI的API密钥
    api_key = os.getenv("zhipu_search_apikey")
    # 智谱AI的API基础URL
    api_base = "https://open.bigmodel.cn/api/paas/v4/"

    # 验证API密钥是否存在，这是程序运行的必要条件
    if not api_key:
        raise ValueError("缺少必要的环境变量: zhipu_search_apikey")

    # 创建输出目录，用于存储抓取的文章文件
    # exist_ok=True 避免目录已存在时报错
    root_dir = os.getenv('root_dir')
    full_path = os.path.join(root_dir, "output/html")
    os.makedirs("output/html", exist_ok=True)

    # 配置 Stagehand 的各种参数
    config = StagehandConfig(
        env="LOCAL",  # 运行环境：本地模式
        model_name="openai/glm-4.6",  # 使用智谱AI的GLM-4.5V模型（支持多模态理解）
        model_api_key=api_key,  # API密钥
        model_api_base=api_base,  # API基础URL
        # 本地浏览器启动选项：通过Chrome DevTools Protocol连接到已启动的Chrome实例
        local_browser_launch_options={"cdp_url": "http://localhost:9222"}
    )

    # 创建 Stagehand 实例
    stagehand = Stagehand(config)

    # 初始化 Stagehand，建立与浏览器的连接
    await stagehand.init()

    # 返回初始化完成的 Stagehand 实例
    return stagehand

async def main():
    """
    程序主函数 - 执行完整的网页爬虫流程

    主要流程：
    1. 初始化 Stagehand 和浏览器连接
    2. 导航到 The Atlantic 最新文章页面
    3. 使用 AI 观察并获取页面上的所有文章链接
    4. 逐个处理每篇文章，提取内容并保存到本地文件
    5. 处理完成后清理资源，关闭浏览器

    异常处理：
    - 键盘中断（Ctrl+C）：优雅地退出程序
    - 其他异常：记录错误信息并清理资源
    - 无论成功失败都会尝试关闭浏览器连接

    资源管理：
    - 使用 try-finally 确保浏览器资源被正确释放
    - 防止僵尸浏览器进程占用系统资源
    """
    # 初始化 stagehand 变量为 None，确保在 finally 块中可以安全检查
    stagehand = None

    try:
        # 在控制台显示程序启动信息
        print("started")
        # 在日志中记录程序启动事件
        logger.info("程序启动")

        # 初始化 Stagehand 实例，建立与浏览器的连接
        stagehand = await initialize_stagehand()
        # 获取页面对象，用于后续的网页操作
        page = stagehand.page

        # 导航到 The Atlantic 网站的最新文章页面
        logging.info("开始新的抓取任务")
        await page.goto("https://www.theatlantic.com/latest", timeout=60000)
        # 等待页面加载完毕并稳定
        await page.wait_for_load_state("domcontentloaded")

        page_content = await page.content()
        logging.info("showing page content")
        logging.info(page_content[:1000] + "...")  # 只记录前1000个字符避免日志过长
        login_flag = await page.observe("find href:My Account")
        logging.info("获取登录状态")
        logging.info(login_flag)
        if not login_flag:
            logger.info("browser not login")
            exit(0)
        logging.info("网站已登录")
        # 使用 Stagehand 的 AI 观察功能，自动识别并获取页面上的文章链接
        # observe 方法会分析页面结构并返回可执行的动作列表
        # Use observe to validate elements before extraction
        results = await page.extract("extract the title and href of the articles of the newest 2 day", schema=EssayUrls)
        logger.info(results)
        # 记录获取到的文章数量，用于监控程序进度
        logger.info(f"获取到 {len(results.list_of_EssayUrl)} 个文章链接")
        
        # 遍历所有文章链接，逐一进行处理
        for i, action in enumerate(results.list_of_EssayUrl):
            # 处理单篇文章，传入页面对象、动作对象和文章索引
            for j in range(3):
                success = await process_single_article(page, action, i)
                if success:
                    break
            # 返回原来的起始页
            await page.goto("https://www.theatlantic.com/latest", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
    except KeyboardInterrupt:
        # 处理用户主动中断程序的情况（如按 Ctrl+C）
        logger.info("用户中断程序")

    except Exception as e:
        # 捕获并处理其他未预期的异常
        logger.error(f"程序执行出错: {e}")

    finally:
        # 无论程序如何结束，都要确保清理浏览器资源
        if stagehand:
            try:
                # 关闭 Stagehand 实例，断开与浏览器的连接
                await stagehand.close()
                # 记录资源清理完成
                logger.info("浏览器已关闭")
            except Exception as e:
                # 如果关闭浏览器过程中出现异常，也要记录错误
                logger.error(f"关闭浏览器失败: {e}")


# =============================================================================
# 程序入口点
# =============================================================================
# 当脚本作为主程序运行时（而不是被导入时），执行主函数
# 使用 asyncio.run() 创建事件循环并运行异步主函数
if __name__ == "__main__":
    asyncio.run(main())