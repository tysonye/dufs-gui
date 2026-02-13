"""使用 Win32 API 创建原生启动画面 - 修复版"""
import ctypes
from ctypes import wintypes

# Win32 常量
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_CAPTION = 0x00C00000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

SW_SHOWNOACTIVATE = 4

# 颜色定义 (BGR 格式 - 蓝绿红)
def rgb(r, g, b):
    """将 RGB 转换为 Win32 BGR"""
    return (b << 16) | (g << 8) | r

COLOR_BG = rgb(248, 250, 252)          # 极浅灰背景 #F8FAFC
COLOR_PRIMARY = rgb(232, 112, 58)      # 珊瑚橙 #E8703A
COLOR_TEXT_TITLE = rgb(45, 55, 72)     # 深灰标题 #2D3748
COLOR_TEXT_SUB = rgb(100, 116, 139)    # 中灰副标题 #64748B
COLOR_ACCENT = rgb(56, 189, 248)       # 天蓝 #38BDF8
COLOR_LIGHT_GRAY = rgb(226, 232, 240)  # 浅灰 #E2E8F0

# API 引用
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32


class Win32SplashScreen:
    """修复后的 Win32 启动画面"""
    
    def __init__(self, title="DufsGUI", subtitle="文件服务器管理工具"):
        self.hwnd = None
        self.title = title
        self.subtitle = subtitle
        self.message = "正在初始化..."
        self.progress = 0
        self.width = 480
        self.height = 280
        self._create_window()
        
    def _create_window(self):
        """创建窗口"""
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        
        hInstance = kernel32.GetModuleHandleW(None)
        
        # 创建窗口 - 使用 STATIC 类，无边框无标题栏
        self.hwnd = user32.CreateWindowExW(
            WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            "STATIC",
            self.title,
            WS_POPUP | WS_VISIBLE,
            x, y, self.width, self.height,
            None, None, hInstance, None
        )
        
        if not self.hwnd:
            return
        
        # 显示窗口
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        user32.UpdateWindow(self.hwnd)
        
        # 初始绘制
        self._draw_frame()
        
    def _draw_frame(self):
        """绘制完整界面"""
        if not self.hwnd:
            return
            
        hdc = user32.GetDC(self.hwnd)
        if not hdc:
            return
            
        try:
            # 1. 绘制背景
            self._draw_background(hdc)
            
            # 2. 绘制装饰元素
            self._draw_decorations(hdc)
            
            # 3. 绘制标题
            self._draw_title(hdc)
            
            # 4. 绘制副标题
            self._draw_subtitle(hdc)
            
            # 5. 绘制状态消息
            self._draw_message(hdc)
            
            # 6. 绘制进度条
            self._draw_progress_bar(hdc)
            
            # 7. 绘制底部装饰线
            self._draw_bottom_line(hdc)
            
        finally:
            user32.ReleaseDC(self.hwnd, hdc)
        
    def _draw_background(self, hdc):
        """绘制背景"""
        brush = gdi32.CreateSolidBrush(COLOR_BG)
        rect = wintypes.RECT(0, 0, self.width, self.height)
        user32.FillRect(hdc, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)
        
    def _draw_decorations(self, hdc):
        """绘制装饰元素"""
        # 左上角装饰圆点
        self._draw_circle(hdc, 40, 60, 6, COLOR_PRIMARY)
        
        # 右侧装饰线
        pen = gdi32.CreatePen(0, 2, COLOR_LIGHT_GRAY)
        old_pen = gdi32.SelectObject(hdc, pen)
        
        for i in range(3):
            y = 80 + i * 25
            gdi32.MoveToEx(hdc, self.width - 60, y, None)
            gdi32.LineTo(hdc, self.width - 30, y)
            
        gdi32.SelectObject(hdc, old_pen)
        gdi32.DeleteObject(pen)
        
        # 小装饰点
        self._draw_circle(hdc, self.width - 45, 180, 4, COLOR_ACCENT)
        self._draw_circle(hdc, self.width - 35, 200, 3, COLOR_LIGHT_GRAY)
        
    def _draw_circle(self, hdc, x, y, radius, color):
        """绘制圆形"""
        brush = gdi32.CreateSolidBrush(color)
        old_brush = gdi32.SelectObject(hdc, brush)
        gdi32.Ellipse(hdc, x - radius, y - radius, x + radius, y + radius)
        gdi32.SelectObject(hdc, old_brush)
        gdi32.DeleteObject(brush)
        
    def _draw_title(self, hdc):
        """绘制标题 - 大字体"""
        font = gdi32.CreateFontW(
            48, 0, 0, 0, 700,  # 48px, 粗体
            0, 0, 0, 0, 0, 0, 0, 0,
            "Microsoft YaHei"
        )
        old_font = gdi32.SelectObject(hdc, font)
        gdi32.SetTextColor(hdc, COLOR_TEXT_TITLE)
        gdi32.SetBkMode(hdc, 1)  # TRANSPARENT
        
        rect = wintypes.RECT(0, 60, self.width, 110)
        user32.DrawTextW(hdc, self.title, -1, ctypes.byref(rect), 
                        0x00000001 | 0x00000004)  # DT_CENTER | DT_VCENTER
        
        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(font)
        
    def _draw_subtitle(self, hdc):
        """绘制副标题 - 中等字体"""
        font = gdi32.CreateFontW(
            18, 0, 0, 0, 400,  # 18px, 正常
            0, 0, 0, 0, 0, 0, 0, 0,
            "Microsoft YaHei"
        )
        old_font = gdi32.SelectObject(hdc, font)
        gdi32.SetTextColor(hdc, COLOR_TEXT_SUB)
        gdi32.SetBkMode(hdc, 1)
        
        rect = wintypes.RECT(0, 115, self.width, 145)
        user32.DrawTextW(hdc, self.subtitle, -1, ctypes.byref(rect),
                        0x00000001 | 0x00000004)
        
        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(font)
        
    def _draw_message(self, hdc):
        """绘制状态消息 - 清晰字体"""
        font = gdi32.CreateFontW(
            16, 0, 0, 0, 500,  # 16px, 中等粗细
            0, 0, 0, 0, 0, 0, 0, 0,
            "Microsoft YaHei"
        )
        old_font = gdi32.SelectObject(hdc, font)
        gdi32.SetTextColor(hdc, COLOR_TEXT_SUB)
        gdi32.SetBkMode(hdc, 1)
        
        rect = wintypes.RECT(0, 170, self.width, 195)
        user32.DrawTextW(hdc, self.message, -1, ctypes.byref(rect),
                        0x00000001 | 0x00000004)
        
        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(font)
        
    def _draw_progress_bar(self, hdc):
        """绘制进度条"""
        bar_x = 90
        bar_y = 210
        bar_width = 300
        bar_height = 6
        
        # 背景条
        brush = gdi32.CreateSolidBrush(COLOR_LIGHT_GRAY)
        rect = wintypes.RECT(bar_x, bar_y, bar_x + bar_width, bar_y + bar_height)
        user32.FillRect(hdc, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)
        
        # 进度条
        if self.progress > 0:
            progress_width = int(bar_width * self.progress / 100)
            brush = gdi32.CreateSolidBrush(COLOR_PRIMARY)
            rect = wintypes.RECT(bar_x, bar_y, bar_x + progress_width, bar_y + bar_height)
            user32.FillRect(hdc, ctypes.byref(rect), brush)
            gdi32.DeleteObject(brush)
            
    def _draw_bottom_line(self, hdc):
        """绘制底部装饰线"""
        colors = [COLOR_PRIMARY, COLOR_ACCENT, rgb(139, 92, 246)]
        segment_width = self.width // len(colors)
        
        for i, color in enumerate(colors):
            pen = gdi32.CreatePen(0, 3, color)
            old_pen = gdi32.SelectObject(hdc, pen)
            x1 = i * segment_width
            x2 = (i + 1) * segment_width if i < len(colors) - 1 else self.width
            gdi32.MoveToEx(hdc, x1, self.height - 3, None)
            gdi32.LineTo(hdc, x2, self.height - 3)
            gdi32.SelectObject(hdc, old_pen)
            gdi32.DeleteObject(pen)
            
    def update_progress(self, message, progress=None):
        """更新进度"""
        self.message = message
        if progress is not None:
            self.progress = max(0, min(100, progress))
        print(f"[启动] {message}")
        # 立即重绘
        self._draw_frame()
            
    def close(self):
        """关闭窗口"""
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None
            
    def __del__(self):
        """析构函数"""
        self.close()
