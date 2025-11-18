import asyncio
import os
import re
import sys
import logging

# 设置UTF-8编码
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

from dotenv import load_dotenv
from stagehand import Stagehand, StagehandConfig
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EssayInfo(BaseModel):
    title: str = Field(..., description="标题")
    subtitle: str = Field(..., description="副标题")
    content: str = Field(..., description="正文内容，请注意不要包含广告的内容")
    author: str = Field(..., description="作者")

def sanitize_filename(title: str, index: int) -> str:
    """清理标题使其能作为文件名"""
    clean_title = re.sub(r'[<>:"/\\|?*]', '', title)
    clean_title = re.sub(r'[^\w\s-]', '', clean_title)
    clean_title = re.sub(r'\s+', '_', clean_title.strip())
    clean_title = clean_title[:100]
    return clean_title or f"article_{index + 1}"

def save_article(content: str, filename: str) -> bool:
    """保存文章到文件"""
    root_dir = os.getenv("root_dir")
    # 拼接root_dir和filename为最终路径名
    full_path = os.path.join(root_dir, filename) if root_dir else filename
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"文章已保存到: {full_path}")
        return True
    except Exception as e:
        logger.error(f"文件写入失败: {e}")
        return False

async def safe_navigate_back(page):
    """安全地返回上一页或重新导航"""
    try:
        await page.go_back()
        logger.info("成功返回上一页")
    except Exception:
        try:
            await page.goto("https://www.theatlantic.com/latest")
            logger.info("重新导航到主页")
        except Exception as e:
            logger.error(f"重新导航失败: {e}")

async def process_single_article(page, action, index: int) -> bool:
    """处理单篇文章"""
    try:
        logger.info(f"处理第 {index + 1} 篇文章: {action.description}")
        print(action.description)

        await page.act(action)
        await page.wait_for_load_state("domcontentloaded")

        try:
            result = await page.extract(
                "提取文章的标题、副标题、作者名字、正文内容，请注意不要包含广告内容",
                schema=EssayInfo
            )
        except Exception as e:
            logger.error(f"文章内容提取失败: {e}")
            await safe_navigate_back(page)
            return False

        print("=" * 20)
        print(result)
        print("=" * 20)

        clean_title = sanitize_filename(result.title, index)
        filename = f"output/{clean_title}.txt"
        save_article(result.content, filename)
        print(f"文章已保存到: {filename}")

        await safe_navigate_back(page)
        return True

    except Exception as e:
        logger.error(f"处理第 {index + 1} 篇文章时发生错误: {e}")
        await safe_navigate_back(page)
        return False

async def initialize_stagehand() -> Stagehand:
    """初始化Stagehand配置和连接"""
    load_dotenv()

    api_key = os.getenv("zhipu_search_apikey")
    api_base = "https://open.bigmodel.cn/api/paas/v4/"
    if not api_key:
        raise ValueError("缺少必要的环境变量: zhipu_search_apikey")

    os.makedirs("output", exist_ok=True)

    config = StagehandConfig(
        env="LOCAL",
        model_name="openai/glm-4.5v",
        model_api_key=api_key,
        model_api_base=api_base,
        local_browser_launch_options={"cdp_url": "http://localhost:9222"}
    )

    stagehand = Stagehand(config)
    await stagehand.init()
    return stagehand

async def main():
    stagehand = None
    try:
        print("started")
        logger.info("程序启动")

        stagehand = await initialize_stagehand()
        page = stagehand.page

        await page.goto("https://www.theatlantic.com/latest")
        actions = await page.observe("获取最近一天的所有文章标题和链接")

        logger.info(f"获取到 {len(actions)} 个文章链接")

        for i, action in enumerate(actions):
            success = await process_single_article(page, action, i)
            if not success:
                logger.warning(f"第 {i + 1} 篇文章处理失败，继续处理下一篇")

    except KeyboardInterrupt:
        logger.info("用户中断程序")
        print("\n用户中断程序")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        print(f"程序执行出错: {e}")
    finally:
        if stagehand:
            try:
                print("\n🔚 关闭浏览器...")
                await stagehand.close()
                logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())