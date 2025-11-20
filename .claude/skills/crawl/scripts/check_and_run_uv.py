import os
import subprocess
import sys
import socket
from dotenv import load_dotenv

def is_port_open(port):
    """检查端口是否开启"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
    except:
        return False


def get_userdata_dir():
    """从.env文件读取root_dir并构建userdata目录路径"""
    load_dotenv()
    root_dir = os.getenv('root_dir')
    if not root_dir:
        raise ValueError("在.env文件中未找到root_dir配置")

    userdata_dir = os.path.join(root_dir, 'userdata')
    # 确保目录存在
    os.makedirs(userdata_dir, exist_ok=True)
    return userdata_dir


def start_chrome_debug():
    """启动Chrome远程调试"""
    userdata_dir = get_userdata_dir()
    if os.name == "nt":  # Windows环境
        chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        chrome_cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--proxy-server=http://127.0.0.1:1087",
            f"--user-data-dir={userdata_dir}",
            "--headless=new"
        ]
    else:  # Mac环境
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        chrome_cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={userdata_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--proxy-server=http://127.0.0.1:1087",
            "--start-maximized",
            #"--headless=new"
        ]

    try:
        print(f"正在启动Chrome调试模式...")
        print(chrome_cmd)
        print(f"用户数据目录: {userdata_dir}")

        # 使用后台方式启动Chrome，避免阻塞
        subprocess.Popen(chrome_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True)

        # 等待一段时间让Chrome启动
        import time
        time.sleep(5)

        print("Chrome调试模式已启动")
        return True

    except Exception as e:
        print(f"启动Chrome失败: {e}", file=sys.stderr)
        return False


def check_chrome_debug():
    """检查9222端口并启动Chrome调试"""
    port = 9222

    while not is_port_open(port):
        print(f"端口 {port} 未开启，正在启动Chrome...")
        start_chrome_debug()


def run_uv_sync():
    """执行 uv sync 并实时输出日志"""
    print("正在执行 uv sync...\n")

    process = subprocess.Popen(
        ["uv", "sync"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        print(line, end='')

    process.wait()

    if process.returncode == 0:
        print("\nuv sync 完成！")
    else:
        print("\nuv sync 执行失败！", file=sys.stderr)


def main():
    venv_dir = ".venv"

    # 判断系统类型
    if os.name == "nt":
        print("当前系统：Windows")
    else:
        print(f"当前系统：{os.uname().sysname}")

    # 检查Chrome调试端口
    print("\n检查Chrome调试环境...")
    check_chrome_debug()

    # 判断 .venv 是否存在
    print("\n检查Python虚拟环境...")
    if not os.path.isdir(venv_dir):
        print(".venv 不存在~")
        run_uv_sync()
    else:
        print(".venv 已存在，跳过 uv sync")


if __name__ == "__main__":
    main()
