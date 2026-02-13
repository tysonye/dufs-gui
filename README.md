# DufsGUI - 文件服务器管理工具

一个基于 PyQt5 开发的 Windows 桌面应用程序，为 [DUFS](https://github.com/sigoden/dufs) 文件服务器提供图形化管理界面，支持本地网络共享和公网访问功能。

## 功能特性

### 核心功能
- **多服务管理** - 同时管理多个 DUFS 文件服务器实例
- **可视化配置** - 通过图形界面配置服务路径、端口、权限等参数
- **服务状态监控** - 实时显示服务运行状态（运行中/停止/错误等）
- **自动端口分配** - 智能检测并分配可用端口，避免冲突
- **配置持久化** - 自动保存服务配置，支持原子写和备份恢复

### 权限控制
- 允许上传文件
- 允许删除文件  
- 允许搜索文件
- 允许打包下载（Archive）
- 允许所有操作（快捷开关）
- 账户认证（用户名/密码）

### 网络访问
- **本地访问** - 自动生成内网访问地址
- **公网访问** - 集成 Cloudflare Tunnel，一键开启外网访问
- **访问地址管理** - 支持查看和复制访问链接

### 系统托盘
- 最小化到系统托盘
- 托盘菜单快速管理服务
- 托盘消息通知
- 开机自启动支持

### 日志管理
- 实时查看服务日志
- 独立日志窗口
- 日志自动刷新
- 支持多服务日志切换

## 技术架构

### 项目结构
```
dufs-gui/
├── main.py                 # 程序入口
├── main_window.py          # 主窗口（协调者模式）
├── main_view.py            # 主视图（UI层）
├── main_controller.py      # 主控制器（业务逻辑层）
├── service.py              # 服务模块导出
├── base_service.py         # 基础服务实现
├── service_state.py        # 服务状态机
├── cloudflare_tunnel.py    # Cloudflare 隧道管理
├── service_manager.py      # 服务管理器
├── service_dialog.py       # 服务配置对话框
├── service_info_dialog.py  # 服务信息对话框
├── config_manager.py       # 配置管理器（线程安全）
├── tray_manager.py         # 托盘管理器
├── tray_controller.py      # 托盘菜单构建器
├── tray_event_handler.py   # 托盘事件处理器
├── log_manager.py          # 日志管理器
├── log_window.py           # 日志窗口
├── auto_saver.py           # 自动保存器
├── event_bus.py            # 事件总线
├── utils.py                # 工具函数
├── constants.py            # 常量定义
└── build.py                # 打包脚本
```

### 架构模式
- **协调者模式** - MainWindow 作为协调者，组合 View、Controller 和 AutoSaver
- **状态机模式** - ServiceStateMachine 管理服务状态转换
- **观察者模式** - 通过 PyQt 信号槽机制实现组件间通信
- **线程安全** - 使用锁机制保护共享数据（配置、服务列表等）

## 环境要求

- Windows 10/11
- Python 3.8+（开发/源码运行）
- PyQt5
- requests

## 安装使用



### 方式一：源码运行
```bash
# 克隆仓库
git clone https://github.com/yourusername/dufs-gui.git
cd dufs-gui

# 安装依赖
pip install PyQt5 requests

# 运行程序
python main.py
```

### 方式二：自行打包
```bash
# 安装打包依赖
pip install pyinstaller

# 执行打包
python build.py
```

打包输出目录：`dist/DufsGUI/`

## 使用说明

### 添加服务
1. 点击"添加服务"按钮
2. 填写服务名称、选择服务路径
3. 设置端口号（留空则自动分配）
4. 配置权限选项
5. 点击"确定"保存

### 启动服务
- 选中服务，点击"启动"按钮
- 或使用托盘菜单快速启动

### 开启公网访问
1. 确保服务已启动
2. 点击"公网"按钮
3. 首次使用会自动下载 cloudflared
4. 等待生成公网地址

### 查看日志
- 选中服务，点击"日志"按钮
- 或双击服务打开信息对话框

### 配置说明
配置文件位置：`%APPDATA%\DufsGUI\dufs_config.json`

配置包含：
- 服务列表（名称、路径、端口、权限等）
- 应用状态（窗口位置、大小等）

## 安全说明

### 端口安全
- 自动过滤浏览器黑名单端口（如 22, 80, 443 等）
- 自动过滤系统保留端口
- 启动前检测端口占用情况

### 路径安全
- 服务路径验证，防止路径遍历攻击
- 规范化路径处理

### 进程安全
- 程序退出时自动清理残留进程
- 进程组管理，防止孤儿进程
- 子进程生命周期监控

## 依赖组件

### 内置工具
- `dufs.exe` - 文件服务器核心（需放置于程序目录或 lib 子目录）
- `cloudflared.exe` - Cloudflare 隧道工具（可自动下载）

### Python 依赖
```
PyQt5>=5.15.0
requests>=2.25.0
```

## 开发计划

- [ ] 多用户权限规则配置
- [ ] HTTPS 证书配置
- [ ] 服务运行统计
- [ ] 多语言支持
- [ ] 深色模式主题

## 注意事项

1. **Windows 专用** - 当前版本仅支持 Windows 系统
2. **防火墙设置** - 如无法访问，请检查 Windows 防火墙设置
3. **公网访问** - 使用 Cloudflare Tunnel 可能需要代理下载
4. **端口冲突** - 如遇端口冲突，程序会自动尝试分配其他端口

## 许可证

MIT License

## 致谢

- [DUFS](https://github.com/sigoden/dufs) - 优秀的文件服务器工具
- [Cloudflare](https://www.cloudflare.com/) - 提供隧道服务
