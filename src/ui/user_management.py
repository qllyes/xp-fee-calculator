"""
用户管理模块 - 企业级专业表格设计 (混合布局版)
"""
import streamlit as st
import pandas as pd
import math
import io
from typing import Dict, List


def show_user_management(users_config_path: str) -> None:
    """显示用户管理界面 - 企业级专业表格设计
    
    Args:
        users_config_path: 用户配置文件路径
    """
    from src.core import auth
    from src.core.file_utils import read_excel_safe

    # === 页面样式 ===
    st.markdown("""
        <style>
        /* 页面标题 */
        .user-mgmt-header {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        /* 统计卡片样式 */
        .stat-card {
            background-color: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            text-align: center;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #4f46e5;
        }
        .stat-label {
            font-size: 0.85rem;
            color: #6b7280;
            margin-top: 4px;
        }
        
        /* 表头样式 */
        .table-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 0px;
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        /* 单元格通用样式 - 紧凑版 */
        .cell-content {
            display: flex;
            align-items: center;
            justify-content: center; /* 默认居中 */
            height: 100%;
            font-size: 0.85rem;
            color: #374151;
            padding: 0;
            margin: 0;
            line-height: 1.2;
        }
        
        /* 角色徽章 - 更紧凑 */
        .role-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .role-badge.admin {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            color: #92400e;
        }
        .role-badge.user {
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            color: #1e40af;
        }
        
        /* 用户名样式 */
        .username-cell {
            font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
            color: #4f46e5;
            font-weight: 600;
        }
        
        /* 密码样式 */
        .password-cell {
            font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            background: #fef2f2;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
            color: #991b1b;
            letter-spacing: 1px;
        }
        
        /* 当前用户标记 */
        .current-user-tag {
            display: inline-block;
            padding: 1px 4px;
            background: #ecfdf5;
            color: #065f46;
            border-radius: 3px;
            font-size: 0.65rem;
            font-weight: 500;
            margin-left: 4px;
            border: 1px solid #a7f3d0;
        }
        
        /* 行分隔线 */
        .row-divider {
            border-bottom: 1px solid #e5e7eb;
            margin: 0;
            padding: 0;
        }
        
        /* 极度压缩 Streamlit 列的垂直间距 */
        div[data-testid="column"] {
            display: flex;
            align-items: center;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* 极度压缩整体垂直间距 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* 压缩按钮的所有间距 */
        .stButton {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .stButton > button {
            padding: 0.15rem 0.4rem !important;
            min-height: 24px !important;
            height: 24px !important;
            font-size: 0.75rem !important;
            margin: 0 !important;
        }
        
        /* 进一步压缩按钮容器 */
        div[data-testid="column"] > div > div {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* 工具栏容器样式，确保高度一致 */
        .toolbar-container {
            display: flex;
            align-items: flex-end;
            gap: 10px;
        }
        
        /* 调整搜索框高度 */
        div[data-testid="stTextInput"] input {
            min-height: 42px !important;
            height: 42px !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        /* 调整下载按钮和添加按钮的高度，使其与搜索框一致 */
        div[data-testid="stDownloadButton"] button,
        div[class*="stButton"] button {
            min-height: 42px !important;
            height: 42px !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            line-height: 42px !important;
        }

        /* 针对表格内的操作按钮，恢复小尺寸 */
        div[data-testid="column"] .stButton > button {
            min-height: 24px !important;
            height: 24px !important;
            line-height: 24px !important;
            padding: 0.15rem 0.4rem !important;
        }
        
        </style>
    """, unsafe_allow_html=True)

    # === 页面标题 ===
    st.markdown('<div class="user-mgmt-header"><span>⚙️</span> 用户管理</div>', unsafe_allow_html=True)
    
    if st.button("← 返回主页", type="secondary"):
        st.session_state["show_user_management"] = False
        st.rerun()
    
    st.markdown("---")

    # === 获取用户数据 ===
    users = auth.get_all_users(users_config_path)
    current_username = st.session_state.get("user", {}).get("username", "")
    
    # === 顶部统计仪表盘 ===
    if users:
        total_users = len(users)
        admin_count = sum(1 for u in users if u["role"] == "admin")
        user_count = total_users - admin_count
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{total_users}</div><div class="stat-label">总用户数</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{admin_count}</div><div class="stat-label">管理员</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{user_count}</div><div class="stat-label">普通用户</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

    # === 搜索与工具栏 ===
    col_search, col_export, col_add_btn = st.columns([2.5, 0.8, 0.8], vertical_alignment="bottom")
    
    with col_search:
        search_term = st.text_input("🔍 搜索用户", placeholder="输入用户名或显示名称进行筛选...", label_visibility="collapsed")
    
    # 准备导出数据
    export_df = pd.DataFrame(users)
    export_df = export_df.rename(columns={
        "username": "登录名称",
        "display_name": "用户名称",
        "role": "角色",
        "password": "密码"
    })
    export_cols = ["登录名称", "用户名称", "角色", "密码"]
    for col in export_cols:
        if col not in export_df.columns:
            export_df[col] = ""
    export_df = export_df[export_cols]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        export_df.to_excel(writer, index=False, sheet_name='用户列表')
    excel_data = output.getvalue()

    with col_export:
        st.download_button(
            label="📥 导出名单",
            data=excel_data,
            file_name="用户名单.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col_add_btn:
        if st.button("➕ 添加用户", type="primary", use_container_width=True):
            st.session_state["show_add_user_form"] = not st.session_state.get("show_add_user_form", False)
            st.rerun()

    # === 新增用户表单 (内联显示) ===
    if st.session_state.get("show_add_user_form", False):
        with st.container(border=True):
            st.markdown("#### 📝 新增用户")
            with st.form("add_user_form_inline", clear_on_submit=True):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    new_username = st.text_input("用户名 *", placeholder="请输入用户名")
                    new_display_name = st.text_input("显示名称", placeholder="可选，默认同用户名")
                with col_f2:
                    new_password = st.text_input("密码 *", type="default", placeholder="请输入明文密码")
                    new_role = st.selectbox("角色", ["user", "admin"], 
                                          format_func=lambda x: "🔑 管理员" if x == "admin" else "👤 普通用户")
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.form_submit_button("✅ 确认添加", type="primary", use_container_width=True):
                        if not new_username or not new_password:
                            st.error("用户名和密码不能为空")
                        else:
                            success, msg = auth.add_user(users_config_path, new_username, new_password, 
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

    # === 数据过滤 ===
    filtered_users = users
    if search_term:
        search_lower = search_term.lower()
        filtered_users = [
            u for u in users 
            if search_lower in u["username"].lower() or 
               search_lower in u.get("display_name", "").lower()
        ]

    if not filtered_users:
        st.info("📭 未找到匹配的用户")
    else:
        # === 分页逻辑 ===
        ITEMS_PER_PAGE = 6
        total_items = len(filtered_users)
        total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
        
        if "user_mgmt_page" not in st.session_state:
            st.session_state.user_mgmt_page = 1
        
        if st.session_state.user_mgmt_page > total_pages:
            st.session_state.user_mgmt_page = 1
            
        current_page = st.session_state.user_mgmt_page
        
        start_idx = (current_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        users_to_show = filtered_users[start_idx:end_idx]

        # === 表头 ===
        # 所有表头居中
        st.markdown("""
            <div class="table-header">
                <div style="flex: 1.5; text-align: center;">角色</div>
                <div style="flex: 2; text-align: center;">用户名</div>
                <div style="flex: 2; text-align: center;">显示名称</div>
                <div style="flex: 2.5; text-align: center;">密码</div>
                <div style="flex: 2; text-align: center;">操作</div>
            </div>
        """, unsafe_allow_html=True)
        
        # === 用户列表内容 ===
        for i, user in enumerate(users_to_show):
            global_idx = start_idx + i
            
            role_class = "admin" if user["role"] == "admin" else "user"
            role_icon = "🔑" if user["role"] == "admin" else "👤"
            role_text = "管理员" if user["role"] == "admin" else "普通用户"
            password_display = user.get("password", "******")
            is_current = user["username"] == current_username
            current_tag = '<span class="current-user-tag">当前</span>' if is_current else ""
            
            cols = st.columns([1.5, 2, 2, 2.5, 2])
            
            # 所有单元格内容居中
            with cols[0]:
                st.markdown(f'<div class="cell-content"><span class="role-badge {role_class}">{role_icon} {role_text}</span></div>', unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f'<div class="cell-content"><span class="username-cell">{user["username"]}</span>{current_tag}</div>', unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(f'<div class="cell-content">{user["display_name"]}</div>', unsafe_allow_html=True)
            
            with cols[3]:
                st.markdown(f'<div class="cell-content"><span class="password-cell">{password_display}</span></div>', unsafe_allow_html=True)
            
            with cols[4]:
                if user["username"] != current_username:
                    if st.button("🗑️ 删除", key=f"del_{user['username']}_{global_idx}", 
                               type="secondary", use_container_width=True,
                               help=f"删除用户 {user['username']}"):
                        success, msg = auth.delete_user(users_config_path, user["username"])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.button("当前用户", key=f"cur_{user['username']}_{global_idx}", 
                             disabled=True, use_container_width=True)
            
            # 行分隔线
            st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)

        # === 分页控件 ===
        if total_pages > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            
            with col_prev:
                if st.button("◀ 上一页", disabled=current_page == 1, use_container_width=True):
                    st.session_state.user_mgmt_page -= 1
                    st.rerun()
            
            with col_info:
                st.markdown(f"<div style='text-align: center; line-height: 32px; color: #666;'>第 {current_page} / {total_pages} 页 (共 {total_items} 条)</div>", unsafe_allow_html=True)
            
            with col_next:
                if st.button("下一页 ▶", disabled=current_page == total_pages, use_container_width=True):
                    st.session_state.user_mgmt_page += 1
                    st.rerun()

    # === 批量导入用户 ===
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📂 批量导入用户 (Excel)", expanded=False):
        st.markdown("""
        **说明**：请上传包含以下列的 Excel 文件：
        - `登录名称` (必填): 作为登录账号
        - `用户名称` (选填): 显示名称
        - `角色` (选填): admin 或 user (默认 user)
        - `密码` (选填): 默认使用下方设置的初始密码
        """)
        
        col_imp1, col_imp2 = st.columns(2)
        with col_imp1:
            default_password = st.text_input("初始密码", value="123456", help="如果Excel中未指定密码，将使用此密码")
        
        uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx"])
        
        if uploaded_file and st.button("🚀 开始导入", type="primary"):
            try:
                # 使用 read_excel_safe 读取，并强制所有列为字符串
                df = read_excel_safe(uploaded_file, dtype_spec=str)
                
                # 简单的列名映射检查
                if "登录名称" not in df.columns:
                    st.error("❌ 缺少必要列：`登录名称`")
                else:
                    success_count = 0
                    fail_count = 0
                    fail_reasons = []
                    
                    progress_bar = st.progress(0)
                    total = len(df)
                    
                    for index, row in df.iterrows():
                        # 处理 NaN 值
                        raw_username = row["登录名称"]
                        if pd.isna(raw_username) or str(raw_username).strip() == "":
                            continue
                            
                        username = str(raw_username).strip()
                        
                        raw_display_name = row.get("用户名称", username)
                        display_name = str(raw_display_name).strip() if not pd.isna(raw_display_name) else username
                        
                        raw_role = row.get("角色", "user")
                        role = str(raw_role).strip() if not pd.isna(raw_role) else "user"
                        if role not in ["admin", "user"]: role = "user"
                        
                        raw_password = row.get("密码", default_password)
                        password = str(raw_password).strip() if not pd.isna(raw_password) else default_password
                        
                        # 再次清理可能残留的 .0
                        if username.endswith(".0"): username = username[:-2]
                        if password.endswith(".0"): password = password[:-2]
                        
                        status, msg = auth.add_user(users_config_path, username, password, role, display_name)
                        if status:
                            success_count += 1
                        else:
                            fail_count += 1
                            fail_reasons.append(f"{username}: {msg}")
                        
                        progress_bar.progress((index + 1) / total)
                    
                    st.success(f"导入完成！成功: {success_count}, 失败: {fail_count}")
                    if fail_reasons:
                        with st.expander("查看失败详情"):
                            st.write(fail_reasons)
                    
                    if success_count > 0:
                        # 延迟刷新以显示成功消息
                        import time
                        time.sleep(1)
                        st.rerun()
                        
            except Exception as e:
                st.error(f"读取文件失败: {e}")
