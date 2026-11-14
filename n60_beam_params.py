# =============================================================================
# 文件：n60_beam_params.py
# 作用：N60 相控阵的 Windows 上位机控制软件（图形界面 + 串口通信）
# =============================================================================
# 【这个程序是干嘛的？—— 项目背景（小白必读）】
#
# 硬件：一台有 60 个麦克风的相控阵设备（5 个子阵 × 每个 12 个阵元，
#       排成一个"碗"的形状），由一块 FPGA 芯片控制，通过串口和电脑通信。
#
# 原理：相控阵就像一支"无形的电子枪"。虽然每个麦克风都是全向收声的，
#       但只要给 60 路信号分别加上不同的【时间延迟】和【幅度加权】，
#       就能让整台设备"只盯着空间中的某一点听"（聚焦），
#       或者"朝某个方向听"（波束偏转），其余方向的声音被压掉。
#       —— 延迟控制"往哪看"，幅度控制"看得多集中"。
#
# 本程序（上位机）要做的事：
#   1. 用图形界面让你拖动滑块，选择"看的方向"（水平角/俯仰角）和"看多远"（距离）；
#   2. 根据这些参数，现场算出 60 个通道各自的延迟（相位）和幅度；
#   3. 把这些数字打包成特定的二进制数据帧，通过串口发给 FPGA；
#   4. FPGA 收到后，就按这些数字驱动 60 路发射/接收电路。
#
# 运行前提：电脑上要先装 Python 和两个第三方库：
#   - PyQt6    ：负责画图形界面（pip install PyQt6）
#   - pyserial ：负责串口通信（pip install pyserial）
# =============================================================================

# -----------------------------------------------------------------------------
# 一、导入工具包
# -----------------------------------------------------------------------------
import sys          # sys：和 Python 解释器本身相关的工具（比如拿命令行参数、退出程序）
import os           # os：操作系统工具（文件路径、文件夹操作等）
import math         # math：数学函数（sin、cos、sqrt、弧度换算等）
import struct       # struct：把数字打包成"二进制字节"（发给 FPGA 时要用）
import datetime     # datetime：日期时间工具（给日志加时间戳）
import csv          # csv：读写 CSV 表格文件（读取离线优化表）

# try / except 是 Python 的"异常处理"：先试着执行，失败了就执行 except 里的内容。
# 这里试着导入 pyserial 库；如果电脑上没装，就跳过并把 serial 设为 None。
# 这样程序不会一启动就崩溃，而是等用户点"连接串口"时再提示"缺少库"。
try:
    import serial               # pyserial 库：负责和串口设备（FPGA）通信
    import serial.tools.list_ports  # 它自带的小工具：枚举电脑上有哪些串口
except ImportError:             # ImportError = "导入失败"（库不存在）
    serial = None               # 把 serial 标记为"没有"，后面代码里判断 serial is None 即可

# 导入 PyQt6 里的控件（PyQt6 是 Python 最流行的图形界面库之一）。
# QtCore   ：核心功能（定时器 QTimer、枚举常量 Qt 等）
# QtGui    ：图形功能（字体 QFont、图标 QIcon 等）
# QtWidgets：各种界面控件（按钮、下拉框、滑动条等）
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,   # 整个 GUI 程序的"总管理员"，每个 PyQt 程序必须有且仅有一个
    QCheckBox,      # 复选框（勾选框）
    QComboBox,      # 下拉框
    QGridLayout,    # 网格布局（把控件按行列摆放）
    QGroupBox,      # 分组框（把相关控件圈在一个带标题的框里）
    QHBoxLayout,    # 水平布局（控件从左到右排）
    QLabel,         # 文字标签
    QMainWindow,    # 主窗口（程序最外层的大窗户）
    QMessageBox,    # 弹窗（提示错误信息用）
    QPushButton,    # 按钮
    QSlider,        # 滑动条（滑块）
    QSpinBox,       # 数字输入框（带上下箭头）
    QTextEdit,      # 多行文本框（用来显示日志）
    QVBoxLayout,    # 垂直布局（控件从上到下排）
    QWidget,        # 通用"控件容器"，一切控件的基类
)

# ==============================================================================
# 二、N60 碗状复合阵列 —— 核心声学常量与几何定义
# ==============================================================================
# 下面的数字都是硬件设计定死的，程序里叫"常量"（全大写是 Python 的约定）。
CHANNEL_COUNT = 60          # 总通道数：60 路麦克风
SOUND_SPEED_M_S = 343.0     # 声速（米/秒）：常温下空气中声音的传播速度
CARRIER_HZ = 40000.0        # 载波频率（赫兹）：40kHz，即发射的超声波频率
PWM_PERIOD_TICKS = 2500     # PWM 周期（计数节拍）：FPGA 用一个 0~2499 的数表示"一个完整相位周期"

MIN_DISTANCE_MM = 500       # 目标距离最小值（毫米）：0.5 米
MAX_DISTANCE_MM = 5000      # 目标距离最大值（毫米）：5 米
MAX_STEER_DEG = 30.0        # 波束最大偏转角（度）：最多朝左右各偏 30°

# 严格解耦的三种幅度模式（下拉框里给用户选的选项）：
MODE_UNIT_COSINE = "unit_cosine (物理法向 3.5次方加权)"   # 模式1：按物理指向性实时计算幅度
MODE_OPTIMIZED_DBC = "optimized_dbc_margin (离线算法优化表)" # 模式2：直接查提前算好的 CSV 表
MODE_UNIFORM = "uniform (全通无衰减 - 仅测总功率)"         # 模式3：全部幅度=1，用于测试总功率
AMPLITUDE_MODES = (MODE_UNIT_COSINE, MODE_OPTIMIZED_DBC, MODE_UNIFORM)  # 三个模式打包成一个元组

# 5 个子阵的水平偏角与基准半径（毫米）：
# 5 组麦克风分别朝 -45°/-22.5°/0°/+22.5°/+45°，围成一个扇形碗面。
UNIT_ANGLES_DEG = [-45.0, -22.5, 0.0, 22.5, 45.0]
BOWL_RADIUS_MM = 176.445    # 碗面所在球面的半径

# 子阵内部 12 个阵元的局部坐标 (mm)，每项是 (水平偏移 x, 垂直偏移 y)。
# 以子阵中心为 (0,0)，正数表示右/上，负数表示左/下。
N12_LOCAL_COORDS = [
    (0.000, 0.000), (14.280, 10.958), (-10.958, 14.280), (-14.280, -10.958),
    (10.958, -14.280), (35.097, 8.011), (15.620, 32.435), (-15.620, 32.435),
    (-35.097, 8.011), (-28.146, -22.446), (0.000, -36.000), (28.146, -22.446)
]


def resource_path(relative_path):
    """把"相对路径"转成程序真正能用的路径。

    为什么要这样写？因为这个程序最后会用 PyInstaller 打包成独立的 .exe，
    打包后所有文件会被压缩进一个临时目录，路径就和开发时不一样了。
    这句代码专门处理"打包后"和"开发时"两种情况。
    """
    # sys._MEIPASS 是 PyInstaller 打包后才会存在的特殊变量，指向解压出来的临时目录。
    # hasattr(对象, 名字) 检查这个对象有没有那个属性。有就说明现在是"打包后"状态。
    if hasattr(sys, "_MEIPASS"):
        # 打包后：文件都在临时目录 _MEIPASS 里，所以拼到它下面。
        return os.path.join(sys._MEIPASS, relative_path)
    # 没打包（正常用 python 运行）：文件就在当前工作目录，直接拼当前目录。
    return os.path.join(os.path.abspath("."), relative_path)

# ==============================================================================
# 三、N60 3D 空间声学解算核心函数
# ==============================================================================
def generate_n60_geometry():
    """动态解算 60 路阵元在三维空间中的绝对坐标 (x, y, z)，单位：毫米

    和 generate_n60_csv.py 里的同名函数功能一样，但注意：
    这个版本返回的单位是【毫米】（CSV 脚本里返回的是米），因为
    本程序里后面所有计算都用毫米做单位，保持一致。
    """
    # 用空列表装结果
    geometry = []
    # enumerate：一边取元素一边编号。unit_id=0~4，angle_deg=-45°~+45°
    for unit_id, angle_deg in enumerate(UNIT_ANGLES_DEG):
        # 度 → 弧度（Python 的三角函数只认弧度）
        theta = math.radians(angle_deg)
        # 子阵中心在碗面上的坐标（毫米）：
        #   cx = 半径 × sin(偏角)      （左右位置）
        #   cy = 0                     （垂直方向，碗只在水平面倾斜）
        #   cz = -半径 × cos(偏角)     （前后位置，负号 = 碗口朝前方）
        cx = BOWL_RADIUS_MM * math.sin(theta)
        cy = 0.0
        cz = -BOWL_RADIUS_MM * math.cos(theta)
        # 遍历该子阵内部的 12 个阵元（lx=局部x，ly=局部y）
        for lx, ly in N12_LOCAL_COORDS:
            # 局部坐标叠加到子阵中心，水平偏移 lx 要跟着子阵旋转：
            #   旋转后 x 方向分量 = lx×cos(θ)，z 方向分量 = lx×sin(θ)
            gx = cx + lx * math.cos(theta)
            gy = cy + ly                 # 垂直方向不旋转，直接叠加
            gz = cz + lx * math.sin(theta)
            # 把 (x,y,z) 存进列表
            geometry.append((gx, gy, gz))
    # 返回 60 个坐标
    return geometry


def limit_direction_n60(az_deg, el_deg):
    """将全空间合成指向角死死限制在 30° 以内

    参数：az_deg = 用户想看的水平角（度），el_deg = 用户想看的俯仰角（度）。
    返回值：把角度换算成"三维方向单位向量"，如果超出 30° 就按比例压缩回来，
    同时算出压缩后的真实角度。

    背景：硬件上波束最多偏 30°，如果用户把两个滑块都拉满（如水平 30° +
    俯仰 30°），合成方向其实偏了 40 多度，超过硬件能力，必须"压"回来。
    """
    # 三角函数算方向向量。先算水平角 az 和俯仰角 el 各自的正弦值。
    # 数学小知识：一个单位向量的三个分量 (sx, sy, sz) 满足 sx²+sy²+sz²=1，
    # 其中 sx=sin(az) 是左右分量，sy=sin(el) 是上下分量。
    sx = math.sin(math.radians(float(az_deg)))   # float() 保险起见转成小数
    sy = math.sin(math.radians(float(el_deg)))
    # 允许的最大"水平偏移量"：sin(30°)=0.5
    max_s = math.sin(math.radians(MAX_STEER_DEG))
    # math.hypot(a,b) = sqrt(a²+b²)，这里算出合成后的总偏转量 sxy
    sxy = math.hypot(sx, sy)
    # 如果总偏转超过了上限 0.5（对应 30°）：
    if sxy > max_s and sxy > 0.0:
        # 按比例缩小（scale < 1），把 sx、sy 一起压回 30° 以内。
        # 这就是"限幅"：方向不变，只是角度变小。
        scale = max_s / sxy
        sx *= scale
        sy *= scale
        sxy = max_s                    # 更新总偏转为上限值
    # 由 sx、sy 反推出第三个分量 sz（前后方向），保证向量长度=1。
    # max(0.0, ...) 防止开根号时出现负数（浮点误差导致）。
    sz = math.sqrt(max(0.0, 1.0 - sx * sx - sy * sy))
    # asin 是 arcsin（反正弦），把分量反算回"度"，得到压缩后的真实角度。
    # max(-1.0, min(1.0, ...))：把参数夹在 [-1,1] 之间，防止浮点误差导致数学域错误。
    actual_az = math.degrees(math.asin(max(-1.0, min(1.0, sx))))
    actual_el = math.degrees(math.asin(max(-1.0, min(1.0, sy))))
    # 综合偏转角（水平和俯仰合起来的真实角度）
    combined_angle = math.degrees(math.asin(max(0.0, min(1.0, sxy))))
    # 把 6 个值打包成"元组"返回（多个返回值用元组装）。
    return sx, sy, sz, actual_az, actual_el, combined_angle


def load_optimized_table(distance_mm, az_deg):
    """从本地 CSV 检索最优降旁瓣幅度分布（最近邻查表）

    作用：当用户选了"离线优化表"模式时，用这个函数去读 generate_n60_csv.py
    生成的那张 CSV，找出和目标 (距离, 角度) 最接近的一行，返回 60 个幅度值。

    参数：distance_mm = 目标距离（毫米），az_deg = 目标方位角（度）。
    """
    # 定位 CSV 文件：仓库根目录下的 analysis_outputs 文件夹里
    here = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(here, "analysis_outputs", "n60_5x12_focus_table_dbc_margin.csv")
    # 如果文件不存在（比如还没运行过生成脚本），就返回 60 个全 1（不衰减）。
    # [1.0] * 60 是"列表乘法"：把一个元素的列表复制 60 份。
    if not os.path.exists(csv_path):
        return [1.0] * CHANNEL_COUNT
    # "最近邻"算法用的两个变量：
    min_diff = float("inf")   # 记录目前找到的最小差值。inf = 正无穷大，保证第一个就能比过
    matched_row = None        # 记录目前最匹配的那一行数据
    try:
        # 打开 CSV 文件，csv.DictReader 按"字典"方式逐行读取
        # （每行会自动变成一个字典，键是表头）
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # 逐行扫描整张表
            for row in reader:
                # 取出这行的距离和角度，转成小数
                d_row = float(row["distance_mm"])
                az_row = float(row["az_deg"])
                # 计算"这行和目标差多远"：
                #   距离差（除以1000归一化）+ 角度差（转弧度）→ 一个二维"距离"
                # math.hypot 算出两者的综合差距，越小越接近。
                diff = math.hypot((distance_mm - d_row) / 1000.0, math.radians(az_deg - az_row))
                # 如果这行比之前找到的都更接近，就更新记录
                if diff < min_diff:
                    min_diff = diff
                    matched_row = row
        # 循环结束，matched_row 就是全表最接近目标的一行。
        # 取出该行的 amp_00 ~ amp_59 共 60 个幅度，全部转成小数后返回。
        if matched_row:
            return [float(matched_row[f"amp_{i:02d}"]) for i in range(CHANNEL_COUNT)]
    except Exception:
        # 读取过程中任何一步出错（文件损坏、格式不对等），都静默跳过，
        # 走最后的兜底逻辑。except 后面没写具体错误类型 = 捕获一切错误。
        pass
    # 兜底：找不到就返回全 1（等于不衰减，安全第一）。
    return [1.0] * CHANNEL_COUNT

# ==============================================================================
# 四、UI 样式表定义
# ==============================================================================
# STYLESHEET 是一大段"CSS 风格的界面美化代码"（Qt 的样式表语法和网页 CSS 很像），
# 用三引号 """...""" 包起来，可以跨多行。作用是给整个窗口设置深色科技风皮肤：
#   深灰背景、青色高亮 (#00E5FF)、橙色警告 (#FF5722) 等。
STYLESHEET = """
QMainWindow { background-color: #1E1E1E; border-image: url('bg.jpg') 0 0 0 0 stretch stretch; }
QWidget { font-family: "Microsoft YaHei UI", "Consolas"; font-size: 16px; color: #E0E0E0; }
QWidget#LeftPanel { background-color: rgba(20, 20, 25, 0.72); border-right: 1px solid rgba(64, 196, 255, 0.24); }
QTextEdit, QComboBox, QSpinBox { background-color: rgba(0, 0, 0, 0.42); border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 4px; padding: 6px; color: #00E5FF; }
QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); color: #E0E0E0; padding: 8px; border-radius: 6px; }
QPushButton:hover { background-color: rgba(64, 196, 255, 0.25); border: 1px solid #40C4FF; color: #40C4FF; }
QPushButton#btn_action { background-color: rgba(0, 188, 212, 0.50); border: 1px solid rgba(0, 229, 255, 0.60); font-weight: bold; }
QPushButton#btn_danger { background-color: rgba(255, 87, 34, 0.55); border: 1px solid rgba(255, 87, 34, 0.70); }
QGroupBox { border: 1px solid rgba(64, 196, 255, 0.30); border-radius: 8px; margin-top: 15px; padding-top: 25px; color: #40C4FF; font-weight: bold; background-color: rgba(0, 0, 0, 0.22); }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QSlider::groove:horizontal { border: 1px solid #777777; height: 8px; background: rgba(0, 0, 0, 0.50); border-radius: 4px; }
QSlider::handle:horizontal { background: #00E5FF; border: 1px solid #00E5FF; width: 18px; margin: -5px 0; border-radius: 9px; }
QLabel.transducer { background-color: rgba(0, 229, 255, 0.08); border: 1px solid rgba(0, 229, 255, 0.30); border-radius: 6px; color: #FFFFFF; font-family: "Consolas"; font-size: 11px; }
"""

# ==============================================================================
# 五、串口通信底层类
# ==============================================================================
# class 是 Python 的"类"关键字。类 = 把"数据 + 操作这些数据的方法（函数）"
# 打包在一起的一个模具。可以把它想象成"一台机器的图纸"，
# 用图纸造出来的每一台机器叫"实例"（instance）。
class SerialLogic:
    """负责和 FPGA 之间的串口收发。"""

    def __init__(self):
        """__init__ 是类的"构造函数"：每次用 SerialLogic() 造新实例时自动执行。
        用来初始化这台"机器"的初始状态。
        """
        # self 代表"这台机器自己"。self.ser 就是这台机器上的一个"串口对象"，
        # 初始时还没打开任何串口，所以是 None（什么都没有）。
        self.ser = None

    def open(self, port, baud):
        """打开串口。port = 串口名字，baud = 波特率（每秒传输多少位）。
        返回值：两个值打包成元组 (是否成功, 提示文字)。
        """
        # 检查三种"开不了"的情况，各自返回失败原因：
        if serial is None: return False, "未安装 pyserial 库"   # 库没装上
        if not port: return False, "未选择串口"                  # 用户没选端口
        if self.ser and self.ser.is_open: return False, "串口已打开"  # 已经开过了
        try:
            # 真正打开串口：
            #   port.split(" ")：串口名可能是 "COM3 (USB Serial)" 这种带描述的，
            #   用空格切开，只取第一个单词 "COM3"。
            #   baudrate=波特率，timeout=0 表示读取时不等待（立刻返回）。
            self.ser = serial.Serial(port=port.split(" ")[0], baudrate=int(baud), timeout=0)
            return True, "成功"
        except Exception as exc:  # 打开失败（端口被占用、不存在等），exc 是错误详情
            return False, str(exc)

    def close(self):
        """关闭串口。"""
        if self.ser:          # 如果串口对象存在
            self.ser.close()  # 关闭它
        self.ser = None       # 置空，表示"当前没有打开的串口"

    def send(self, data):
        """向 FPGA 发送一串字节。data 是 bytes 类型（二进制数据）。
        返回值同样是 (是否成功, 提示文字)。
        """
        if not self.ser or not self.ser.is_open:  # 串口没打开
            return False, "串口未连接"
        try:
            self.ser.write(data)  # 把整包数据写进串口
            return True, "成功"
        except Exception as exc:  # 发送过程中出错（比如线被拔了）
            return False, str(exc)

# ==============================================================================
# 六、上位机主窗体类（整个 GUI 的心脏）
# ==============================================================================
class PhasedArrayWindow(QMainWindow):
    """主窗口类。括号里的 QMainWindow 表示"继承"它：这个类自动拥有
    主窗口的一切能力（显示、关闭、缩放等），我们只需要往里加自己的功能。"""

    def __init__(self):
        """构造函数：程序一创建主窗口就执行，负责初始化所有东西。"""
        # super().__init__()：先调用父类 QMainWindow 的构造函数，
        # 把"主窗口"这份基础能力初始化好（这行是固定模板，必须写）。
        super().__init__()
        # setWindowTitle：设置窗口标题栏文字
        self.setWindowTitle("N60 5x12 相控阵控制器 (底层固件强制指令码: 0x01)")
        # resize：设置窗口大小（宽 1360 像素，高 860 像素）
        self.resize(1360, 860)

        # 尝试加载窗口图标（icon.jpg），如果文件存在才设置，否则跳过。
        icon_path = resource_path("icon.jpg")
        if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))

        # --- 创建核心数据对象 ---
        self.logic = SerialLogic()              # 串口通信"机器"
        self.coords_3d = generate_n60_geometry() # 60 个阵元的 3D 坐标（毫米）
        self.current_amps = [255] * CHANNEL_COUNT   # 当前 60 路的幅度（0~255，255=最大）
        self.current_phases = [0] * CHANNEL_COUNT   # 当前 60 路的相位（0~2499）
        self.transducer_labels = []                 # 存放 60 个界面小标签（后面画阵列图用）

        # --- UI 通信防抖定时器 ---
        # QTimer 是 Qt 的定时器。这个定时器设置为"单次触发"：
        # 用户拖动滑块会触发很多次计算，我们不希望每次都立刻发串口包（太频繁），
        # 而是"停手 120 毫秒后"再发一次 —— 这就是"防抖"（debounce）。
        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)          # 单次模式：触发一次就停
        self.auto_timer.timeout.connect(self.send_to_fpga)  # 时间到 → 调用发送函数

        # --- 自动扫描专用定时器 (1秒间隔) ---
        # 自动扫描：让波束自动从 -30° 扫到 +30°，每 1 秒转 2°。
        # 这个定时器是"重复模式"，每 1000 毫秒触发一次 handle_auto_sweep。
        self.sweep_timer = QTimer(self)
        self.sweep_timer.timeout.connect(self.handle_auto_sweep)
        self.sweep_direction = 1  # 扫描方向：1 表示增加角度（向右扫），-1 表示减小角度（向左扫）

        # 依次调用三个初始化步骤（顺序很重要）：
        self.init_ui()          # 1. 搭建所有界面控件
        self.refresh_ports()    # 2. 扫描电脑上的串口，填进下拉框
        self.calculate_array()  # 3. 按默认参数先算一遍 60 路幅度/相位

    # =====================================================================
    # 六-1. 搭建界面（init_ui）
    # =====================================================================
    def init_ui(self):
        """把窗口里的所有控件摆出来。"""
        # 创建一个"总容器"控件，并把它设为主窗口的内容区
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        # 水平布局：里面的内容从左到右排。左边是控制面板，右边是计算面板。
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 四周不留空白边距
        main_layout.setSpacing(0)                   # 控件之间不留间距

        # ----------------- 左侧控制面板 -----------------
        # 左边一栏：串口连接 + 日志显示，固定宽度 315 像素
        left_panel = QWidget()
        left_panel.setObjectName("LeftPanel")   # 起个名字，让样式表能按名字美化它
        left_panel.setFixedWidth(315)           # 固定宽度
        left_layout = QVBoxLayout(left_panel)   # 垂直布局：从上到下排

        # 标题文字
        lbl_logo = QLabel("FPGA 硬件连接 (N60)")
        lbl_logo.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 20px;")
        left_layout.addWidget(lbl_logo)         # addWidget：把控件放进布局

        # 串口号下拉框 + 波特率下拉框
        self.cmb_port = QComboBox()             # 串口列表（稍后 refresh_ports 填充）
        self.cmb_baud = QComboBox()             # 波特率列表
        self.cmb_baud.addItems(["115200", "921600", "9600"])  # 三种常见波特率
        self.cmb_baud.setCurrentText("921600")  # 默认选 921600（最快的）

        # 依次放入布局：文字标签、下拉框、刷新按钮
        left_layout.addWidget(QLabel("串口号 (Port):"))
        left_layout.addWidget(self.cmb_port)
        btn_refresh = QPushButton("刷新串口")
        btn_refresh.clicked.connect(self.refresh_ports)  # 点击 → 重新扫描串口
        left_layout.addWidget(btn_refresh)

        left_layout.addWidget(QLabel("波特率 (Baudrate):"))
        left_layout.addWidget(self.cmb_baud)

        # "连接 FPGA" 按钮：点击后切换 连接/断开 状态
        self.btn_open = QPushButton("连接 FPGA")
        self.btn_open.setObjectName("btn_action")   # 用样式表里的青色风格
        self.btn_open.setMinimumHeight(44)          # 最小高度 44，更显眼
        self.btn_open.clicked.connect(self.toggle_serial)  # 点击 → toggle_serial
        left_layout.addWidget(self.btn_open)

        # 复选框："参数修改后自动同步" —— 勾上后，改参数会自动发串口包给 FPGA
        self.chk_auto_send = QCheckBox("参数修改后自动同步")
        left_layout.addWidget(self.chk_auto_send)

        # 留一点空白，然后放"运行日志"文本框（只读，显示发帧记录）
        left_layout.addSpacing(16)
        left_layout.addWidget(QLabel("运行日志:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)              # 只读：用户不能手动改内容
        left_layout.addWidget(self.txt_log)

        # 清空日志按钮：点击后调用文本框自带的 clear() 方法
        btn_clear = QPushButton("清空日志")
        btn_clear.clicked.connect(self.txt_log.clear)
        left_layout.addWidget(btn_clear)

        # ----------------- 右侧计算面板 -----------------
        # 右边：参数控制 + 阵列图形 + 发送按钮
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)  # 四周留 20 像素边距

        # 分组框一："N60 空间聚焦与 3D 偏转控制"
        self.grp_ctrl = QGroupBox("N60 空间聚焦与 3D 偏转控制")
        ctrl_l = QVBoxLayout(self.grp_ctrl)

        # 一行：幅度加窗模式下拉框（三种模式，见前面 AMPLITUDE_MODES）
        h_amp = QHBoxLayout()                       # 水平行布局
        h_amp.addWidget(QLabel("幅度加窗模式:"))
        self.cmb_amp = QComboBox()
        self.cmb_amp.addItems(AMPLITUDE_MODES)      # 放入三个模式选项
        self.cmb_amp.setCurrentText(MODE_UNIT_COSINE)  # 默认用物理法向加权模式
        # 信号槽机制（Qt 的核心）：currentIndexChanged（用户切换选项）触发时，
        # 自动调用 self.calculate_array（重新计算 60 路参数）。
        self.cmb_amp.currentIndexChanged.connect(self.calculate_array)
        h_amp.addWidget(self.cmb_amp)
        h_amp.addStretch()                          # 占位弹性空间，把内容顶到左边
        ctrl_l.addLayout(h_amp)                     # 把这一行放进纵向布局

        # 水平角滑块：范围 -30°~+30°，初始 0°
        self.lbl_az = QLabel()                      # 显示当前水平角的标签
        self.sld_az = self.make_slider(-int(MAX_STEER_DEG), int(MAX_STEER_DEG), 0)
        self.sld_az.valueChanged.connect(self.calculate_array)  # 拖动 → 重算
        ctrl_l.addLayout(self.make_labeled_slider(self.lbl_az, self.sld_az))

        # 俯仰角滑块：范围 -30°~+30°，初始 0°
        self.lbl_el = QLabel()
        self.sld_el = self.make_slider(-int(MAX_STEER_DEG), int(MAX_STEER_DEG), 0)
        self.sld_el.valueChanged.connect(self.calculate_array)
        ctrl_l.addLayout(self.make_labeled_slider(self.lbl_el, self.sld_el))

        # 距离行：滑块 + 数字输入框，两者联动（改一个另一个跟着变）
        h_dist = QHBoxLayout()
        self.lbl_dist = QLabel()                    # 显示当前距离的标签
        self.lbl_dist.setFixedWidth(240)
        self.sld_dist = QSlider(Qt.Orientation.Horizontal)  # 水平滑块
        self.sld_dist.setRange(MIN_DISTANCE_MM, MAX_DISTANCE_MM)  # 500~5000 毫米
        self.sld_dist.setValue(1000)                # 默认 1000 毫米 = 1 米
        self.sld_dist.valueChanged.connect(self.distance_slider_changed)
        self.spn_dist = QSpinBox()                  # 数字输入框
        self.spn_dist.setRange(MIN_DISTANCE_MM, MAX_DISTANCE_MM)
        self.spn_dist.setValue(1000)
        self.spn_dist.setSuffix(" mm")              # 数字后面自动带 " mm" 单位
        self.spn_dist.valueChanged.connect(self.distance_spin_changed)
        h_dist.addWidget(self.lbl_dist)
        h_dist.addWidget(self.sld_dist)
        h_dist.addWidget(self.spn_dist)

        # 新增：自动扫描模式复选框 —— 勾上后波束自动左右扫
        self.chk_auto_sweep = QCheckBox("启用自动扫描模式 (水平角 ±30°, 步进 2°, 间隔 1s)")
        self.chk_auto_sweep.setStyleSheet("color: #FF9800; font-weight: bold;")  # 橙色醒目
        self.chk_auto_sweep.stateChanged.connect(self.toggle_auto_sweep)  # 勾选状态变化 → 切换扫描
        ctrl_l.addWidget(self.chk_auto_sweep)

        # 增加提示：坐标原点位于曲率中心
        # f-string 里 {-BOWL_RADIUS_MM:.1f} 表示把数值保留 1 位小数填入文字
        lbl_origin_tip = QLabel(f"注：空间坐标系原点(0,0,0)位于阵列中心前方 {-BOWL_RADIUS_MM:.1f}mm 的虚拟曲率中心处。")
        lbl_origin_tip.setStyleSheet("color: #777777; font-size: 12px;")
        ctrl_l.addWidget(lbl_origin_tip)

        # 角度限幅提示标签（当用户超范围时这里会显示警告文字）
        self.lbl_limited = QLabel()
        self.lbl_limited.setStyleSheet("color: #FFC107;")
        ctrl_l.addWidget(self.lbl_limited)
        right_layout.addWidget(self.grp_ctrl)       # 整个分组框放进右侧布局

        # ----------------- 硬件测试模块 -----------------
        # 分组框二：单通道扫描测试（调试硬件时用：只点亮某一路）
        self.grp_test = QGroupBox("硬件调试: 单通道扫描测试")
        self.grp_test.setStyleSheet("QGroupBox { border-color: #FF5722; color: #FF5722; }")  # 橙色主题
        test_l = QHBoxLayout(self.grp_test)

        # 复选框：启用测试模式（幅度强制 255，相位强制 0）
        self.chk_test_mode = QCheckBox("启用单通道测试 (幅度强制 255, 相位强制 0)")
        self.chk_test_mode.stateChanged.connect(self.toggle_test_mode)
        test_l.addWidget(self.chk_test_mode)

        # 测试通道编号输入框：0~59，默认禁用（勾上测试模式才可操作）
        test_l.addWidget(QLabel(f"   测试通道 (0-{CHANNEL_COUNT-1}):"))
        self.spn_test_ch = QSpinBox()
        self.spn_test_ch.setRange(0, CHANNEL_COUNT - 1)
        self.spn_test_ch.setEnabled(False)          # 初始灰色不可点
        self.spn_test_ch.valueChanged.connect(self.update_test_state)  # 换通道 → 更新
        test_l.addWidget(self.spn_test_ch)
        test_l.addStretch()                         # 右侧留白
        right_layout.addWidget(self.grp_test)

        # ----------------- N60 5x12 碗状图形网格映射 -----------------
        # 分组框三：用 60 个小格子画一张"碗形阵列俯视图"，
        # 每个格子代表一个阵元，实时显示它的幅度和相位（方便肉眼检查）。
        grp_array = QGroupBox("N60 碗状物理阵列映射图 (U0E0..U4E11 对应 transducer_io[0..59])")
        array_l = QGridLayout(grp_array)            # 网格布局：行列摆放
        array_l.setSpacing(4)

        # grid_positions() 先算出每个通道应该放在网格的第几行第几列
        positions = self.grid_positions()
        # 循环创建 60 个标签，每个代表一个阵元
        for ch in range(CHANNEL_COUNT):
            row, col = positions[ch]                # 取出这个通道的 (行, 列)
            lbl = QLabel()
            lbl.setProperty("class", "transducer")  # 设 CSS 类名，套用样式表美化
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 文字居中
            lbl.setFixedSize(64, 52)                # 固定格子大小
            array_l.addWidget(lbl, row, col, alignment=Qt.AlignmentFlag.AlignCenter)
            self.transducer_labels.append(lbl)      # 存起来，后面刷新显示要用

        # stretch=1：让阵列图区域在窗口变大时优先拉伸占满空间
        right_layout.addWidget(grp_array, stretch=1)

        # 最底下的大按钮：一键把当前参数打包发给 FPGA
        self.btn_send = QPushButton("同步参数至 FPGA (强制 0x01 帧)")
        self.btn_send.setObjectName("btn_action")
        self.btn_send.setMinimumHeight(55)
        self.btn_send.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))  # 大号粗体字
        self.btn_send.clicked.connect(self.send_to_fpga)   # 点击 → 发送
        right_layout.addWidget(self.btn_send)

        # 最后把左右两个面板装进主布局（左 | 右）
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    # =====================================================================
    # 六-2. 几个界面小工具函数
    # =====================================================================
    def make_slider(self, low, high, value):
        """工厂函数：造一个水平滑块并设好范围/初始值，返回它。"""
        slider = QSlider(Qt.Orientation.Horizontal)  # 水平方向滑块
        slider.setRange(low, high)   # 范围
        slider.setValue(value)       # 初始值
        return slider

    def make_labeled_slider(self, label, slider):
        """工厂函数：把"文字标签 + 滑块"装进一个水平布局并返回。"""
        layout = QHBoxLayout()
        label.setFixedWidth(240)     # 标签固定宽度，让滑块对齐更整齐
        layout.addWidget(label)
        layout.addWidget(slider)
        return layout

    def grid_positions(self):
        """将 3D 全局平面坐标无损映射至 2D 密铺 UI 网格

        把 60 个阵元的实际空间位置（x: 左右, y: 上下）按比例换算成
        界面网格的 (行, 列)，并用"就近找空格"的方式避免两个阵元重叠。
        这样画出来的阵列图，位置关系和真实硬件碗形大致一致。
        """
        positions = []          # 存放每个通道的 (行, 列)
        used = set()            # 记录哪些格子已经被占了（set = 集合，元素不重复）
        # 逐个通道处理
        for ch in range(CHANNEL_COUNT):
            gx, gy, _ = self.coords_3d[ch]   # 取出坐标；"_" 表示第三个值 z 用不到，随手丢弃
            # 把 x（-176~+176mm 左右）映射到 0~24 列：
            #   (gx + 160) / 320 × 24，再四舍五入成整数
            col0 = int(round((gx + 160.0) / 320.0 * 24))
            # 把 y（±36mm 上下）映射到 0~6 行
            row0 = int(round((36.0 - gy) / 72.0 * 6))

            # 初始候选位置 = (row0, col0)
            chosen = (row0, col0)
            # 如果这个位置已被占用，就按下面的顺序往邻近格子找空位
            # （0,0)=原地，(0,1)=右边一格，(1,0)=下面一格，(-1,0)=上面一格……
            offsets = [(0, 0), (0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (0, 2), (0, -2)]
            for dr, dc in offsets:
                # 防止越界：行限制在 0~8，列限制在 0~28
                row = max(0, min(8, row0 + dr))
                col = max(0, min(28, col0 + dc))
                if (row, col) not in used:   # 找到第一个没被占的格子
                    chosen = (row, col)
                    break                    # 立刻结束循环（只找最近的一个空位）
            used.add(chosen)                 # 把这个格子标记为已占用
            positions.append(chosen)         # 记录这个通道的位置
        return positions

    # =====================================================================
    # 六-3. 串口相关操作
    # =====================================================================
    def refresh_ports(self):
        """扫描电脑上所有可用的串口，填进下拉框。"""
        self.cmb_port.clear()                # 先清空下拉框
        if serial is None:                   # 没装 pyserial 库
            self.cmb_port.addItem("缺少 pyserial 库")  # 显示提示文字
            return
        # serial.tools.list_ports.comports()：返回所有串口设备的列表
        for port in serial.tools.list_ports.comports():
            # 每个串口显示成 "设备名 (描述)"，比如 "COM3 (USB Serial Port)"
            self.cmb_port.addItem("{} ({})".format(port.device, port.description))

    def toggle_serial(self):
        """点击"连接/断开 FPGA"按钮时执行：根据当前状态切换。"""
        # 如果按钮现在写着"连接 FPGA"，说明还没连，执行连接：
        if self.btn_open.text() == "连接 FPGA":
            # 调用 SerialLogic.open，传入下拉框里选的串口名和波特率
            ok, msg = self.logic.open(self.cmb_port.currentText(), self.cmb_baud.currentText())
            if ok:                            # 连接成功
                self.btn_open.setText("断开 FPGA")   # 按钮文字改为"断开"
                self.btn_open.setObjectName("btn_danger")  # 换成红色危险风格
                self.btn_open.setStyleSheet("background-color: rgba(255, 87, 34, 0.6);")
                self.log("成功连接至 {}".format(self.cmb_port.currentText()), "green")  # 记日志
            else:                             # 连接失败
                # QMessageBox.critical：弹出红色错误对话框
                QMessageBox.critical(self, "串口错误", "打开失败: {}".format(msg))
        else:
            # 按钮文字不是"连接 FPGA"，说明当前是已连接状态 → 执行断开
            self.logic.close()
            self.btn_open.setText("连接 FPGA")
            self.btn_open.setObjectName("btn_action")
            self.btn_open.setStyleSheet("")   # 清空临时样式
            self.log("已断开连接", "red")

    # =====================================================================
    # 六-4. 距离滑块与数字框的联动
    # =====================================================================
    def distance_slider_changed(self, value):
        """滑块被拖动时：把数字框同步成滑块的值，然后重算参数。
        blockSignals(True) 是"暂时屏蔽信号"：设置数字框时不让它再触发
        自己的 valueChanged 回调，避免两个控件互相触发造成死循环。"""
        self.spn_dist.blockSignals(True)   # 屏蔽数字框的信号
        self.spn_dist.setValue(value)      # 同步数字框 = 滑块值
        self.spn_dist.blockSignals(False)  # 恢复信号
        self.calculate_array()             # 重新计算

    def distance_spin_changed(self, value):
        """数字框被修改时：把滑块同步成数字框的值，然后重算参数（同上防死循环）。"""
        self.sld_dist.blockSignals(True)   # 屏蔽滑块信号
        self.sld_dist.setValue(value)      # 同步滑块 = 数字框值
        self.sld_dist.blockSignals(False)  # 恢复信号
        self.calculate_array()

    # =====================================================================
    # 六-5. 单通道测试模式
    # =====================================================================
    def toggle_test_mode(self):
        """勾选/取消"单通道测试"时执行。测试模式下，只让选中的那一路出声
        （幅度 255），其余全部静音（幅度 0），用来逐路检查硬件好坏。"""
        is_test = self.chk_test_mode.isChecked()   # 现在是否勾选了
        self.spn_test_ch.setEnabled(is_test)       # 勾选后才允许选通道号

        if is_test:
            # 开启测试时，强制关闭自动扫描（两者不能同时开），并禁用参数面板
            self.chk_auto_sweep.setChecked(False)  # 强制取消勾选自动扫描
            self.grp_ctrl.setEnabled(False)        # 参数区变灰不可操作
            self.update_test_state()               # 立即按当前通道刷新
        else:
            self.grp_ctrl.setEnabled(True)         # 恢复参数区
            self.calculate_array()                 # 恢复正常计算

    def update_test_state(self):
        """测试模式下，选中的测试通道变化时调用：只点亮那一路。"""
        if not self.chk_test_mode.isChecked(): return   # 没在测试模式就直接返回
        target_ch = self.spn_test_ch.value()            # 当前选中的通道号
        # 列表推导式：第 target_ch 个元素=255，其余全=0
        self.current_amps = [255 if i == target_ch else 0 for i in range(CHANNEL_COUNT)]
        self.current_phases = [0] * CHANNEL_COUNT       # 相位全部归零
        self.refresh_array_labels()                     # 刷新界面上的 60 个格子
        if self.chk_auto_send.isChecked(): self.auto_timer.start(120)  # 若开了自动同步则防抖发送

    # ==========================================
    # 六-6. 自动扫描模式逻辑
    # ==========================================
    def toggle_auto_sweep(self):
        """勾选/取消"自动扫描"时执行：让波束自动左右来回扫。"""
        if self.chk_auto_sweep.isChecked():
            # 1. 强制切换到 3.5次方物理法向加权模式（扫描时用实时计算模式）
            self.cmb_amp.setCurrentText(MODE_UNIT_COSINE)
            # 2. 强制开启参数改变自动同步 FPGA，保证每一帧都下发
            self.chk_auto_send.setChecked(True)
            # 3. 禁用单通道测试以防干扰
            self.chk_test_mode.setChecked(False)
            self.grp_test.setEnabled(False)

            # 确定初始扫描方向：如果当前角度已经在最右边就向左扫，反之向右
            if self.sld_az.value() >= 30:
                self.sweep_direction = -1
            elif self.sld_az.value() <= -30:
                self.sweep_direction = 1

            # 启动 1s 定时器（每秒触发一次 handle_auto_sweep）
            self.sweep_timer.start(1000)
            self.log("▶ 已开启自动扫描模式 (1s间隔, 2°步进)", "#FF9800")
        else:
            # 取消勾选：停止定时器、恢复测试模块、记日志
            self.sweep_timer.stop()
            self.grp_test.setEnabled(True)
            self.log("⏹ 已关闭自动扫描模式", "#FFFFFF")

    def handle_auto_sweep(self):
        """定时器每秒调用一次：把水平角移动 2°，到边界就反向。"""
        # 提取当前水平角，加上方向步进值（direction 为 1 则 +2，-1 则 -2）
        curr_az = self.sld_az.value()
        next_az = curr_az + (2 * self.sweep_direction)

        # 边界检测与方向翻转：到了 ±30° 就掉头
        if next_az >= 30:
            next_az = 30            # 顶到最右边
            self.sweep_direction = -1   # 改向左扫
        elif next_az <= -30:
            next_az = -30           # 顶到最左边
            self.sweep_direction = 1    # 改向右扫

        # 设置滑块新值。注意：setValue 会自动触发 valueChanged 信号，
        # 进而自动调用 calculate_array → 计算 → 发送串口包（整条链路自动跑通）
        self.sld_az.setValue(next_az)

    # ==========================================
    # 六-7. N60 空间聚焦与幅度模式解耦计算（核心算法）
    # ==========================================
    def calculate_array(self):
        """根据界面上的 距离/角度/模式，算出 60 路各自的相位和幅度。

        这是整个程序的"大脑"：所有滑块一变化都会跑到这里重新计算。
        """
        if self.chk_test_mode.isChecked(): return   # 测试模式下不计算，直接返回

        # ---- 1. 角度超限压缩过滤 ----
        # 调用前面写的限幅函数，拿到压缩后的方向向量和真实角度
        sx, sy, sz, actual_az, actual_el, combined_angle = limit_direction_n60(
            self.sld_az.value(), self.sld_el.value()
        )
        distance_mm = self.sld_dist.value()      # 目标距离（毫米）
        distance_m = distance_mm / 1000.0        # 换算成米
        # 目标点三维坐标 = 距离 × 单位方向向量（米）
        target_m = (distance_m * sx, distance_m * sy, distance_m * sz)

        # 获取当前选择的幅度模式
        current_mode = self.cmb_amp.currentText()
        opt_amps = None                          # 先假设不用查表
        if current_mode == MODE_OPTIMIZED_DBC:
            # 如果是"离线优化表"模式，就去查 CSV 拿 60 个幅度
            opt_amps = load_optimized_table(distance_mm, actual_az)

        # ---- 2. 逐通道全空间近场声程结算与独立幅度分配 ----
        # 对 60 个通道逐一计算
        for ch in range(CHANNEL_COUNT):
            mx, my, mz = self.coords_3d[ch]      # 该阵元的坐标（毫米）

            # --- [A] 相位计算 ---
            # 相位（延迟）的本质：声波从目标点传到每个阵元的路程不一样，
            # 远的阵元声音先到（相位超前），近的阵元声音后到（相位落后）。
            # 要让 60 路信号"同时到达目标点"，就得给近的阵元多延迟、远的少延迟。
            # 注意这里坐标单位是毫米，要先除以 1000 换成米，再算三维距离。
            path_m = math.sqrt((target_m[0] - mx/1000.0)**2 + (target_m[1] - my/1000.0)**2 + (target_m[2] - mz/1000.0)**2)
            # 声程差 ÷ 声速 = 时间差（秒）；时间差 × 载波频率 = 相差多少个"波长周期"。
            # 公式：相位周期数 = (实际路程 - 参考距离) × 频率 / 声速
            phase_cycles = (path_m - distance_m) * CARRIER_HZ / SOUND_SPEED_M_S
            # % 1.0 取小数部分：相位差超过一个完整周期就"折回"（周期是循环的）；
            # × PWM_PERIOD_TICKS 把小数周期换算成 FPGA 的 PWM 计数（0~2499）；
            # round() 四舍五入成整数，再 % PWM_PERIOD_TICKS 保险防越界。
            self.current_phases[ch] = int(round((phase_cycles % 1.0) * PWM_PERIOD_TICKS)) % PWM_PERIOD_TICKS

            # --- [B] 幅度计算：严格隔离的三种理论模型 ---
            final_amp = 1.0                      # 先默认幅度 = 1（不衰减）

            if current_mode == MODE_UNIT_COSINE:
                # 模式1：物理法向 3.5 次方加权（实时计算）
                # 和 generate_n60_csv.py 里的算法完全一样：
                # 阵元"法向量"和"阵元→目标方向"的点积，决定这个阵元该给多大衰减。
                unit_id = ch // 12               # 通道 → 子阵编号
                theta_rad = math.radians(UNIT_ANGLES_DEG[unit_id])
                nx = -math.sin(theta_rad)        # 阵元法向量（水平分量）
                ny = 0.0
                nz = math.cos(theta_rad)         # 阵元法向量（前后分量）
                # 阵元 → 目标的向量（米）
                vx = target_m[0] - mx/1000.0
                vy = target_m[1] - my/1000.0
                vz = target_m[2] - mz/1000.0
                v_len = math.sqrt(vx**2 + vy**2 + vz**2)   # 向量长度 = 距离
                if v_len > 0:
                    vx, vy, vz = vx/v_len, vy/v_len, vz/v_len  # 归一化成单位向量
                    dot_product = vx*nx + vy*ny + vz*nz        # 点积 = 夹角余弦
                    # 依据 HY40A16T12-1 实测参数 (-6dB@35deg) 修正的 3.5 次方衰减模型
                    final_amp = max(0.0, dot_product) ** 3.5
                else:
                    final_amp = 1.0
            elif current_mode == MODE_OPTIMIZED_DBC:
                # 模式2：直接查离线优化表
                final_amp = opt_amps[ch] if opt_amps else 1.0   # 表里有就用表里的，没有就 1
            elif current_mode == MODE_UNIFORM:
                # 模式3：全通（幅度恒为 1，只测总功率）
                final_amp = 1.0

            # 把 0.0~1.0 的小数幅度换算成 FPGA 要的 0~255 整数：
            #   max/min 夹紧范围，×255 放大，round 四舍五入，int 转整数
            self.current_amps[ch] = int(round(max(0.0, min(1.0, final_amp)) * 255.0))

        # ---- 3. 更新前端状态描述（界面文字） ----
        self.lbl_az.setText("水平角 (Azimuth): {}°".format(self.sld_az.value()))
        self.lbl_el.setText("俯仰角 (Elevation): {}°".format(self.sld_el.value()))
        self.lbl_dist.setText("焦距 (Distance): {:.3f} 米".format(distance_m))  # {:.3f}=保留3位小数

        # 判断是否发生了角度限幅（用户要求的角度和实际角度差超过 0.05° 就算）
        limited = abs(actual_az - self.sld_az.value()) > 0.05 or abs(actual_el - self.sld_el.value()) > 0.05
        if limited:
            # 触发限幅：显示警告，把压缩后的实际角度亮出来
            self.lbl_limited.setText(f"触发角度限幅: 水平={actual_az:.1f}°, 俯仰={actual_el:.1f}°, 综合偏转={combined_angle:.1f}°")
        else:
            self.lbl_limited.setText(f"当前综合偏转角: {combined_angle:.2f}°")

        # 刷新界面上的 60 个阵元格子显示
        self.refresh_array_labels()
        # 如果开了"自动同步"，启动 120ms 防抖定时器，稍后自动发串口包
        if self.chk_auto_send.isChecked(): self.auto_timer.start(120)

    # =====================================================================
    # 六-8. 刷新阵列图
    # =====================================================================
    def refresh_array_labels(self):
        """把 current_amps / current_phases 画到界面的 60 个格子上，
        并根据幅度大小调整格子亮度和颜色（幅度大 = 更亮更蓝）。"""
        for ch in range(CHANNEL_COUNT):
            unit_id = ch // 12        # 子阵编号（用于显示 U0~U4）
            elem_id = ch % 12         # 子阵内编号（用于显示 E0~E11）。% 是取余数
            amp = self.current_amps[ch]      # 这路当前的幅度
            phase = self.current_phases[ch]  # 这路当前的相位
            label = self.transducer_labels[ch]  # 对应的界面标签

            # 格子文字：U0E3 / CH:03 / 幅度:255 / 相位:0123
            # {ch:02d} = 数字补两位，{amp:03d} = 补三位，{phase:04d} = 补四位
            label.setText(f"U{unit_id}E{elem_id}\nCH:{ch:02d}\n幅度:{amp:03d}\n相位:{phase:04d}")

            # 亮度：幅度夹在 20~220 之间，防止太暗看不清或太亮刺眼
            intensity = max(20, min(220, amp))
            if amp == 0:
                # 幅度为 0（静音）：格子显示暗色
                color = "rgba(0, 0, 0, 0.45)"
                border = "rgba(255, 255, 255, 0.1)"
            elif phase == 0 and self.chk_test_mode.isChecked():
                # 测试模式 + 相位为 0：格子显示橙色（表示"正在被测试"）
                color = "rgba(255, 87, 34, 0.85)"
                border = "#FF5722"
            else:
                # 正常情况：青色，透明度随幅度变大而变浓
                color = "rgba(0, 229, 255, {:.2f})".format(0.10 + 0.45 * intensity / 255.0)
                border = "rgba(0, 229, 255, 0.45)"

            # 套用背景色/边框/圆角/白字
            label.setStyleSheet(f"background-color: {color}; border: 1px solid {border}; border-radius: 6px; color: #FFFFFF;")

    # ==========================================
    # 六-9. 强制套用 0x01 指令码进行 FPGA 打包
    # ==========================================
    def make_packet(self):
        """把 60 路幅度 + 60 路相位打包成一串二进制数据帧。

        帧格式（和 FPGA 固件约定的协议）：
          帧头 2 字节 : 0xAA 0xBB（固定，用来让 FPGA 认出"这是给我的数据"）
          指令码 1 字节: 0x01（固定，表示"更新参数"这个命令）
          60 个幅度    : 每路 1 字节（0~255）
          60 个相位    : 每路 2 字节（0~2499，小端序）
          校验和 1 字节: 帧头之后所有字节求和，取低 8 位（用来检查数据有没有传错）
          帧尾 2 字节 : 0x0D 0x0A（回车换行，表示"数据结束"）
        """
        # bytearray：可变的字节数组（和列表类似，但里面存的是 0~255 的字节）
        packet = bytearray([0xAA, 0xBB, 0x01])   # 开头：帧头 + 指令码
        # 先追加 60 个幅度字节。int(max(0, min(255, amp))) 夹紧范围，
        # & 0xFF 是位运算"按位与"，保证只取低 8 位（0~255）
        for amp in self.current_amps:
            packet.append(int(max(0, min(255, amp))) & 0xFF)
        # 再追加 60 个相位，每个 2 字节：
        # struct.pack("<H", 数字) 把整数打包成 2 字节二进制，
        # "<" 表示小端序（低字节在前，Intel 电脑和常见单片机都是小端），"H" 表示无符号 2 字节整数。
        for phase in self.current_phases:
            packet.extend(struct.pack("<H", int(phase) % PWM_PERIOD_TICKS))
        # 校验和：从索引 2（跳过帧头 0xAA 0xBB）开始全部字节求和，& 0xFF 取低 8 位
        packet.append(sum(packet[2:]) & 0xFF)
        # 帧尾：回车 0x0D + 换行 0x0A
        packet.extend([0x0D, 0x0A])
        # bytes(packet) 把可变字节数组转成不可变的 bytes 类型返回（串口 write 需要它）
        return bytes(packet)

    def send_to_fpga(self):
        """把当前参数打包并发给 FPGA，同时把发送详情写进日志。"""
        packet = self.make_packet()                       # 打包
        ok, msg = self.logic.send(packet)                 # 发送
        if ok:
            # 扫描模式或测试模式打上不同颜色的标签便于观察
            if self.chk_auto_sweep.isChecked():
                color = "#FF9800"        # 自动扫描：橙色
                tag = "[AUTO SWEEP] "
            elif self.chk_test_mode.isChecked():
                color = "#FF5722"        # 测试模式：红色
                tag = "[TEST MODE] "
            else:
                color = "#00E5FF"        # 正常：青色
                tag = ""

            # 日志里显示：帧总字节数 + 前 12 字节十六进制 + 后 4 字节十六进制。
            # " ".join(生成器) 把每字节转成 "AA" "BB" 这种两位十六进制再空格连起来；
            # f"{b:02X}" 表示把数字 b 格式化成两位大写十六进制。
            # <br> 是 HTML 换行（QTextEdit 支持富文本）。
            self.log(f"{tag}成功下发 N60 帧 [{len(packet)} 字节]<br>" +
                     " ".join(f"{b:02X}" for b in packet[:12]) + " ... " +
                     " ".join(f"{b:02X}" for b in packet[-4:]), color)
        else:
            self.log("发送失败: {}".format(msg), "red")   # 失败记红字

    def log(self, text, color="#FFFFFF"):
        """往日志框里追加一行带时间戳、带颜色的文字。"""
        # datetime.now() 拿当前时间；strftime 格式化；[:-3] 去掉末尾 3 位（只留毫秒前 3 位）
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # append 是"追加"；<span style='color:...'> 是 HTML 颜色标签，让文字变色
        self.txt_log.append("<span style='color:{};'>[{}] {}</span>".format(color, ts, text))


# ==============================================================================
# 七、程序入口（直接运行本文件时从这里开始）
# ==============================================================================
# if __name__ == "__main__": 的含义见 generate_n60_csv.py 末尾的讲解：
# 只有"直接运行本文件"时才执行，被 import 时不执行。
if __name__ == "__main__":
    # QApplication(sys.argv)：创建 GUI 程序的总管理员。每个 PyQt 程序必须有且仅有一个。
    app = QApplication(sys.argv)

    # 加载背景图 bg.jpg：把样式表里的占位文字 "bg.jpg" 替换成真实路径。
    # .replace("\\", "/") 把 Windows 的反斜杠路径统一换成正斜杠（Qt 更认正斜杠）。
    bg_path = resource_path("bg.jpg").replace("\\", "/")
    app.setStyleSheet(STYLESHEET.replace("bg.jpg", bg_path))

    # 创建主窗口实例
    win = PhasedArrayWindow()
    win.show()                  # 显示窗口

    # app.exec()：进入 Qt 的"事件循环"——程序在这里一直转圈，
    # 等待用户点击/拖动等事件并响应，直到用户关掉窗口才结束。
    # sys.exit(...) 把退出码传给操作系统（0 = 正常退出）。
    sys.exit(app.exec())
