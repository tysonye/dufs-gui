"""服务与状态机文件"""
# pyright: reportAny=false
# pyright: reportUnannotatedClassAttribute=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false

import os
import threading
import subprocess
import time
import re
from PyQt5.QtCore import pyqtSignal, QObject, QMetaObject, Qt, pyqtSlot


class ServiceStatus:
    """服务状态枚举"""
    STOPPED = "已停止"
    RUNNING = "运行中"
    STARTING = "启动中"
    STOPPING = "停止中"
    ERROR = "错误"


class ServiceStateMachine:
    """服务状态机，确保状态转换的合法性"""
    
    def __init__(self):
        """初始化状态机"""
        # 定义服务状态转换规则
        self.service_transitions = {
            ServiceStatus.STOPPED: [ServiceStatus.STARTING],
            ServiceStatus.STARTING: [ServiceStatus.RUNNING, ServiceStatus.STOPPED, ServiceStatus.ERROR],
            ServiceStatus.RUNNING: [ServiceStatus.STOPPING, ServiceStatus.ERROR],
            ServiceStatus.STOPPING: [ServiceStatus.STOPPED],
            ServiceStatus.ERROR: [ServiceStatus.STOPPED, ServiceStatus.STARTING]
        }
        
        # 定义公网访问状态转换规则
        self.public_transitions = {
            "stopped": ["starting"],
            "starting": ["running", "stopping", "stopped"],
            "running": ["stopping", "stopped"],
            "stopping": ["stopped"]
        }
    
    def can_transition(self, current_status: str, new_status: str, public_access: bool = False) -> bool:
        """检查状态转换是否合法
        
        Args:
            current_status (str): 当前状态
            new_status (str): 新状态
            public_access (bool): 是否为公网访问状态
            
        Returns:
            bool: 状态转换是否合法
        """
        try:
            # 确保参数有效
            if not current_status or not new_status:
                return False
            
            # 状态相同，无需转换
            if current_status == new_status:
                return True
            
            # 检查状态转换规则
            if public_access:
                transitions = self.public_transitions
            else:
                transitions = self.service_transitions
            
            # 检查当前状态是否在转换规则中
            if current_status not in transitions:
                return False
            
            # 检查新状态是否在允许的转换列表中
            return new_status in transitions[current_status]
        except Exception:
            # 捕获所有异常，确保方法不会崩溃
            return False
    
    def validate_combined_state(self, service_status: str, public_status: str) -> bool:
        """验证服务状态和公网访问状态的组合是否合法
        
        Args:
            service_status (str): 服务状态
            public_status (str): 公网访问状态
            
        Returns:
            bool: 状态组合是否合法
        """
        try:
            # 确保参数有效
            if not service_status or not public_status:
                return False
            
            # 服务未运行时，公网访问不能运行
            if service_status == ServiceStatus.STOPPED and public_status in ["running", "starting"]:
                return False
            
            # 服务启动中或运行中时，公网访问状态可以是任意合法状态
            return True
        except Exception:
            # 捕获所有异常，确保方法不会崩溃
            return False


class DufsService(QObject):
    """单个Dufs服务实例"""
    # 状态更新信号（类级别定义）
    status_updated = pyqtSignal()
    # 进度更新信号（类级别定义）
    progress_updated = pyqtSignal(int, str)
    # 日志更新信号（类级别定义）
    log_updated = pyqtSignal(str, bool, str)
    
    def __init__(self, name: str = "默认服务", serve_path: str = ".", port: str = "5000", bind: str = ""):
        super().__init__()
        self.name = name
        self.serve_path = serve_path
        self.port = port
        self.bind = bind
        
        # 权限设置
        self.allow_all = False
        self.allow_upload = False
        self.allow_delete = False
        self.allow_search = False
        self.allow_symlink = False
        self.allow_archive = False
        
        # 多用户权限规则
        self.auth_rules = []
        
        # 进程信息
        self.process = None
        self.status = ServiceStatus.STOPPED
        
        # 访问地址
        self.local_addr = ""
        
        # 添加线程锁，保护共享资源
        self.lock = threading.Lock()
        
        # 日志相关属性
        self.log_widget = None
        self.log_tab_index = None
        
        # 日志线程终止标志
        self.log_thread_terminate = False
        
        # 日志缓冲，用于降低UI更新频率
        self.log_buffer = []
        # 日志刷新定时器
        self.log_timer = None
        
        # 公网访问相关属性
        self.cloudflared_process = None
        self.public_url = ""
        # 统一使用枚举值管理公网访问状态
        self.public_access_status = "stopped"  # stopped, starting, running, stopping
        self.cloudflared_start_progress = 0  # cloudflared启动进度（0-100）
        
        # cloudflared监控相关属性
        self.cloudflared_monitor_thread = None
        self.cloudflared_monitor_terminate = False
        self.cloudflared_restart_count = 0
        self.max_cloudflared_restarts = 3
    
    def is_cloudflared_running(self):
        """检查cloudflared进程是否正在运行"""
        if self.cloudflared_process is None:
            return False
        return self.cloudflared_process.poll() is None
        
    def update_status(self, status: str | None = None, public_access_status: str | None = None) -> bool:
        """统一更新服务状态和公网访问状态，并确保UI更新在主线程中执行
        
        Args:
            status (str, optional): 服务状态
            public_access_status (str, optional): 公网访问状态
            
        Returns:
            bool: 状态更新是否成功
        """
        # 增强状态验证
        if status is not None and status not in [ServiceStatus.STOPPED, ServiceStatus.STARTING, ServiceStatus.RUNNING, ServiceStatus.STOPPING, ServiceStatus.ERROR]:
            print(f"无效的服务状态: {status}")
            return False
        
        if public_access_status is not None and public_access_status not in ["stopped", "starting", "running", "stopping"]:
            print(f"无效的公网访问状态: {public_access_status}")
            return False
        
        # 创建状态机实例
        state_machine = ServiceStateMachine()
        
        # 验证状态转换的合法性
        if status is not None:
            if not state_machine.can_transition(self.status, status):
                return False
        
        if public_access_status is not None:
            if not state_machine.can_transition(self.public_access_status, public_access_status, public_access=True):
                return False
        
        # 验证状态组合的合法性
        new_service_status = status if status is not None else self.status
        new_public_status = public_access_status if public_access_status is not None else self.public_access_status
        if not state_machine.validate_combined_state(new_service_status, new_public_status):
            return False
        
        # 使用线程锁保护状态更新
        with self.lock:
            # 更新服务状态（如果提供）
            if status is not None:
                self.status = status
            
            # 更新公网访问状态（如果提供）
            if public_access_status is not None:
                self.public_access_status = public_access_status
        
        # 通过QMetaObject确保在UI线程中发射信号
        if threading.current_thread() is not threading.main_thread():
            QMetaObject.invokeMethod(
                self,
                "_emit_status_updated",
                Qt.QueuedConnection
            )
        else:
            self.status_updated.emit()
        
        return True
    
    @pyqtSlot()
    def _emit_status_updated(self):
        """在UI线程中发射信号"""
        self.status_updated.emit()
    
    def get_cloudflared_path(self):
        """获取cloudflared路径，直接使用根目录的cloudflared.exe"""
        import shutil
        
        # 定义cloudflared文件名（仅支持Windows系统）
        cloudflared_filename = "cloudflared.exe"
        
        # 检查多个位置，优先使用根目录的cloudflared.exe
        check_paths = [
            os.path.join(os.getcwd(), cloudflared_filename),  # 根目录
            os.path.join(os.path.dirname(os.path.abspath(__file__)), cloudflared_filename),  # 脚本所在目录
        ]
        
        for path in check_paths:
            if os.path.exists(path):
                return path
        
        # 尝试从系统PATH获取
        if shutil.which(cloudflared_filename):
            return cloudflared_filename
        
        # 如果都找不到，直接返回cloudflared.exe（会在运行时失败）
        return cloudflared_filename
    
    def start(self, log_manager=None):
        """启动服务
        
        Args:
            log_manager: 日志管理器实例
        """
        from constants import AppConstants
        
        try:
            # 确保服务未在运行中
            if self.status != ServiceStatus.STOPPED:
                if log_manager:
                    log_manager.append_log(f"服务 '{self.name}' 已在运行中，跳过启动", False, self.name)
                return False
            
            # 记录启动服务日志
            if log_manager:
                log_manager.append_log(f"开始启动服务 '{self.name}'", False, self.name)
            
            # 更新服务状态为启动中
            self.update_status(ServiceStatus.STARTING)
            
            # 检查并验证dufs.exe
            from constants import verify_executable
            if not verify_executable("dufs.exe"):
                if log_manager:
                    log_manager.append_log("dufs.exe 文件不存在或验证失败", True, self.name)
                self.update_status(ServiceStatus.ERROR)
                return False
            
            # 构建dufs命令
            cmd = ["dufs.exe"]
            cmd.extend([self.serve_path])
            cmd.extend(["--port", self.port])
            
            if self.bind:
                cmd.extend(["--bind", self.bind])
            
            if self.allow_upload:
                cmd.extend(["--allow-upload"])
            
            if self.allow_delete:
                cmd.extend(["--allow-delete"])
            
            if self.allow_search:
                cmd.extend(["--allow-search"])
            
            if self.allow_archive:
                cmd.extend(["--allow-archive"])
            
            if self.allow_all:
                cmd.extend(["--allow-all"])
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                shell=False
            )
            
            # 等待服务启动
            time.sleep(AppConstants.SERVICE_START_WAIT_SECONDS)
            
            # 检查服务是否启动成功
            if self.process.poll() is None:
                # 构建本地地址
                try:
                    # 使用统一的IP获取函数
                    from utils import get_local_ip
                    ip = get_local_ip()
                    self.local_addr = f"http://{ip}:{self.port}"
                except Exception as e:
                    print(f"构建本地地址失败: {str(e)}")
                    self.local_addr = f"http://localhost:{self.port}"
                
                # 启动日志线程
                threading.Thread(target=self.read_service_output, args=(log_manager,), daemon=True).start()
                
                # 更新状态为运行中（会触发status_updated信号）
                self.update_status(ServiceStatus.RUNNING)
                
                if log_manager:
                    log_manager.append_log(f"服务 '{self.name}' 启动成功，地址: {self.local_addr}", False, self.name)
                return True
            else:
                # 服务启动失败
                try:
                    output = self.process.stdout.read()
                    if log_manager:
                        log_manager.append_log(f"服务 '{self.name}' 启动失败: {output}", True, self.name)
                except Exception as e:
                    print(f"读取错误输出失败: {str(e)}")
                self.update_status(ServiceStatus.ERROR)
                return False
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"启动服务失败: {str(e)}", True, self.name)
            self.update_status(ServiceStatus.ERROR)
            return False
    
    def stop(self, log_manager=None):
        """停止服务
        
        Args:
            log_manager: 日志管理器实例
        """
        try:
            # 确保服务正在运行
            if self.status == ServiceStatus.STOPPED:
                if log_manager:
                    log_manager.append_log(f"服务 '{self.name}' 已停止，无需停止", False, self.name)
                return False
            
            # 记录停止服务日志
            if log_manager:
                log_manager.append_log(f"开始停止服务 '{self.name}'", False, self.name)
            
            # 更新状态为停止中
            self.update_status(ServiceStatus.STOPPING)
            
            # 停止公网共享
            if self.public_access_status in ["running", "starting"]:
                self.stop_public_access(log_manager)
            
            # 停止内网服务
            if self.status in [ServiceStatus.RUNNING, ServiceStatus.STOPPING]:
                if self.process:
                    try:
                        self.process.terminate()
                        from constants import AppConstants
                        self.process.wait(timeout=AppConstants.PROCESS_TERMINATE_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        print(f"服务 '{self.name}' 进程终止超时，强制终止")
                        self.process.kill()
                        self.process.wait()
            
            # 清除残留的 dufs 和 cloudflared 进程
            self._kill_residual_processes(log_manager)
            
            # 更新状态
            self.update_status(ServiceStatus.STOPPED)
            self.local_addr = ""
            self.public_url = ""
            
            if log_manager:
                log_manager.append_log(f"服务 '{self.name}' 已停止", False, self.name)
            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"停止服务失败: {str(e)}", True, self.name)
            self.update_status(ServiceStatus.ERROR)
            return False
    
    def _kill_residual_processes(self, log_manager=None):
        """清除当前服务产生的残留进程（只清理该服务的进程，不影响其他服务）
        
        Args:
            log_manager: 日志管理器实例
        """
        import subprocess
        import time
        
        port = self.port
        
        try:
            # 1. 首先终止当前服务的 dufs 进程（通过PID）
            if self.process and self.process.pid:
                try:
                    self._kill_process_tree(self.process.pid, log_manager)
                    if log_manager:
                        log_manager.append_log(f"已终止 dufs 进程 PID:{self.process.pid}", False, self.name)
                except Exception as e:
                    if log_manager:
                        log_manager.append_log(f"终止 dufs 进程失败: {str(e)}", True, self.name)
            
            # 2. 终止当前服务的 cloudflared 进程（通过PID）
            if self.cloudflared_process and self.cloudflared_process.pid:
                try:
                    self._kill_process_tree(self.cloudflared_process.pid, log_manager)
                    if log_manager:
                        log_manager.append_log(f"已终止 cloudflared 进程 PID:{self.cloudflared_process.pid}", False, self.name)
                except Exception as e:
                    if log_manager:
                        log_manager.append_log(f"终止 cloudflared 进程失败: {str(e)}", True, self.name)
            
            # 3. 查找并终止占用该端口的 dufs 进程（精确匹配）
            try:
                result = subprocess.run(
                    ["netstat", "-ano", "|", "findstr", f":{port}"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=5
                )
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                # 获取进程名称
                                proc_result = subprocess.run(
                                    ["tasklist", "|", "findstr", pid],
                                    capture_output=True,
                                    text=True,
                                    shell=True,
                                    timeout=5
                                )
                                if proc_result.stdout and 'dufs' in proc_result.stdout.lower():
                                    # 终止该进程
                                    subprocess.run(
                                        ["taskkill", "/F", "/PID", pid, "/T"],
                                        capture_output=True,
                                        shell=True,
                                        timeout=5
                                    )
                                    if log_manager:
                                        log_manager.append_log(f"已终止占用端口 {port} 的 dufs 进程 PID:{pid}", False, self.name)
                            except Exception:
                                pass
            except Exception as e:
                if log_manager:
                    log_manager.append_log(f"查找端口占用进程时出错: {str(e)}", True, self.name)
            
            # 4. 查找并终止与该服务端口相关的 cloudflared 进程
            try:
                result = subprocess.run(
                    ["wmic", "process", "where", f"CommandLine like '%{port}%'", "get", "ProcessId", "/format:csv"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=5
                )
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[2:]:  # 跳过标题行
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            pid = parts[-1]
                            if pid and pid.isdigit():
                                subprocess.run(
                                    ["taskkill", "/F", "/PID", pid, "/T"],
                                    capture_output=True,
                                    shell=True,
                                    timeout=5
                                )
                                if log_manager:
                                    log_manager.append_log(f"已终止 cloudflared 进程 PID:{pid}", False, self.name)
            except Exception:
                pass
            
            # 5. 释放端口占用
            self._release_port(port)
            
            # 6. 短暂等待确保进程终止
            time.sleep(0.3)
            
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"清除残留进程时出错: {str(e)}", True, self.name)
    
    def _kill_process_tree(self, pid: int, log_manager=None) -> bool:
        """递归终止进程树（使用psutil，如果可用）
        
        Args:
            pid: 进程ID
            log_manager: 日志管理器实例
            
        Returns:
            bool: 是否成功终止
        """
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # 先终止子进程
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            # 等待子进程结束
            gone, alive = psutil.wait_procs(children, timeout=3)
            
            # 强制终止未结束的进程
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # 终止父进程
            parent.terminate()
            parent.wait(timeout=3)
            
            if log_manager:
                log_manager.append_log(f"已清理进程树 PID:{pid}, 子进程数:{len(children)}", False, self.name)
            return True
        except ImportError:
            # 无psutil时回退到taskkill
            try:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid), "/T"],
                    capture_output=True,
                    shell=True
                )
                return True
            except Exception:
                return False
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"清理进程树失败: {str(e)}", True, self.name)
            return False
    
    def _release_port(self, port: int) -> None:
        """释放端口占用
        
        Args:
            port: 端口号
        """
        try:
            # 使用 netsh 命令释放端口（Windows专用）
            import subprocess
            subprocess.run(
                ["netsh", "int", "ipv4", "delete", "excludedportrange", "protocol=tcp", f"startport={port}", "numberofports=1"],
                capture_output=True,
                shell=True
            )
        except Exception:
            pass
    
    def start_public_access(self, log_manager=None):
        """启动公网访问

        Args:
            log_manager: 日志管理器实例
        """
        try:
            # 检查并验证cloudflared.exe
            from constants import verify_executable
            cloudflared_path = self.get_cloudflared_path()
            if not verify_executable(cloudflared_path):
                if log_manager:
                    log_manager.append_log(f"cloudflared.exe 文件不存在或验证失败: {cloudflared_path}", True, self.name)
                return False
            
            # 构建cloudflared命令
            cmd = [cloudflared_path, "tunnel", "--url", self.local_addr]
            
            # 记录启动公网访问的日志
            if log_manager:
                log_manager.append_log(f"启动公网访问: {self.local_addr}", False, self.name)
            
            # 启动进程
            self.cloudflared_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                shell=False
            )
            
            # 更新状态
            self.update_status(public_access_status="starting")
            
            # 启动监控线程
            self.cloudflared_monitor_thread = threading.Thread(target=self.monitor_cloudflared, args=(log_manager,), daemon=True)
            self.cloudflared_monitor_thread.start()
            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"启动公网共享失败: {str(e)}", True, self.name)
            self.update_status(public_access_status="stopped")
            return False
    
    def stop_public_access(self, log_manager=None):
        """停止公网访问
        
        Args:
            log_manager: 日志管理器实例
        """
        try:
            # 设置终止标志，通知监控线程停止
            self.cloudflared_monitor_terminate = True
            
            # 等待监控线程结束
            if self.cloudflared_monitor_thread and self.cloudflared_monitor_thread.is_alive():
                try:
                    self.cloudflared_monitor_thread.join(timeout=2.0)
                except Exception as e:
                    print(f"等待监控线程结束失败: {str(e)}")
            
            # 保存进程引用，避免在操作过程中访问已经释放的内存
            cloudflared_process = getattr(self, 'cloudflared_process', None)
            if cloudflared_process:
                # 记录停止公网访问的日志
                if log_manager:
                    log_manager.append_log("停止公网访问", False, self.name)
                
                try:
                    cloudflared_process.terminate()
                    cloudflared_process.wait(timeout=5)
                except Exception as e:
                    print(f"终止cloudflared进程失败: {str(e)}")
                
                # 更新服务状态
                if hasattr(self, 'public_access_status'):
                    self.public_url = ""
                    self.update_status(public_access_status="stopped")
                
                # 记录停止成功的日志
                if log_manager:
                    log_manager.append_log("公网访问已停止", False, self.name)
            
            # 重置终止标志和线程引用
            self.cloudflared_monitor_terminate = False
            self.cloudflared_monitor_thread = None
            
            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"停止公网共享失败: {str(e)}", True, self.name)
            return False
    
    def monitor_cloudflared(self, log_manager=None):
        """监控cloudflared进程
        
        Args:
            log_manager: 日志管理器实例
        """
        import time
        import re
        
        try:
            cloudflared_process = self.cloudflared_process
            if not cloudflared_process:
                return
            
            # 重置终止标志
            self.cloudflared_monitor_terminate = False
            
            # 添加超时检查
            start_time = time.time()
            timeout = 30  # 30秒超时
            
            # 读取输出
            for line in iter(cloudflared_process.stdout.readline, ''):
                # 检查终止标志
                if self.cloudflared_monitor_terminate:
                    break
                
                if time.time() - start_time > timeout:
                    if log_manager:
                        log_manager.append_log("云流服务启动超时", True, self.name)
                    break
                    
                if cloudflared_process.poll() is not None:
                    break
                    
                # 处理输出
                if "trycloudflare.com" in line:
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        self.public_url = match.group(0)
                        # 确保在主线程中更新状态和UI
                        self.update_status(public_access_status="running")
                        if log_manager:
                            log_manager.append_log(f"公网地址: {self.public_url}", False, self.name)
                elif "error" in line.lower():
                    if log_manager:
                        log_manager.append_log(f"Cloudflare错误: {line.strip()}", True, self.name)
                else:
                    if log_manager:
                        log_manager.append_log(line.strip(), False, self.name)
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.01)
            
            # 处理进程退出
            if cloudflared_process.poll() is not None:
                self.public_url = ""
                self.update_status(public_access_status="stopped")
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"监控cloudflared失败: {str(e)}", True, self.name)
            self.update_status(public_access_status="error")
    
    def read_service_output(self, log_manager=None):
        """读取服务输出
        
        Args:
            log_manager: 日志管理器实例
        """
        try:
            if self.process and self.process.stdout:
                # 直接读取输出，使用迭代器方式
                while self.process.poll() is None:
                    try:
                        line = self.process.stdout.readline()
                        if not line:
                            break
                        if line.strip():
                            # 使用日志管理器添加日志
                            if log_manager:
                                log_manager.append_log(line.strip(), False, self.name)
                    except Exception as e:
                        print(f"读取服务输出失败: {str(e)}")
                        break
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"读取服务输出失败: {str(e)}", True, self.name)
