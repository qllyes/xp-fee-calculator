"""
用户管理模块 - 企业级专业表格设计 (混合布局版)
"""
import streamlit as st
from typing import Dict, List


def show_user_management(users_config_path: str) -> None:
    """显示用户管理界面 - 企业级专业表格设计
    
    Args:
        users_config_path: 用户配置文件路径
    """
    from src.core import auth

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
        
        /* 表头样式 */
        .table-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 10px;
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
        }
        
        /* 行样式 */
        .table-row {
            padding: 0px 0;
            border-bottom: 0px solid #e5e7eb;
            transition: background-color 0.2s;
        }
        .table-row:hover {
            background-color: #f9fafb;
        }
        
        /* 单元格通用样式 */
        .cell-content {
            display: flex;
            align-items: center;
            height: 100%;
            font-size: 0.9rem;
            color: #374151;
        }
        
        /* 角色徽章 */
        .role-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
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
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
            color: #4f46e5;
            font-weight: 600;
        }
        
        /* 密码样式 */
        .password-cell {
            font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            background: #fef2f2;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
            color: #991b1b;
            letter-spacing: 1px;
        }
        
        /* 当前用户标记 */
        .current-user-tag {
            display: inline-block;
            padding: 2px 6px;
            background: #ecfdf5;
            color: #065f46;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 500;
            margin-left: 6px;
            border: 1px solid #a7f3d0;
        }
        
        /* 压缩 Streamlit 列的垂直间距 */
        div[data-testid="column"] {
            display: flex;
            align-items: center;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        
        /* 压缩整体垂直间距 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.3rem !important;
        }
        
        /* 压缩按钮的所有间距 */
        .stButton {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .stButton > button {
            padding: 0.2rem 0.5rem !important;
            min-height: 28px !important;
            height: 28px !important;
            font-size: 0.8rem !important;
            margin: 0 !important;
        }
        
        /* 进一步压缩按钮容器 */
        div[data-testid="column"] > div > div {
            margin: 0 !important;
            padding: 0 !important;
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
    
    if not users:
        st.info("📭 暂无用户数据")
    else:
        # === 表头 ===
        # 使用自定义 HTML 渲染表头背景
        st.markdown("""
            <div class="table-header">
                <div style="width: 15%;">角色</div>
                <div style="width: 20%;">用户名</div>
                <div style="width: 20%;">显示名称</div>
                <div style="width: 25%;">密码</div>
                <div style="width: 20%; text-align: center;">操作</div>
            </div>
        """, unsafe_allow_html=True)
        
        # === 用户列表内容 ===
        # 使用 Streamlit 列布局来模拟表格行，以便嵌入按钮
        for i, user in enumerate(users):
            role_class = "admin" if user["role"] == "admin" else "user"
            role_icon = "🔑" if user["role"] == "admin" else "👤"
            role_text = "管理员" if user["role"] == "admin" else "普通用户"
            password_display = user.get("password", "******")
            is_current = user["username"] == current_username
            current_tag = '<span class="current-user-tag">当前</span>' if is_current else ""
            
            # 定义列宽比例，需与表头视觉一致
            # 注意：Streamlit 的 columns 比例是相对的，这里尽量凑出视觉上的对齐
            # 表头比例: 15, 20, 20, 25, 20
            cols = st.columns([1.5, 2, 2, 2.5, 2])
            
            with cols[0]:
                st.markdown(f'<div class="cell-content"><span class="role-badge {role_class}">{role_icon} {role_text}</span></div>', unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f'<div class="cell-content"><span class="username-cell">{user["username"]}</span>{current_tag}</div>', unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(f'<div class="cell-content">{user["display_name"]}</div>', unsafe_allow_html=True)
            
            with cols[3]:
                st.markdown(f'<div class="cell-content"><span class="password-cell">{password_display}</span></div>', unsafe_allow_html=True)
            
            with cols[4]:
                # 操作列：嵌入按钮
                if user["username"] != current_username:
                    if st.button("🗑️ 删除", key=f"del_{user['username']}_{i}", 
                               type="secondary", use_container_width=True,
                               help=f"删除用户 {user['username']}"):
                        success, msg = auth.delete_user(users_config_path, user["username"])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    # 同样使用按钮（禁用），保持行高一致
                    st.button("当前用户", key=f"cur_{user['username']}_{i}", 
                             disabled=True, use_container_width=True)
            
            # 行分隔线（紧凑）
            st.markdown('<div style="border-bottom: 0px solid #e5e7eb; margin: 0px 0;"></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # === 新增用户按钮 ===
    if st.button("➕ 添加新用户", type="primary", use_container_width=True):
        st.session_state["show_add_user_form"] = True
        st.rerun()
    
    # === 新增用户表单 ===
    if st.session_state.get("show_add_user_form", False):
        st.markdown("---")
        with st.container(border=True):
            st.markdown("#### 📝 新增用户")
            with st.form("add_user_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("用户名 *", placeholder="请输入用户名")
                    new_display_name = st.text_input("显示名称", placeholder="可选，默认同用户名")
                with col2:
                    new_password = st.text_input("密码 *", type="default", placeholder="请输入明文密码") # type="default" 显示明文
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
