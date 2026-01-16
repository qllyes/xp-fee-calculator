import sys
import os
from streamlit.web import cli as stcli

def main():
    """
    项目统一入口脚本 (Launcher)
    
    使用方法:
    1. 命令行运行: python main.py
    2. 使用 uv: uv run python main.py
    
    注意: 不要使用 'streamlit run main.py' 来运行此脚本，
    因为它通过代码内部调用启动 streamlit，会导致递归调用。
    """
    # 1. 获取当前脚本（根目录）的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 定位实际的 Streamlit 应用文件
    app_path = os.path.join(current_dir, "src", "ui", "app.py")
    
    if not os.path.exists(app_path):
        print(f"Error: 找不到应用文件: {app_path}")
        sys.exit(1)

    # 3. 构造启动参数
    # 这里的 sys.argv 模拟了命令行参数：streamlit run src/ui/app.py [user_args...]
    # sys.argv[1:] 保留了用户调用 python main.py 时传入的额外参数
    sys.argv = ["streamlit", "run", app_path] + sys.argv[1:]
    
    # 4. 启动 Streamlit
    print(f"🚀 正在启动新品铺货费计算器...\n入口文件: {app_path}\n")
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
