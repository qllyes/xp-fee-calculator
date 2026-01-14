"""用户认证工具模块"""

import hashlib
import json
import os
from typing import Dict, List, Optional, Tuple


def hash_password(password: str) -> str:
    """使用 SHA-256 对密码进行哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码是否匹配"""
    return hash_password(password) == password_hash


def load_users(config_path: str) -> List[Dict]:
    """加载用户列表"""
    if not os.path.exists(config_path):
        return []
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("users", [])


def save_users(config_path: str, users: List[Dict]) -> None:
    """保存用户列表"""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)


def authenticate(config_path: str, username: str, password: str) -> Optional[Dict]:
    """用户认证，返回用户信息（不含密码）或 None"""
    users = load_users(config_path)
    for user in users:
        if user["username"] == username and verify_password(password, user["password_hash"]):
            return {
                "username": user["username"],
                "role": user["role"],
                "display_name": user.get("display_name", username)
            }
    return None


def add_user(config_path: str, username: str, password: str, role: str, display_name: str) -> Tuple[bool, str]:
    """新增用户（管理员功能）"""
    users = load_users(config_path)
    if any(u["username"] == username for u in users):
        return False, "用户名已存在"
    users.append({
        "username": username,
        "password_hash": hash_password(password),
        "role": role,
        "display_name": display_name
    })
    save_users(config_path, users)
    return True, f"用户 {username} 添加成功"


def delete_user(config_path: str, username: str) -> Tuple[bool, str]:
    """删除用户（管理员功能）"""
    users = load_users(config_path)
    original_count = len(users)
    users = [u for u in users if u["username"] != username]
    if len(users) == original_count:
        return False, "用户不存在"
    save_users(config_path, users)
    return True, f"用户 {username} 已删除"


def get_all_users(config_path: str) -> List[Dict]:
    """获取所有用户（管理员功能，不含密码）"""
    users = load_users(config_path)
    return [
        {
            "username": u["username"],
            "role": u["role"],
            "display_name": u.get("display_name", u["username"])
        }
        for u in users
    ]
