# =============================================================================
# 网页爬虫程序 - 抓取 The Atlantic 网站文章
# =============================================================================
# 该程序使用 Stagehand 库（基于 Playwright）来自动化浏览器操作，
# 访问 The Atlantic 网站的最新文章页面，获取文章列表并逐个抓取完整内容
# =============================================================================

import asyncio          # 异步编程库，用于处理异步I/O操作，提高程序并发性能
import os              # 操作系统接口，用于文件路径处理、环境变量获取等
import re              # 正则表达式库，用于字符串模式匹配和文本清理
import sys             # 系统相关参数和函数，用于处理系统级别的操作
import logging         # 日志记录库，用于记录程序运行过程中的各种信息

# =============================================================================
# Windows 平台 UTF-8 编码设置
# =============================================================================
# 解决 Windows 系统下控制台输出中文乱码的问题
# 将标准输出和错误输出流重新编码为 UTF-8 格式
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# 第三方库导入
from dotenv import load_dotenv    # 环境变量管理库，从 .env 文件加载环境变量
from stagehand import Stagehand, StagehandConfig  # Stagehand 网页自动化库
from pydantic import BaseModel, Field  # 数据验证和设置管理库

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
    文章信息数据模型

    使用 Pydantic BaseModel 定义文章的数据结构，
    用于数据验证和结构化存储从网页提取的文章信息
    """
    title: str = Field(..., description="文章标题")  # 必填字段，存储文章主标题
    subtitle: str = Field(..., description="文章副标题")  # 必填字段，存储文章副标题或摘要
    content: str = Field(..., description="正文内容，请注意不要包含广告的内容")  # 必填字段，存储完整的文章正文内容，排除广告等无关内容
    author: str = Field(..., description="作者")  # 必填字段，存储文章作者姓名

def sanitize_filename(title: str, index: int) -> str:
    """
    将文章标题清理为合法的文件名

    处理步骤：
    1. 移除 Windows 系统不允许的文件名字符：< > : " / \ | ? *
    2. 移除除字母、数字、空格和连字符以外的特殊字符
    3. 将连续的空格替换为单个下划线
    4. 限制文件名长度为100个字符
    5. 如果清理后标题为空，使用默认名称

    参数：
        title (str): 原始文章标题
        index (int): 文章索引，用于生成默认文件名

    返回：
        str: 清理后可作为文件名的字符串
    """
    # 移除 Windows 系统文件名中不允许的字符
    clean_title = re.sub(r'[<>:"/\\|?*]', '', title)

    # 移除除字母、数字、空格和连字符以外的所有特殊字符
    # \w 匹配字母、数字和下划线，\s 匹配空白字符
    clean_title = re.sub(r'[^\w\s-]', '', clean_title)

    # 将连续的空白字符（空格、制表符、换行符等）替换为单个下划线
    # 并去除首尾空白字符
    clean_title = re.sub(r'\s+', '_', clean_title.strip())

    # 限制文件名长度，防止因标题过长导致文件系统问题
    clean_title = clean_title[:100]

    # 如果清理后标题为空，使用默认名称 "article_序号"
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
        logger.info(f"处理第 {index + 1} 篇文章: {action.description}")
        logger.info(action)  # 记录完整的动作对象信息，便于调试

        # 执行点击操作，导航到文章页面
        await page.act(action)

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

        # 将文章标题转换为合法的文件名
        clean_title = sanitize_filename(action.description, index)

        # 构建输出文件路径，保存在 output 目录下
        filename = f"output/{clean_title}.txt"

        # 保存文章正文内容到文件
        save_article(result.content, filename)

        # 在控制台显示保存结果，提供用户反馈
        print(f"文章已保存到: {filename}")

        return True

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
    - 模型：智谱AI GLM-4.5V（支持视觉理解）
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
    os.makedirs("output", exist_ok=True)

    # 配置 Stagehand 的各种参数
    config = StagehandConfig(
        env="LOCAL",  # 运行环境：本地模式
        model_name="openai/glm-4.5v",  # 使用智谱AI的GLM-4.5V模型（支持多模态理解）
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
        await page.goto("https://www.theatlantic.com/latest")
        # 等待页面加载完毕
        await page.wait_for_load_state("domcontentloaded")
        page_content = await page.content()
        logging.info("showing page content")
        logging.info(page_content)
        login_flag = await page.observe("find href:My Account")
        logging.info("获取登录状态")
        logging.info(login_flag)
        if not login_flag:
            logger.info("browser not login")
            exit(0)
        logging.info("网站已登录")
        # 使用 Stagehand 的 AI 观察功能，自动识别并获取页面上的文章链接
        # observe 方法会分析页面结构并返回可执行的动作列表
        actions = await page.observe("获取最近一天的所有文章标题和链接")

        # 记录获取到的文章数量，用于监控程序进度
        logger.info(f"获取到 {len(actions)} 个文章链接")
        logger.info(actions)
        # 遍历所有文章链接，逐一进行处理
        for i, action in enumerate(actions):
            # 处理单篇文章，传入页面对象、动作对象和文章索引
            success = await process_single_article(page, action, i)

            # 如果文章处理失败，记录警告但继续处理下一篇文章
            # 这种容错设计确保单篇文章的失败不会影响整体任务
            if not success:
                logger.warning(f"第 {i + 1} 篇文章处理失败，继续处理下一篇")
            # 返回原来的起始页
            await page.goto("https://www.theatlantic.com/latest")
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