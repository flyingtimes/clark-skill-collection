---
name: crawl
description: 这个技能接收用户的需求，抓取theatlantic.com的文章
---

# **crawl**



# 输入
用户给出的文件和需求描述文本


# 功能要求
首先检查运行环境是否就绪
```bash
cd scripts ; uv run check_and_run_uv.py
```
使用下面示例调用处理程序，并获取结果
```bash
cd scripts ; uv run main.py
```
处理程序会执行很长时间，请一直保持等待知道程序执行完毕。务必不要中断程序的执行。