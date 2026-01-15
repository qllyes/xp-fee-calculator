import streamlit as st
import os
import sys
import json
# import time  <-- 移除了不需要的时间控制模块

# --- Path Setup ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

if project_root not in sys.path:
    sys.path.append(project_root)

# Page Config
st.set_page_config(page_title="新品铺货费计算器", page_icon="💰", layout="wide")

# Load Config with Cache
@st.cache_data(show_spinner=False)
def get_config(path):
    from src.core.config_loader import load_config
    return load_config(path)

@st.cache_data(show_spinner=False)
def get_store_master(path):
    from src.core.store_manager import load_store_master
    return load_store_master(path)

@st.cache_data(show_spinner=False)
def get_xp_mapping(path):
    from src.core.store_manager import load_xp_mapping
    return load_xp_mapping(path)

@st.cache_data(show_spinner=False)
def get_region_map(path):
    import pandas as pd  # 延迟导入
    if os.path.exists(path):
        return pd.read_excel(path, engine='openpyxl')
    return None

@st.cache_data(show_spinner=False)
def get_dim_metadata(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# 用户配置路径（登录页面需要）
USERS_CONFIG_PATH = os.path.join(project_root, "config", "users.json")
REMEMBER_ME_FILE = os.path.join(project_root, "config", ".remember_me")

# 持久化工具函数
def load_remembered_user():
    """从文件加载记住的用户信息"""
    try:
        if os.path.exists(REMEMBER_ME_FILE):
            with open(REMEMBER_ME_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("username", ""), data.get("password", "")
    except Exception:
        pass
    return "", ""

def save_remembered_user(username, password):
    """保存用户名和密码到文件"""
    try:
        with open(REMEMBER_ME_FILE, "w", encoding="utf-8") as f:
            json.dump({"username": username, "password": password}, f, ensure_ascii=False)
    except Exception:
        pass

def clear_remembered_user():
    """清除记住的用户信息"""
    try:
        if os.path.exists(REMEMBER_ME_FILE):
            os.remove(REMEMBER_ME_FILE)
    except Exception:
        pass


def show_login_page(container_placeholder) -> bool:
    """显示登录页面"""
    # 【核心修复1】将所有登录页内容渲染到传入的容器中
    with container_placeholder.container():
        
        # 【最终优化】位置移至最顶端
        # 这就是用户打开页面看到的第一个元素（视觉左上角开始）
        # 使用全宽度的淡蓝色 Info Banner，既显眼又专业，且一直保持显示
        st.markdown(
            """
            <div style="
                background-color: #eef4ff; 
                border: 1px solid #cce5ff; 
                border-radius: 4px; 
                padding: 10px 15px; 
                font-size: 0.9rem; 
                color: #004085; 
                margin-bottom: 30px; 
                display: flex;
                align-items: center;
            ">
                <span style="font-size: 1.2rem; margin-right: 8px;">ℹ️</span>
                <span>
                    <b>系统提示</b>：首次加载资源可能需要 5-10 秒，属于正常现象，请耐心等待。
                </span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.markdown("""
            <style>
            header[data-testid="stHeader"] { display: none; }
            footer { display: none; }
            </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            st.markdown('<div style="text-align: center; font-size: 2.5rem; margin: 60px 0 4px 0;">💰</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align: center; font-size: 1.5rem; font-weight: 600; margin-bottom: 20px;">新品铺货费计算器</div>', unsafe_allow_html=True)
            
            with st.container(border=True):
                # 从文件加载记住的用户信息（持久化）
                rem_username, rem_password = load_remembered_user()
                username = st.text_input("👤 用户名", value=rem_username, placeholder="请输入用户名")
                password = st.text_input("🔒 密码", value=rem_password, type="password", placeholder="请输入密码")
                
                # "记住我"选项
                remember_me = st.checkbox("记住我", value=bool(rem_username))
                
                if st.button("登 录", type="primary", use_container_width=True):
                    # 【核心修复2】添加错误捕获
                    try:
                        from src.core import auth

                        if not username or not password:
                            st.error("请输入用户名和密码")
                            return False
                        
                        user = auth.authenticate(USERS_CONFIG_PATH, username, password)
                        if user:
                            # 持久化保存或清除记住的用户信息
                            if remember_me:
                                save_remembered_user(username, password)
                            else:
                                clear_remembered_user()
                            
                            st.session_state["logged_in"] = True
                            st.session_state["user"] = user
                            
                            # 登录成功后，显式清空登录页容器
                            container_placeholder.empty()
                            
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")
                            return False
                    except Exception as e:
                        st.error(f"登录过程发生错误: {str(e)}")
                        st.caption("请联系管理员检查配置文件路径或 src/core/auth.py 是否正常")
                        return False
            
    return False


def show_user_management() -> None:
    """显示用户管理界面 - 使用企业级专业表格设计"""
    from src.ui.user_management import show_user_management as _show_user_mgmt
    _show_user_mgmt(USERS_CONFIG_PATH)

def _show_user_management_old() -> None:
    """显示用户管理界面 - 列表式布局"""
    # 进入此页面时才导入 auth
    from src.core import auth

    st.markdown("### ⚙️ 用户管理")
    if st.button("← 返回主页", type="secondary"):
        st.session_state["show_user_management"] = False
        st.rerun()
    st.divider()
    
    # 用户列表 - 表格式展示
    st.markdown("#### 用户列表")
    users = auth.get_all_users(USERS_CONFIG_PATH)
    
    if not users:
        st.info("暂无用户")
    else:
        # 表头
        header_cols = st.columns([0.8, 1.5, 1.2, 1, 0.8])
        with header_cols[0]:
            st.markdown("**角色**")
        with header_cols[1]:
            st.markdown("**用户名**")
        with header_cols[2]:
            st.markdown("**显示名称**")
        with header_cols[3]:
            st.markdown("**权限**")
        with header_cols[4]:
            st.markdown("**操作**")
        
        st.markdown("---")
        
        # 用户列表内容
        current_user = st.session_state.get("user", {}).get("username", "")
        for user in users:
            row_cols = st.columns([0.8, 1.5, 1.2, 1, 0.8])
            
            with row_cols[0]:
                role_icon = "🔑" if user["role"] == "admin" else "👤"
                st.markdown(role_icon)
            
            with row_cols[1]:
                st.markdown(f"`{user['username']}`")
            
            with row_cols[2]:
                st.markdown(user["display_name"])
            
            with row_cols[3]:
                role_label = "管理员" if user["role"] == "admin" else "普通用户"
                st.markdown(role_label)
            
            with row_cols[4]:
                if user["username"] != current_user:
                    if st.button("🗑️", key=f"del_{user['username']}", help="删除用户"):
                        success, msg = auth.delete_user(USERS_CONFIG_PATH, user["username"])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.caption("当前")
    
    st.markdown("---")
    
    # 新增用户按钮 - 放在列表下方
    if st.button("➕ 添加新用户", type="primary", use_container_width=True):
        st.session_state["show_add_user_form"] = True
        st.rerun()
    
    # 新增用户表单（弹出式）
    if st.session_state.get("show_add_user_form", False):
        with st.container(border=True):
            st.markdown("#### 新增用户")
            with st.form("add_user_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("用户名", placeholder="请输入用户名")
                    new_display_name = st.text_input("显示名称", placeholder="可选，默认同用户名")
                with col2:
                    new_password = st.text_input("密码", type="password", placeholder="请输入密码")
                    new_role = st.selectbox("角色", ["user", "admin"], 
                                          format_func=lambda x: "管理员" if x == "admin" else "普通用户")
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.form_submit_button("✅ 确认添加", type="primary", use_container_width=True):
                        if not new_username or not new_password:
                            st.error("用户名和密码不能为空")
                        else:
                            success, msg = auth.add_user(USERS_CONFIG_PATH, new_username, new_password, 
                                                        new_role, new_display_name or new_username)
                            if success:
                                st.success(msg)
                                st.session_state["show_add_user_form"] = False
                                st.rerun()
                            else:
                                st.error(msg)
                with btn_col2:
                    if st.form_submit_button("❌ 取消", use_container_width=True):
                        st.session_state["show_add_user_form"] = False
                        st.rerun()


def main():
    # 检查登录状态
    if not st.session_state.get("logged_in", False):
        # 【核心修复】创建一个空的容器占位符
        # 登录页面的所有内容都会渲染在这个容器里
        login_holder = st.empty()
        
        # 将占位符传给登录函数
        show_login_page(login_holder)
        return
    
    # 登录后加载配置（仅加载一次）
    # 延迟导入核心库（此时用户已看到界面，加载不会阻塞登录页）
    # 这里的 import 会在用户成功登录并 rerun 后执行
    from src.core.store_manager import load_store_master, calc_auto_counts, extract_manual_counts, load_xp_mapping
    from src.core.calculator import calculate_fee
    from src.core.file_utils import read_excel_safe
    import pandas as pd
    import base64
    from io import BytesIO
    # from datetime import datetime # 如果不需要可以不导入
    
    if "config" not in st.session_state:
        try:
            config_path = os.path.join(project_root, "config", "coefficients.xlsx")
            st.session_state["config"] = get_config(config_path)
        except Exception as e:
            st.error(f"无法加载配置文件: {e}")
            st.stop()
    
    config = st.session_state["config"]
    
    # 获取当前用户角色
    user = st.session_state.get("user", {})
    user_role = user.get("role", "user")
    is_admin = (user_role == "admin")
    
    # 检查是否显示用户管理页面
    if st.session_state.get("show_user_management", False):
        show_user_management()
        return
    
    # --- 优化后的混合布局 CSS ---
    st.markdown("""
        <style>
        /* Popover 菜单样式 - 紧凑版 */
        div[data-testid="stPopoverBody"] {
            padding: 8px 6px !important;
            min-width: 120px !important;
            max-width: 150px !important;
        }

       div[data-testid="stPopoverBody"] button {
            background: transparent !important;
            border: none !important;
            padding: 2px 10px !important;  /* ← 更小的垂直 padding */
            margin: -2px 0 !important;     /* ← 使用负 margin 进一步压缩 */
            font-size: 0.9rem !important;
            width: 100% !important;
            text-align: left !important;
            line-height: 1.1 !important;   /* ← 更紧凑的行高 */
            min-height: 28px !important;   /* ← 限制最小高度 */
        }

        div[data-testid="stPopoverBody"] button:hover {
            background-color: #f0f2f6 !important;
        }

        /* 减少 Popover 内部垂直间距 */
        div[data-testid="stPopoverBody"] > div {
            gap: 0 !important;
        }
        
        /* 1. 顶部留白调整 */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }

        /* 2. 压缩垂直间距 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important;
        }
        
        /* 3. 压缩输入框本身的高度 and 边距 */
        .stNumberInput, .stSelectbox, .stTextInput, .stMultiSelect {
            margin-bottom: -5px !important;
        }
        
        /* 4. 隐藏无关元素 */
        header[data-testid="stHeader"] { display: none; }
        footer { display: none; }

        /* 5. 结果文字大号显示 */
        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
            font-weight: 700 !important;
        }

        /* 让标签居中 */
        div[data-testid="stNumberInput"]:has(input[aria-label="超级旗舰店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="旗舰店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="大店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="中店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="小店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="成长店"]) label[data-testid="stWidgetLabel"] {
            width: 100% !important;
            text-align: center !important;
            justify-content: center !important;
        }
        
        /* 让输入框内的数字居中 */
        div[data-testid="stNumberInput"]:has(input[aria-label="超级旗舰店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="旗舰店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="大店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="中店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="小店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="成长店"]) input {
            text-align: center !important;
        }
        /* 7. 压缩标题 (H2) 的下边距 */
        h2 {
            margin-bottom: 0.2rem !important;
            padding-bottom: 0rem !important;
        }

        /* 8. 向上提拉 Tab 栏，消除默认的大间隙 */
        .stTabs {
            margin-top: -1.5rem !important;
        }

        /* 9. 自定义 secondary 按钮的背景色 */
        button[kind="secondary"] {
            background-color: #F0F2F6 !important;
            border: 1px solid #D1D5DB !important;
            color: #31333F !important;
        }
        
        /* 悬停效果 */
        button[kind="secondary"]:hover {
            background-color: #E6E9EF !important;
            border-color: #B0B5BE !important;
        }

        /* 10. 限制多选框最大高度 */
        .stMultiSelect div[data-baseweb="select"] > div {
            max-height: 46px !important;
            overflow-y: auto !important;
        }
        /* Popover 按钮字体大小 */
        button[data-testid="baseButton-secondary"] {
            font-size: 0.85rem !important;
        }

        </style>
    """, unsafe_allow_html=True)

    # 标题与用户菜单集成在同一行
    title_col, user_col = st.columns([9, 1],vertical_alignment="center")

    with title_col:
        st.markdown("<div style='font-size: 1.8rem; font-weight: 700;'>新品铺货费计算器</div>", unsafe_allow_html=True)

    with user_col:
        user = st.session_state.get("user", {})
        display_name = user.get("display_name", "用户")
        role = user.get("role", "user")
        role_label = "管理员" if role == "admin" else "用户"
        
        with st.popover(f"👤 {display_name}", use_container_width=False):
            if role == "admin":
                if st.button("⚙️ 用户管理", use_container_width=True):
                    st.session_state["show_user_management"] = True
                    st.rerun()
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state["logged_in"] = False
                st.session_state["user"] = None
                st.session_state["show_user_management"] = False
                st.rerun()

    # --- Data Loading (Auto) ---
    store_master_path = os.path.join(project_root, "data", "store_master.xlsx")
    region_map_path = os.path.join(project_root, "data", "region_map.xlsx")
    metadata_path = os.path.join(project_root, "data", "dim_metadata.json")
    
    store_master_df = None
    region_map_df = None
    dim_metadata = None
    update_time = "未知"

    if os.path.exists(store_master_path):
        try:
            store_master_df = get_store_master(store_master_path)
            if "门店表更新时间" in store_master_df.columns:
                update_time = str(store_master_df["门店表更新时间"].iloc[0])
        except Exception as e:
            st.error(f"加载门店数据失败: {e}")
            
    if os.path.exists(region_map_path):
        region_map_df = get_region_map(region_map_path)
        
    if os.path.exists(metadata_path):
        dim_metadata = get_dim_metadata(metadata_path)
        if dim_metadata and "更新时间" in dim_metadata:
            update_time = dim_metadata["更新时间"]
    
    xp_mapping_path = os.path.join(project_root, "data", "处方类别与批文分类表.xlsx")
    xp_map = get_xp_mapping(xp_mapping_path)

    # 显示隐藏式更新时间
    st.markdown(
        f"""
        <div style="
            text-align: right;
            margin-bottom: -28px; 
            position: relative;
            z-index: 999;
            padding-right: 5px;
            top: 2px;
            pointer-events: none;
        ">
            <span style="color: #BDC3C7; font-size: 0.8em;">门店表更新于: {update_time}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Tabs ---
    tab1, tab2 = st.tabs(["🏷️ 单品计算器", "📂 批量计算器"])

    # --- Tab 1: 单品计算器 ---
    with tab1:
        spacer_left, col_center, spacer_right = st.columns([1.5, 7, 1.5])
        
        with col_center:
            with st.container(border=True):
                st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>📝 通道计算器 -- 输入信息</div>", unsafe_allow_html=True)
                
                procurement_type = st.selectbox(
                    "统采or地采", 
                    ["统采", "地采"],
                    index=0,
                )

                c1, c2 = st.columns(2)
                with c1:
                    category = st.selectbox("新品大类", list(config["base_fees"].keys()))       
                with c2:
                    supplier_type = st.selectbox("供应商类型", list(config["supplier_type_coeffs"].keys()))

                # --- 动态布局逻辑开始 ---
                # 1. 准备选项
                all_return_policies = list(config["return_policy_coeffs"].keys()) 
                complex_policies = list(config.get("return_ratio_rules", {}).keys())
                all_return_policies = sorted(list(set(all_return_policies + complex_policies)))
                
                # 2. 预判布局：检查 session_state 或使用默认值
                # 如果这是第一次渲染，st.session_state 还没有这个 key，我们取列表第一个作为默认
                current_policy_val = st.session_state.get("widget_return_policy", all_return_policies[0])
                is_complex_policy = current_policy_val in complex_policies

                # 3. 动态定义列：如果是复杂条件，这行分3列；否则分2列
                if is_complex_policy:
                    # 比例调整：SKU(1) : 退货条件(1.2) : 退货比例(0.8)
                    c3, c4, c4_extra = st.columns([1, 1.2, 0.8])
                else:
                    c3, c4 = st.columns(2)
                    c4_extra = None

                with c3:
                    sku_count = st.number_input("同一供应商单次引进SKU数", min_value=1, value=1)
                
                with c4:
                    # 注意：必须设置 key，以便在 rerun 时能通过 session_state 获取最新值
                    return_policy = st.selectbox("退货条件", all_return_policies, key="widget_return_policy")

                return_ratio_val = 0.0
                if c4_extra:
                    with c4_extra:
                        # 更加简洁的 Label，不需要 st.info 干扰
                        return_ratio_val = st.number_input(
                            "退货比例 (%)", 
                            min_value=0.0, 
                            max_value=100.0, 
                            value=100.0,
                            step=0.1,
                            # 使用 help 替代 info
                            help="请输入比例以匹配折扣档位"
                        )
                # --- 动态布局逻辑结束 ---

                c5, c6 = st.columns(2)
                with c5:
                    cost_price = st.number_input("底价 (元)", min_value=0.0, value=10.0)
                with c6:
                    gross_margin = st.number_input("预估成交综合毛利率 (%)", min_value=0.0, max_value=100.0, value=40.0)               
                c7, c8 = st.columns(2)
                with c7:
                    payment = st.selectbox("付款方式", list(config["payment_coeffs"].keys()))
                with c8:
                    if xp_map:
                        xp_options = sorted(list(xp_map.keys()))
                    else:
                        xp_options = ["无 (未找到映射表)"]
                    selected_xp_category = st.selectbox("处方类别", xp_options)

                target_xp_code = xp_map.get(selected_xp_category) if xp_map else None
                
                st.markdown("""
                            <div style="
                                font-size: 16px; 
                                font-weight: 600; 
                                margin-bottom: 0px; 
                                color: #31333F;
                            ">
                                通道选择
                            </div>
                        """, unsafe_allow_html=True)
                channel_mode = st.radio(
                    "通道模式",
                    ["标准通道", "自定义通道"],
                    label_visibility="collapsed",
                    horizontal=True
                )
                
                channel = "自定义"
                custom_sub_mode = "手动输入"
                manual_counts = {}
                selected_filters = {}
                
                if "标准通道" in channel_mode:
                    color_selection = st.selectbox(
                        "选择标准通道范围",
                        ["全量门店", "小店及以上", "中店及以上", "大店及以上", "旗舰店及以上", "超级旗舰店"],
                        label_visibility="collapsed"
                    )
                    channel = color_selection.split()[-1] 
                else:
                    channel = "自定义"
                    try:
                        custom_sub_mode = st.segmented_control(
                            "自定义输入方式",
                            ["标签筛选", "手动输入"],
                            default="标签筛选",
                            label_visibility="collapsed"
                        )
                    except AttributeError:
                        custom_sub_mode = st.radio(
                            "自定义输入方式:",
                            ["标签筛选", "手动输入"],
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                    
                    if custom_sub_mode == "手动输入":
                        st.caption("请输入各销售规模门店数量:")
                        col_inputs = st.columns(6)
                        with col_inputs[0]: manual_counts["超级旗舰店"] = st.number_input("超级旗舰店", min_value=0, key="custom_super")
                        with col_inputs[1]: manual_counts["旗舰店"] = st.number_input("旗舰店", min_value=0, key="custom_flag")
                        with col_inputs[2]: manual_counts["大店"] = st.number_input("大店", min_value=0, key="custom_big")
                        with col_inputs[3]: manual_counts["中店"] = st.number_input("中店", min_value=0, key="custom_mid")
                        with col_inputs[4]: manual_counts["小店"] = st.number_input("小店", min_value=0, key="custom_small")
                        with col_inputs[5]: manual_counts["成长店"] = st.number_input("成长店", min_value=0, key="custom_grow")
                    else:
                        st.caption("请选择筛选条件 (为空表示全选)")
                        filter_df = region_map_df if region_map_df is not None else store_master_df
                        if filter_df is not None:
                            with st.expander("选择省公司/省份/城市", expanded=True):
                                col_reg1, col_reg2, col_reg3 = st.columns(3)
                                if "filter_company" not in st.session_state: st.session_state["filter_company"] = []
                                if "filter_province" not in st.session_state: st.session_state["filter_province"] = []
                                if "filter_city" not in st.session_state: st.session_state["filter_city"] = []
                                sel_company = st.session_state["filter_company"]
                                sel_province = st.session_state["filter_province"]
                                sel_city = st.session_state["filter_city"]
                                def get_mask(col_name, selected_values):
                                    if not selected_values: return pd.Series(True, index=filter_df.index)
                                    return filter_df[col_name].isin(selected_values)
                                mask_company_cond = get_mask("省公司", sel_company)
                                mask_province_cond = get_mask("省份", sel_province)
                                mask_city_cond = get_mask("城市", sel_city)
                                opts_company = sorted(filter_df[mask_province_cond & mask_city_cond]["省公司"].dropna().unique())
                                opts_province = sorted(filter_df[mask_company_cond & mask_city_cond]["省份"].dropna().unique())
                                opts_city = sorted(filter_df[mask_company_cond & mask_province_cond]["城市"].dropna().unique())
                                def sanitize(current, valid): return [x for x in current if x in valid]
                                st.session_state["filter_company"] = sanitize(st.session_state["filter_company"], opts_company)
                                st.session_state["filter_province"] = sanitize(st.session_state["filter_province"], opts_province)
                                st.session_state["filter_city"] = sanitize(st.session_state["filter_city"], opts_city)
                                with col_reg1: selected_filters["省公司"] = st.multiselect("省公司", options=opts_company, key="filter_company", placeholder="全部 (默认)")
                                with col_reg2: selected_filters["省份"] = st.multiselect("省份", options=opts_province, key="filter_province", placeholder="全部 (默认)")
                                with col_reg3: selected_filters["城市"] = st.multiselect("城市", options=opts_city, key="filter_city", placeholder="全部 (默认)")
                            
                            with st.expander("门店属性筛选", expanded=True):
                                sales_scale_opts = dim_metadata["销售规模"] if dim_metadata else ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
                                selected_filters["销售规模"] = st.multiselect("销售规模", sales_scale_opts, default=[], placeholder="全部 (默认)")
                                col_attr1, col_attr2 = st.columns(2)
                                with col_attr1:
                                    opts = dim_metadata["店龄店型"] if dim_metadata else []
                                    selected_filters["店龄店型"] = st.multiselect("店龄店型", opts, placeholder="全部 (默认)")
                                with col_attr2:
                                    opts = dim_metadata["客流商圈"] if dim_metadata else []
                                    selected_filters["客流商圈"] = st.multiselect("客流商圈", opts, placeholder="全部 (默认)")
                                col_attr3, col_attr4 = st.columns(2)
                                with col_attr3:
                                    opts = dim_metadata["行政区划等级"] if dim_metadata else []
                                    selected_filters["行政区划等级"] = st.multiselect("行政区划等级", opts, placeholder="全部 (默认)")
                                with col_attr4:
                                    opts = dim_metadata["公域O2O店型"] if dim_metadata else []
                                    selected_filters["公域O2O店型"] = st.multiselect("公域O2O店型", opts, placeholder="全部 (默认)")
                                st.markdown("---")
                                col_bool1, col_bool2, col_bool3 = st.columns(3)
                                insurance_opts = ["全部"] + (dim_metadata.get("是否医保店", ["是", "否"]) if dim_metadata else ["是", "否"])
                                o2o_opts = ["全部"] + (dim_metadata.get("是否O2O门店", ["是", "否"]) if dim_metadata else ["是", "否"])
                                coor_opts = ["全部"] + (dim_metadata.get("是否统筹店", ["是", "否"]) if dim_metadata else ["是", "否"])
                                with col_bool1: selected_filters["是否医保店"] = st.selectbox("是否医保店", insurance_opts)
                                with col_bool2: selected_filters["是否O2O门店"] = st.selectbox("是否O2O门店", o2o_opts)
                                with col_bool3: selected_filters["是否统筹店"] = st.selectbox("是否统筹店", coor_opts)

                st.markdown("""
                            <div style="
                                font-size: 16px; 
                                font-weight: 400; 
                                margin-bottom: 5px; 
                                margin-top: 10px;
                                color: #31333F;
                            ">
                                战区选择(如果选中一个战区，只会计算该战区中的门店)
                            </div>
                        """, unsafe_allow_html=True)
                
                war_zone_options = config.get("war_zones", ["全集团"])
                selected_war_zone = st.selectbox("选择战区", war_zone_options, label_visibility="collapsed")

            if st.button("开始计算", type="primary", use_container_width=True):
                needs_master_data = (channel != "自定义") or (custom_sub_mode == "标签筛选")
                
                if needs_master_data and store_master_df is None:
                    st.error("❌ 未找到门店主数据，无法进行自动计算！")
                else:
                    row_data = {
                        "新品大类": category,
                        "统采or地采": procurement_type,
                        "处方类别": selected_xp_category,
                        "同一供应商单次引进SKU数": sku_count,
                        "channel": channel,
                        "预估毛利率(%)": gross_margin,
                        "付款方式": payment,
                        "供应商类型": supplier_type,
                        "底价": cost_price,
                        "退货条件": return_policy,
                        "退货比例(%)": return_ratio_val # [新增] 传入比例
                    }
                    if channel == "自定义" and custom_sub_mode == "手动输入":
                        for k, v in manual_counts.items():
                            row_data[f"(自定义){k}数"] = v

                    try:
                        store_counts = {}
                        excluded_count = 0
                        is_auto_calc_mode = False

                        if channel == "自定义" and custom_sub_mode == "手动输入":
                            store_counts = extract_manual_counts(row_data)
                        elif channel == "自定义" and custom_sub_mode == "标签筛选":
                            is_auto_calc_mode = True
                            store_counts = calc_auto_counts(
                                store_master_df, 
                                channel, 
                                restricted_xp_code=target_xp_code,
                                war_zone=selected_war_zone,
                                filters=selected_filters
                            )
                            if target_xp_code:
                                raw_counts = calc_auto_counts(
                                    store_master_df, 
                                    channel, 
                                    restricted_xp_code=None,
                                    war_zone=selected_war_zone,
                                    filters=selected_filters
                                )
                                excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                        else:
                            is_auto_calc_mode = True
                            store_counts = calc_auto_counts(
                                store_master_df, 
                                channel, 
                                restricted_xp_code=target_xp_code,
                                war_zone=selected_war_zone
                            )
                            if target_xp_code:
                                raw_counts = calc_auto_counts(
                                    store_master_df, 
                                    channel, 
                                    restricted_xp_code=None,
                                    war_zone=selected_war_zone
                                )
                                excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                        
                        result = calculate_fee(row_data, store_counts, config)

                        with st.container(border=True):
                            st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>🧾 通道计算器 -- 输出信息</div>", unsafe_allow_html=True)
                            css_style = """
                            <style>
                                .metric-box { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 10px; }
                                .metric-label { font-size: 0.9rem; color: #666; margin-bottom: 5px; }
                                .metric-value { font-size: 1.8rem; font-weight: 700; }
                            </style>
                            """
                            st.markdown(css_style, unsafe_allow_html=True)
                            col_res1, col_res2, col_res3 = st.columns([1, 1, 1.2]) 
                            with col_res1:
                                st.markdown(f"""<div class="metric-box"><div class="metric-label">理论总新品铺货费(元)</div><div class="metric-value" style="color: #333;">{int(result['theoretical_fee']):,}</div></div>""", unsafe_allow_html=True)
                            with col_res2:
                                st.markdown(f"""<div class="metric-box"><div class="metric-label">折扣</div><div class="metric-value" style="color: #333;">{result['discount_factor']:.2f}</div></div>""", unsafe_allow_html=True)
                            with col_res3:
                                st.markdown(f"""<div class="metric-box"><div class="metric-label">折后总新品铺货费(元)</div><div class="metric-value" style="color: #D32F2F; ">{int(result['final_fee']):,}</div></div>""", unsafe_allow_html=True)
                            if result.get('is_floor_triggered'):
                                procurement = result.get('procurement_type', '未知标准')
                                st.caption(f"⚠️ 已触发最低兜底费用 ({procurement}): {result['min_floor']}元")
                            st.divider()
                            
                            # 仅管理员可见：计算过程详情
                            if is_admin:
                                with st.expander("👁️ 查看计算过程详情", expanded=False):
                                    col_detail_2, col_detail_1 = st.columns(2)
                                    with col_detail_1:
                                        st.markdown("📉 计算系数")
                                        coeffs_data = {
                                            "项目": [name for name, _ in result['coefficients']],
                                            "系数": [val for _, val in result['coefficients']]
                                        }
                                        st.dataframe(pd.DataFrame(coeffs_data), use_container_width=True, hide_index=True)
                                    with col_detail_2:
                                        st.markdown("🏬 门店分布")
                                        store_order = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
                                        store_data = {"销售规模": store_order, "门店数": [result['store_details'].get(t, 0) for t in store_order]}
                                        st.dataframe(pd.DataFrame(store_data), use_container_width=True, hide_index=True)
                                    total_stores = sum(result['store_details'].values())
                                    footer_text = f"计算池中的门店数量: {total_stores:,}"
                                    if is_auto_calc_mode and target_xp_code: footer_text += f" | 剔除受限门店数: {excluded_count}"
                                    st.caption(footer_text)
                            
                            # 仅管理员可见：规则说明
                            if is_admin:
                                with st.expander("规则说明"):
                                    rule_pdf_path = os.path.join(project_root, "data", "rule_description.pdf")
                                    if os.path.exists(rule_pdf_path):
                                        with open(rule_pdf_path, "rb") as f:
                                            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                                        st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>', unsafe_allow_html=True)
                                    else:
                                        st.info("暂无规则说明文档")
                    except Exception as e:
                        st.error(f"计算出错: {e}")

    # --- Tab 2: 批量计算器 ---
    with tab2:
        st.markdown("<p style='color: gray; font-size: 0.95em; margin-top: -10px; margin-bottom: 20px;'>快速为多款新品一次性计算铺货费用</p>", unsafe_allow_html=True)
        with st.expander("📥 需要导入模板？点这里下载", expanded=True):
            template_path = os.path.join(project_root, "data", "batch_template.xlsx")
            if os.path.exists(template_path):
                with open(template_path, "rb") as f:
                    st.download_button("下载导入模板", f, file_name="新品铺货费_批量导入模板.xlsx", use_container_width=True, type="secondary")
            else:
                st.warning("未找到模板文件")
        st.markdown("---")
        uploaded_batch = st.file_uploader("上传批量Excel文件", type=["xlsx"])
        if "batch_last_file_id" not in st.session_state: st.session_state.batch_last_file_id = None
        if "batch_results_df" not in st.session_state: st.session_state.batch_results_df = None

        if uploaded_batch:
            current_file_id = uploaded_batch.file_id
            if current_file_id != st.session_state.batch_last_file_id:
                st.session_state.batch_results_df = None
                st.session_state.batch_last_file_id = current_file_id

            if st.button("开始批量计算", type="primary", use_container_width=True):
                if store_master_df is None:
                    st.error("❌ 未找到门店主数据，请检查 data/store_master.xlsx 文件！")
                else:
                    try:
                        df = read_excel_safe(uploaded_batch)
                        # [新增] 检查是否存在 '退货比例(%)' 列，如果不存在则警告或默认0
                        if '退货比例(%)' not in df.columns:
                            st.warning("⚠️ 提示：上传的Excel中缺少【退货比例(%)】列。如果是效期可退类商品，将默认按 100% 处理。建议下载最新模板。")
                        
                        with st.spinner("正在批量计算..."):
                            results = []
                            progress_bar = st.progress(0)
                            
                            for index, row in df.iterrows():
                                row_dict = row.to_dict()
                                try:
                                    p_type = row_dict.get('统采or地采')
                                    if pd.isna(p_type) or str(p_type).strip() == "":
                                        row_dict['统采or地采'] = "统采"
                                    else:
                                        row_dict['统采or地采'] = str(p_type).strip()

                                    channel_name = row_dict.get('铺货通道')
                                    batch_xp_cat = row_dict.get('处方类别')
                                    batch_target_code = xp_map.get(str(batch_xp_cat).strip()) if (batch_xp_cat and xp_map) else None
                                    
                                    batch_war_zone = row_dict.get('提报战区')
                                    if pd.isna(batch_war_zone) or str(batch_war_zone).strip() == "" or str(batch_war_zone).strip() == "全集团":
                                        batch_war_zone = "全集团"
                                    else:
                                        batch_war_zone = str(batch_war_zone).strip()

                                    # [新增] 清洗退货比例
                                    ratio_val = row_dict.get('退货比例(%)', 100)
                                    if pd.isna(ratio_val): ratio_val = 100
                                    row_dict['退货比例(%)'] = float(ratio_val)

                                    excluded_count = 0
                                    if channel_name == "自定义":
                                        store_counts = extract_manual_counts(row_dict)
                                    else:
                                        store_counts = calc_auto_counts(
                                            store_master_df, 
                                            channel_name, 
                                            restricted_xp_code=batch_target_code,
                                            war_zone=batch_war_zone
                                        )
                                        if batch_target_code:
                                            raw_counts = calc_auto_counts(
                                                store_master_df, 
                                                channel_name, 
                                                restricted_xp_code=None,
                                                war_zone=batch_war_zone
                                            )
                                            excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                                    
                                    result = calculate_fee(row_dict, store_counts, config)
                                    
                                    row_dict['理论总新品铺货费 (元)'] = int(result['theoretical_fee'])
                                    row_dict['折扣'] = result['discount_factor']
                                    row_dict['折后总新品铺货费 (元)'] = int(result['final_fee'])
                                    active_stores = {k: v for k, v in result['store_details'].items() if v > 0}
                                    row_dict['[详情]门店分布'] = str(active_stores)
                                    coeffs_dict = {item[0]: item[1] for item in result['coefficients']}
                                    row_dict['[详情]计算系数'] = str(coeffs_dict)
                                    if batch_target_code and excluded_count > 0:
                                        row_dict['备注'] = f"已剔除受限门店数：{excluded_count}"
                                    elif batch_target_code:
                                        row_dict['备注'] = "无受限门店剔除"
                                    else:
                                        row_dict['备注'] = ""
                                    results.append(row_dict)
                                except Exception as e:
                                    row_dict['备注'] = f"Error: {e}"
                                    results.append(row_dict)
                                progress_bar.progress((index + 1) / len(df))
                            
                            result_df = pd.DataFrame(results)
                            st.success("批量计算完成！")
                            st.session_state.batch_results_df = result_df
                    except Exception as e:
                        st.error(f"处理文件失败: {e}")
            
            if st.session_state.batch_results_df is not None:
                display_df = st.session_state.batch_results_df
                
                # 准备导出数据：普通用户排除详情字段
                export_df = display_df.copy()
                if not is_admin:
                    # 排除最后三个详情字段
                    columns_to_exclude = ['[详情]门店分布', '[详情]计算系数', '备注']
                    export_df = export_df.drop(columns=[col for col in columns_to_exclude if col in export_df.columns])
                
                # 显示预览（根据角色过滤）
                st.dataframe(export_df.head())
                
                # 导出（根据角色过滤）
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    export_df.to_excel(writer, index=False)
                st.download_button(
                    "导出结果", 
                    output.getvalue(), 
                    file_name="新品费批量计算结果.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()