# -*- coding: utf-8 -*-
import threading
import serial
import time
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# 设置 Matplotlib 后端
matplotlib.use('Agg')

# -------------------------- 样式配置 --------------------------
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# -------------------------- 全局数据 --------------------------
data = []
data2 = []
data3 = []
old_data = []
delta_data = []


# -------------------------- 核心代码 EEGThread  --------------------------
class EEGThread(threading.Thread):

    def __init__(self, parent=None):
        super(EEGThread, self).__init__(parent)
        self.filename = 'jox.txt'
        # 请在此处将COM修改为实际脑电设备串口号
        self.com = "COM4"
        self.bps = 57600
        self.vaul = []
        self.is_open = False
        self.is_close = True

    def checkList(self, list, num):
        list_num = 0
        for i in list:
            if i > num:
                list_num += 1
        return list_num

    def checkEeg(self):
        old_num = 0
        delta_num = 0
        for old in old_data:
            if self.checkList(old, 200) > 5:
                old_num += 1

        delta_num = self.checkList(delta_data, 50000)

        if old_num > 3 and delta_num > 4:
            return True
        else:
            return False

    def run(self):
        global data, data2, data3, old_data, delta_data
        try:
            t = serial.Serial(self.com, self.bps)
            b = t.read(3)
            print(str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))) + "脑电波设备配对中")
            while b[0] != 170 or b[1] != 170 \
                    or b[2] != 4:
                b = t.read(3)

            if b[0] == b[1] == 170 and b[2] == 4:
                print(str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))) + "配对成功。")
                a = b + t.read(5)

                if a[0] == 170 and a[1] == 170 and a[2] == 4 and a[3] == 128 and a[4] == 2:
                    while 1:
                        try:
                            a = t.read(8)  # 读取EEG数据
                            sum = ((0x80 + 0x02 + a[5] + a[6]) ^ 0xffffffff) & 0xff
                            if a[0] == a[1] == 170 and a[2] == 32:  # 大包
                                y = 1
                            else:
                                y = 0
                            if a[0] == 170 and a[1] == 170 and a[2] == 4 and a[3] == 128 and a[4] == 2:  # 小包
                                p = 1
                            else:
                                p = 0
                            if sum != a[7] and y != 1 and p != 1:
                                b = t.read(3)
                                c = b[0]
                                d = b[1]
                                e = b[2]
                                while c != 170 or d != 170 or e != 4:
                                    c = d
                                    d = e
                                    e = t.read()

                                    if c == (b'\xaa' or 170) and d == (b'\xaa' or 170) and e == b'\x04':
                                        g = t.read(5)
                                        if c == b'\xaa' and d == b'\xaa' and e == b'\x04' and g[0] == 128 and g[1] == 2:
                                            a = t.read(8)
                                            break

                            if a[0] == 170 and a[1] == 170 and a[2] == 4 and a[3] == 128 and a[4] == 2:  # 小包

                                high = a[5]
                                low = a[6]
                                rawdata = (high << 8) | low
                                if rawdata > 32768:
                                    rawdata = rawdata - 65536
                                sum = ((0x80 + 0x02 + high + low) ^ 0xffffffff) & 0xff
                                if sum == a[7]:
                                    self.vaul.append(rawdata)
                                if sum != a[7]:
                                    b = t.read(3)
                                    c = b[0]
                                    d = b[1]
                                    e = b[2]
                                    while c != 170 or d != 170 or e != 4:
                                        c = d
                                        d = e
                                        e = t.read()
                                        if c == b'\xaa' and d == b'\xaa' and e == b'\x04':
                                            g = t.read(5)
                                            if c == b'\xaa' and d == b'\xaa' and e == b'\x04' and g[0] == 128 and g[
                                                1] == 2:
                                                a = t.read(8)
                                                break
                            if a[0] == a[1] == 170 and a[2] == 32:
                                c = a + t.read(28)
                                delta = (c[7] << 16) | (c[8] << 8) | (c[9])
                                # print(delta)

                                data = self.vaul

                                old_data.append(data)
                                if len(old_data) > 10:
                                    old_data = old_data[-10:]

                                delta_data.append(delta)
                                if len(delta_data) > 10:
                                    delta_data = delta_data[-10:]

                                flag = self.checkEeg()
                                data2.append(c[32])

                                if len(data2) > 20:
                                    data2 = data2[-20:]

                                data3.append(c[34])

                                if len(data3) > 20:
                                    data3 = data3[-20:]

                                self.vaul = []
                        except Exception as e:
                            sse = 1
        except Exception as e:
            sse = 1


# -------------------------- Streamlit 界面优化 (亮色版) --------------------------

st.set_page_config(
    page_title="脑电波实时监测系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 强制亮色模式 CSS
st.markdown("""
    <style>
    /* 强制背景为白色，文字为黑色 */
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    /* 侧边栏背景调整为浅灰 */
    [data-testid="stSidebar"] {
        background-color: #F0F2F6;
    }
    /* 调整 Metric 卡片的样式 */
    div[data-testid="stMetricValue"] {
        color: #333333;
    }
    </style>
""", unsafe_allow_html=True)

# ---- 侧边栏 ----
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/brain--v1.png", width=80)
    st.title("监测控制台")
    st.markdown("---")

    # 状态指示灯
    status_placeholder = st.empty()
    status_placeholder.info("⏳ 等待线程启动...")

    st.markdown("### 系统设置")
    run_monitoring = st.toggle("开启实时数据流", value=True)
    refresh_rate = st.slider("刷新频率 (秒)", 0.1, 1.0, 0.2)


# ---- 主界面标题 ----
st.title("🧠 单通道睡眠监测与闭环调控系统")
st.markdown("通过串口实时获取并分析 EEG 信号，展示专注度与放松度趋势。")
st.markdown("---")


# ---- 线程管理 ----
@st.cache_resource
def start_eeg_thread():
    thread = EEGThread()
    thread.daemon = True
    thread.start()
    return thread


try:
    eeg_thread = start_eeg_thread()
    # 更新侧边栏状态
    status_placeholder.success(f"✅ 设备已连接 ({eeg_thread.com})")
except Exception as e:
    status_placeholder.error(f"❌ 连接失败: {e}")

# ---- 仪表盘区域 (Metrics) ----
m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    metric_focus = st.empty()
with m_col2:
    metric_relax = st.empty()
with m_col3:
    metric_raw = st.empty()

st.markdown("### 📊 实时趋势分析")

# ---- 绘图区域布局 ----
plot_col1, plot_col2 = st.columns(2)

with plot_col1:
    plot_placeholder_1 = st.empty()

with plot_col2:
    plot_placeholder_2 = st.empty()

# -------------------------- 实时循环逻辑 --------------------------
if run_monitoring:
    while True:
        # 获取数据快照
        current_data = list(data)
        current_data2 = list(data2)  # 放松值
        current_data3 = list(data3)  # 专注值

        # 1. 更新顶部指标 (Metrics)
        last_relax = current_data2[-1] if current_data2 else 0
        last_focus = current_data3[-1] if current_data3 else 0
        last_raw_len = len(current_data)

        delta_relax = last_relax - current_data2[-2] if len(current_data2) > 1 else 0
        delta_focus = last_focus - current_data3[-2] if len(current_data3) > 1 else 0

        metric_relax.metric(label="当前放松指数", value=f"{last_relax}", delta=f"{delta_relax}")
        metric_focus.metric(label="当前专注指数", value=f"{last_focus}", delta=f"{delta_focus}")
        metric_raw.metric(label="捕捉数据点总数", value=f"{last_raw_len}", delta="实时")

        # 2. 绘图区域 1：专注值与放松值
        # 强制白色背景
        fig1, ax1 = plt.subplots(figsize=(6, 3.5), facecolor='white')

        # 文字强制为黑色
        ax1.set_title("专注/放松指数趋势", fontsize=12, color='black', fontweight='bold')

        # 优化线条样式
        ax1.plot(current_data2, color='#28a745', label="放松值", linewidth=2.5, alpha=0.9)  # 绿色
        ax1.plot(current_data3, color='#007bff', label="专注值", linewidth=2.5, alpha=0.9)  # 蓝色

        # 填充线下区域
        if len(current_data2) > 0:
            ax1.fill_between(range(len(current_data2)), current_data2, color='#28a745', alpha=0.1)
        if len(current_data3) > 0:
            ax1.fill_between(range(len(current_data3)), current_data3, color='#007bff', alpha=0.1)

        # 调整坐标轴颜色
        ax1.tick_params(axis='x', colors='black')
        ax1.tick_params(axis='y', colors='black')
        ax1.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9)
        ax1.grid(True, linestyle='--', alpha=0.3, color='#aaaaaa')

        plot_placeholder_1.pyplot(fig1, use_container_width=True)
        plt.close(fig1)

        # 3. 绘图区域 2：脑电波原始值
        fig2, ax2 = plt.subplots(figsize=(6, 3.5), facecolor='white')

        ax2.set_title("原始脑电波", fontsize=12, color='black', fontweight='bold')

        display_data = current_data[-200:] if len(current_data) > 200 else current_data

        # 使用深黄色/橙色显示原始波形，在白底上更清晰
        ax2.plot(display_data, color='#d68910', linewidth=1.2)

        ax2.tick_params(axis='x', colors='black')
        ax2.tick_params(axis='y', colors='black')
        ax2.grid(True, linestyle='--', alpha=0.3, color='#aaaaaa')

        plot_placeholder_2.pyplot(fig2, use_container_width=True)
        plt.close(fig2)

        time.sleep(refresh_rate)

else:
    st.warning("⚠️ 监控已暂停。请在侧边栏开启实时数据流。")