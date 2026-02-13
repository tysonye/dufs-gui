"""启动性能分析器 - 测量和优化程序启动时间"""

import time
import functools
from typing import Dict, List, Optional
from contextlib import contextmanager


class StartupProfiler:
    """启动性能分析器 - 记录各阶段耗时"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._timings: Dict[str, List[float]] = {}
        self._start_time: Optional[float] = None
        self._total_start: Optional[float] = None
        self._enabled = True
    
    def enable(self):
        """启用性能分析"""
        self._enabled = True
    
    def disable(self):
        """禁用性能分析"""
        self._enabled = False
    
    def start(self):
        """开始记录总时间"""
        self._total_start = time.perf_counter()
        self._timings.clear()
    
    @contextmanager
    def measure(self, name: str):
        """上下文管理器测量代码块耗时
        
        使用示例:
            with profiler.measure("导入模块"):
                import some_module
        """
        if not self._enabled:
            yield
            return
        
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            if name not in self._timings:
                self._timings[name] = []
            self._timings[name].append(elapsed)
    
    def record(self, name: str, elapsed: float):
        """记录耗时"""
        if not self._enabled:
            return
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(elapsed)
    
    def get_report(self) -> str:
        """生成性能报告"""
        if not self._timings:
            return "暂无性能数据"
        
        lines = ["\n========== 启动性能分析报告 =========="]
        
        # 计算总时间
        total_elapsed = 0
        for timings in self._timings.values():
            total_elapsed += sum(timings)
        
        if self._total_start:
            real_total = time.perf_counter() - self._total_start
            lines.append(f"总启动时间: {real_total*1000:.2f} ms")
            lines.append(f"测量时间合计: {total_elapsed*1000:.2f} ms")
            lines.append("")
        
        # 按耗时排序
        sorted_items = sorted(
            self._timings.items(),
            key=lambda x: sum(x[1]),
            reverse=True
        )
        
        lines.append(f"{'阶段':<30} {'次数':<8} {'总耗时(ms)':<12} {'平均耗时(ms)':<12}")
        lines.append("-" * 70)
        
        for name, timings in sorted_items:
            total = sum(timings) * 1000
            avg = (total / len(timings)) if timings else 0
            count = len(timings)
            lines.append(f"{name:<30} {count:<8} {total:>10.2f}  {avg:>10.2f}")
        
        lines.append("=" * 70)
        return "\n".join(lines)
    
    def print_report(self):
        """打印性能报告"""
        print(self.get_report())
    
    def save_report(self, filepath: str):
        """保存性能报告到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.get_report())


def profile(name: str):
    """装饰器 - 测量函数耗时
    
    使用示例:
        @profile("初始化UI")
        def setup_ui(self):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = StartupProfiler()
            with profiler.measure(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 全局分析器实例
profiler = StartupProfiler()


# 便捷函数
def start_profiling():
    """开始性能分析"""
    profiler.start()


def print_startup_report():
    """打印启动报告"""
    profiler.print_report()


# 用于测量导入时间的上下文管理器
@contextmanager
def measure_import(module_name: str):
    """测量模块导入时间
    
    使用示例:
        with measure_import("PyQt5"):
            from PyQt5.QtWidgets import QApplication
    """
    with profiler.measure(f"导入: {module_name}"):
        yield
