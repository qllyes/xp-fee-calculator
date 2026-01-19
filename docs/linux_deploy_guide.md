# Linux Crontab 定时更新配置指南

本指南用于在 Linux 服务器上配置定时任务，以实现 `xp-fee-calculator` 各项配置表（门店数据、映射表等）的自动更新。

## 1. 前置准备

### 1.1 确认脚本路径
请先确认项目在服务器上的根目录，假设项目路径为：
`/opt/xinpin/xp-fee-calculator`

### 1.2 确认 Python 环境
请确认运行项目所使用的 Python 解释器绝对路径（通常在 venv 虚拟环境中）。
```bash
# 进入项目目录
cd /opt/xinpin/xp-fee-calculator
# 查看当前虚拟环境的 python 路径
which python 
# 假设输出为: /opt/xinpin/xp-fee-calculator/.venv/bin/python
```

### 1.3 确认数据库连接
由于 `src/sync_db_to_exel.py` 脚本直接使用硬编码的数据库连接配置，请确保服务器能够访问脚本中配置的 MySQL：
- Host: 10.243.0.221
- Port: 3306

---

## 2. 配置 Crontab

### 2.1 打开编辑器
执行以下命令打开当前用户的 Crontab 编辑界面：
```bash
crontab -e
```

### 2.2 添加定时任务
在文件末尾添加以下一行配置。

**场景 A：每月 1 号凌晨 4:00 执行 (推荐)**
```bash
# 自动更新铺货费计算器门店数据 (每月1号运行)
0 4 1 * * cd /opt/xinpin/xp-fee-calculator && .venv/bin/python src/sync_db_to_exel.py >> logs/cron_sync.log 2>&1
```

**场景 B：每天凌晨 3:00 执行 (更高频)**
```bash
# 自动更新铺货费计算器门店数据 (每日运行)
0 3 * * * cd /opt/xinpin/xp-fee-calculator && .venv/bin/python src/sync_db_to_exel.py >> logs/cron_sync.log 2>&1
```

### 2.3 验证语法
配置完成后保存退出。可以使用 `crontab -l` 查看是否保存成功。

> [!TIP]
> **关键点解释**:
> *   `cd /opt/xinpin/xp-fee-calculator`：必须先切换到项目根目录，否则 Python 可能找不到 `src` 模块。
> *   `.venv/bin/python`：使用项目专属的虚拟环境 Python，避免库缺失。
> *   `>> logs/cron_sync.log 2>&1`：将输出日志（包含成功或报错信息）追加保存到日志文件，便于排查。**请确保 `logs` 目录已存在**。

---

## 3. 手动创建日志目录
为了避免日志重定向报错，请手动创建 logs 文件夹：
```bash
mkdir -p /opt/xinpin/xp-fee-calculator/logs
```

## 4. 验证更新是否生效

配置完成后，您可以手动运行一次命令来测试：

```bash
cd /opt/xinpin/xp-fee-calculator
.venv/bin/python src/sync_db_to_exel.py
```

### 观察点
1.  **终端输出**: 应显示 `🎉 Sync completed successfully!`。
2.  **文件时间**: 查看 `data/store_master.xlsx` 的修改时间是否变为当前时间 (`ls -l data/store_master.xlsx`)。
3.  **Web 页面**: 刷新 Streamlit 页面，右上角的“门店表更新时间”应自动从旧时间变更为新时间（得益于 Smart Caching 策略，无需重启 Web 服务）。
