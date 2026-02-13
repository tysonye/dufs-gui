"""配置管理文件（加强版，支持原子写和备份）"""
import os
import json
import shutil
import tempfile
import threading
from typing import Optional
from constants import CONFIG_FILE


# 线程锁，保护配置写入
_config_lock = threading.Lock()


def load_config() -> dict:
    """从JSON文件加载配置（加强版，支持备份恢复）"""
    try:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"配置文件损坏: {str(e)}，尝试从备份恢复")
                # 尝试从备份恢复
                backup_file = f"{CONFIG_FILE}.backup"
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        print("从备份恢复配置成功")
                        return config
                    except (json.JSONDecodeError, IOError, OSError) as e2:
                        print(f"从备份恢复失败: {str(e2)}")
                return {"services": [], "app_state": {}}
    except (IOError, OSError) as e:
        print(f"加载配置失败: {str(e)}")
    return {"services": [], "app_state": {}}


def save_config(config_data: dict) -> bool:
    """保存配置到JSON文件（原子写，防止半写入）

    实现策略：
    1. 写入临时文件
    2. 刷新到磁盘
    3. 重命名为目标文件（原子操作）
    4. 保留备份
    """
    with _config_lock:
        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(CONFIG_FILE)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            # 创建临时文件（在同一目录，确保重命名是原子操作）
            fd, temp_path = tempfile.mkstemp(
                dir=config_dir,
                prefix='.config_tmp_',
                suffix='.json'
            )

            try:
                # 写入临时文件
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # 确保数据写入磁盘

                # 如果原文件存在，先备份
                if os.path.exists(CONFIG_FILE):
                    backup_file = f"{CONFIG_FILE}.backup"
                    try:
                        shutil.copy2(CONFIG_FILE, backup_file)
                    except (IOError, OSError) as e:
                        print(f"备份配置失败: {str(e)}")

                # 原子重命名（Windows: 先删除再重命名）
                if os.path.exists(CONFIG_FILE):
                    if os.name == 'nt':  # Windows
                        # Windows 不能直接覆盖，需要先删除
                        old_backup = f"{CONFIG_FILE}.old"
                        if os.path.exists(old_backup):
                            os.remove(old_backup)
                        os.rename(CONFIG_FILE, old_backup)

                os.rename(temp_path, CONFIG_FILE)

                return True

            except (IOError, OSError) as e:
                # 清理临时文件
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except (IOError, OSError):
                    pass
                raise e

        except (IOError, OSError) as e:
            print(f"保存配置失败: {str(e)}")
            return False


class ConfigManager:
    """配置管理器（加强版，线程安全）"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config = load_config()

    def get_services(self) -> list:
        """获取服务列表"""
        with self._lock:
            return self._config.get("services", []).copy()

    def set_services(self, services: list) -> bool:
        """设置服务列表"""
        with self._lock:
            self._config["services"] = services
            return save_config(self._config)

    def get_app_state(self) -> dict:
        """获取应用程序状态"""
        with self._lock:
            return self._config.get("app_state", {}).copy()

    def set_app_state(self, state: dict) -> bool:
        """设置应用程序状态"""
        with self._lock:
            self._config["app_state"] = state
            return save_config(self._config)

    def update_app_state(self, **kwargs) -> bool:
        """更新应用程序状态（增量更新）"""
        with self._lock:
            app_state = self._config.get("app_state", {})
            app_state.update(kwargs)
            self._config["app_state"] = app_state
            return save_config(self._config)

    def reload(self) -> bool:
        """重新加载配置"""
        with self._lock:
            self._config = load_config()
            return True

    def get_config(self) -> dict:
        """获取完整配置（副本）"""
        with self._lock:
            return self._config.copy()
