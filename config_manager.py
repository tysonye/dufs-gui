"""配置管理文件"""
import os
import json
from constants import CONFIG_FILE


def load_config() -> dict:
    """从JSON文件加载配置"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {str(e)}")
    return {"services": []}


def save_config(config_data: dict) -> bool:
    """保存配置到JSON文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置失败: {str(e)}")
    return False


class ConfigManager:
    """简化版配置管理器"""
    def __init__(self) -> None:
        self.config = load_config()
    
    def get_services(self) -> list:
        return self.config.get("services", [])
    
    def set_services(self, services: list) -> bool:
        self.config["services"] = services
        return save_config(self.config)
