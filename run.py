"""
启动脚本：同时启动 Streamlit + ngrok 公网隧道
手机在任何地方都能访问，不需要同一 WiFi。

首次使用：
  1. 浏览器打开 https://dashboard.ngrok.com/signup
  2. 免费注册账号
  3. 复制你的 authtoken
  4. 运行：python run.py --token <你的authtoken>

之后直接运行：
  python run.py
"""

import subprocess
import sys
import os
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

TOKEN_FILE = ".ngrok_token"


def save_token(token: str):
    with open(TOKEN_FILE, "w") as f:
        f.write(token.strip())
    print(f"✅ Token 已保存")


def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return None


def main():
    # 处理命令行参数
    if "--token" in sys.argv:
        idx = sys.argv.index("--token")
        token = sys.argv[idx + 1]
        save_token(token)
        # 配置到 pyngrok
        from pyngrok import ngrok, conf
        conf.get_default().auth_token = token
        print("✅ ngrok 已配置")
    else:
        token = load_token()
        if token:
            from pyngrok import ngrok, conf
            conf.get_default().auth_token = token

    # 检查是否已配置
    token = load_token()
    if not token:
        print("=" * 55)
        print("  ⚠️  首次使用需要配置 ngrok（免费）")
        print("=" * 55)
        print()
        print("  1. 浏览器打开: https://dashboard.ngrok.com/signup")
        print("  2. 注册免费账号")
        print("  3. 复制你的 authtoken")
        print("  4. 运行: python run.py --token <你的token>")
        print()
        print("=" * 55)
        print()
        ans = input("没有 token 只在局域网可用，是否继续？[Y/n]: ")
        if ans.lower() == "n":
            sys.exit(0)

    # 启动 Streamlit（ngrok 由 app.py 内部自动启动）
    print()
    print("🚀 启动中...")
    print()
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8501",
        "--server.headless", "true",
    ])


if __name__ == "__main__":
    main()
