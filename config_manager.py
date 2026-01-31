"""配置管理文件"""
import os
import json
import shutil
from constants import get_config_file


def load_config() -> dict:
    """从JSON文件加载配置"""
    config_file = get_config_file()
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {str(e)}")
        # 尝试从备份恢复
        backup_path = config_file + ".bak"
        if os.path.exists(backup_path):
            try:
                print("尝试从备份恢复配置...")
                shutil.copy2(backup_path, config_file)
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e2:
                print(f"从备份恢复失败: {str(e2)}")
    return {"services": []}


def save_config(config_data: dict) -> bool:
    """保存配置到JSON文件（带备份机制和故障恢复）"""
    config_file = get_config_file()
    temp_path = config_file + ".tmp"
    backup_path = config_file + ".bak"
    
    try:
        # 1. 先写入临时文件
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 2. 备份原文件（如果存在）
        if os.path.exists(config_file):
            try:
                shutil.copy2(config_file, backup_path)
            except Exception as e:
                print(f"备份配置文件失败: {str(e)}")
        
        # 3. 原子性替换（Windows需要先删除原文件）
        if os.path.exists(config_file):
            os.remove(config_file)
        os.rename(temp_path, config_file)
        
        return True
    except Exception as e:
        print(f"保存配置失败: {str(e)}")
        # 尝试恢复备份
        try:
            if os.path.exists(backup_path) and not os.path.exists(config_file):
                print("尝试恢复备份...")
                shutil.copy2(backup_path, config_file)
        except Exception as e2:
            print(f"恢复备份失败: {str(e2)}")
        
        # 清理临时文件
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        return False


class ConfigManager:
    """配置管理器（带备份和事务支持）"""
    def __init__(self) -> None:
        self.config = load_config()
    
    def get_services(self) -> list:
        return self.config.get("services", [])
    
    def set_services(self, services: list) -> bool:
        """保存服务配置（带备份机制）"""
        self.config["services"] = services
        return save_config(self.config)
    
    def restore_backup(self) -> bool:
        """从备份恢复配置"""
        backup_path = CONFIG_FILE + ".bak"
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, CONFIG_FILE)
                self.config = load_config()
                return True
        except Exception as e:
            print(f"恢复备份失败: {str(e)}")
        return False
