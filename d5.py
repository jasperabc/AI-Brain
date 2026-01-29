# -*- coding: utf-8 -*-
import threading
import serial
import time
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from scipy import signal
from datetime import datetime, timedelta

# 设置 Matplotlib 后端
matplotlib.use('Agg')

# -------------------------- 全局配置 --------------------------
# 样式配置（保持原样）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['grid.linewidth'] = 0.8
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['figure.titlesize'] = 14
plt.rcParams['legend.fontsize'] = 9

# 核心参数配置
EPOCH_DURATION = 30
FS = 256
BANDS = {
    'Delta': (0.5, 4),
    'Theta': (4, 8),
    'Alpha': (8, 13),
    'Spindle': (12, 14)
}


# -------------------------- 核心代码 EEGThread  --------------------------
class EEGThread(threading.Thread):
    def __init__(self, parent=None):
        super(EEGThread, self).__init__(parent)
        self.filename = 'jox.txt'
        self.com = "COM3"  # 请修改为实际设备串口号
        self.bps = 57600
        self.is_open = False
        self.is_close = True

        # 【关键修复】将全局数据移动到线程内部，这样刷新页面数据不会丢
        self.data = []
        self.data2 = []
        self.data3 = []
        self.old_data = []
        self.delta_data = []
        self.epochs = []
        self.current_epoch = {
            'start_time': None,
            'raw_data': [],
            'relax_data': [],
            'focus_data': [],
            'timestamps': []
        }
        self.vaul = []
        self.is_collecting = True  # 线程内部的采集开关

    def checkList(self, list_obj, num):
        list_num = 0
        for i in list_obj:
            if i > num:
                list_num += 1
        return list_num

    def checkEeg(self):
        old_num = 0
        delta_num = 0
        for old in self.old_data:
            if self.checkList(old, 200) > 5:
                old_num += 1
        delta_num = self.checkList(self.delta_data, 50000)
        return old_num > 3 and delta_num > 4

    def _calculate_psd(self, eeg_data):
        eeg_array = np.array(eeg_data)
        if eeg_array.size == 0 or len(eeg_array) < 256:
            return {band: 0 for band in BANDS.keys()}
        f, psd = signal.welch(
            eeg_array, fs=FS, window='hann',
            nperseg=256, noverlap=128, scaling='density'
        )
        psd = np.asarray(psd)
        band_energies = {}
        for band_name, (low, high) in BANDS.items():
            mask = (f >= low) & (f <= high)
            band_energies[band_name] = np.sum(psd[mask])
        return band_energies

    def run(self):
        # 移除 global 声明，全部使用 self.xxx
        try:
            t = serial.Serial(self.com, self.bps)
            b = t.read(3)
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 脑电波设备配对中")

            while b[0] != 170 or b[1] != 170 or b[2] != 4:
                b = t.read(3)

            if b[0] == b[1] == 170 and b[2] == 4:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 配对成功")
                a = b + t.read(5)

                if a[0] == 170 and a[1] == 170 and a[2] == 4 and a[3] == 128 and a[4] == 2:
                    while 1:
                        # 使用 self.is_collecting 控制
                        if not self.is_collecting:
                            time.sleep(0.1)
                            continue

                        try:
                            a = t.read(8)
                            sum_val = ((0x80 + 0x02 + a[5] + a[6]) ^ 0xffffffff) & 0xff
                            y = 1 if (a[0] == a[1] == 170 and a[2] == 32) else 0
                            p = 1 if (a[0] == 170 and a[1] == 170 and a[2] == 4 and a[3] == 128 and a[4] == 2) else 0

                            if sum_val != a[7] and y != 1 and p != 1:
                                b = t.read(3)
                                c, d, e = b[0], b[1], b[2]
                                while c != 170 or d != 170 or e != 4:
                                    c, d = d, e
                                    e = ord(t.read())
                                    if c == (b'\xaa' or 170) and d == (b'\xaa' or 170) and e == b'\x04':
                                        g = t.read(5)
                                        if c == b'\xaa' and d == b'\xaa' and e == b'\x04' and g[0] == 128 and g[1] == 2:
                                            a = t.read(8)
                                            break

                            if a[0] == 170 and a[1] == 170 and a[2] == 4 and a[3] == 128 and a[4] == 2:
                                high = a[5]
                                low = a[6]
                                rawdata = (high << 8) | low
                                if rawdata > 32768:
                                    rawdata -= 65536
                                sum_val = ((0x80 + 0x02 + high + low) ^ 0xffffffff) & 0xff
                                if sum_val == a[7]:
                                    self.vaul.append(rawdata)
                                else:
                                    b = t.read(3)
                                    c, d, e = b[0], b[1], b[2]
                                    while c != 170 or d != 170 or e != 4:
                                        c, d = d, e
                                        e = ord(t.read())
                                        if c == b'\xaa' and d == b'\xaa' and e == b'\x04':
                                            g = t.read(5)
                                            if c == b'\xaa' and d == b'\xaa' and e == b'\x04' and g[0] == 128 and g[
                                                1] == 2:
                                                a = t.read(8)
                                                break

                            if a[0] == a[1] == 170 and a[2] == 32:
                                c = a + t.read(28)
                                delta = (c[7] << 16) | (c[8] << 8) | c[9]
                                current_time = datetime.now()

                                # 修改：使用 self.xxx 更新数据
                                self.data = self.vaul
                                self.old_data.append(self.data)
                                if len(self.old_data) > 10:
                                    self.old_data = self.old_data[-10:]

                                self.delta_data.append(delta)
                                if len(self.delta_data) > 10:
                                    self.delta_data = self.delta_data[-10:]

                                self.data2.append(c[32])
                                if len(self.data2) > 20:
                                    self.data2 = self.data2[-20:]

                                self.data3.append(c[34])
                                if len(self.data3) > 20:
                                    self.data3 = self.data3[-20:]

                                # 初始化当前Epoch
                                if self.current_epoch['start_time'] is None:
                                    self.current_epoch['start_time'] = current_time

                                # 填充当前Epoch数据
                                self.current_epoch['raw_data'].extend(self.vaul)
                                self.current_epoch['relax_data'].append(c[32])
                                self.current_epoch['focus_data'].append(c[34])
                                self.current_epoch['timestamps'].append(current_time)

                                # 检查是否达到30秒Epoch
                                time_diff = (current_time - self.current_epoch['start_time']).total_seconds()
                                if time_diff >= EPOCH_DURATION:
                                    psd_data = self._calculate_psd(self.current_epoch['raw_data'])
                                    self.epochs.append({
                                        'start': self.current_epoch['start_time'],
                                        'end': current_time,
                                        'raw': self.current_epoch['raw_data'].copy(),
                                        'relax': self.current_epoch['relax_data'].copy(),
                                        'focus': self.current_epoch['focus_data'].copy(),
                                        'timestamps': self.current_epoch['timestamps'].copy(),
                                        'psd': psd_data
                                    })
                                    if len(self.epochs) > 100:
                                        self.epochs.pop(0)
                                    self.current_epoch = {
                                        'start_time': None,
                                        'raw_data': [],
                                        'relax_data': [],
                                        'focus_data': [],
                                        'timestamps': []
                                    }

                                self.vaul = []
                        except Exception as e:
                            continue
        except Exception as e:
            print(f"设备连接异常: {e}")


# -------------------------- Streamlit 界面 --------------------------
st.set_page_config(page_title="脑电波实时监测系统", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

# 样式优化（保持原样）
st.markdown("""
    <style>
    .stApp {background-color: #FFFFFF; color: #2C3E50;}
    [data-testid="stSidebar"] {background-color: #F8F9FA;}
    button {border-radius: 8px !important; font-weight: 500 !important;}
    div[data-testid="stMetricValue"] {font-size: 1.5rem !important; font-weight: 600 !important;}
    div[data-testid="stMetricLabel"] {color: #6C757D !important;}
    h1, h2, h3 {color: #2C3E50 !important;}
    .plot-container {border: 1px solid #E9ECEF; border-radius: 8px; padding: 10px;}
    </style>
""", unsafe_allow_html=True)

# 【关键修复】使用 Session State 管理状态
if 'is_collecting' not in st.session_state:
    st.session_state.is_collecting = True
if 'playback_mode' not in st.session_state:
    st.session_state.playback_mode = False


# ---- 启动线程 ----
@st.cache_resource
def start_eeg_thread():
    thread = EEGThread()
    thread.daemon = True
    thread.start()
    return thread


# 获取线程实例（这个实例在缓存中，所以数据不会丢）
try:
    eeg_thread = start_eeg_thread()
    # 同步状态：将界面上的开关状态传给线程
    eeg_thread.is_collecting = st.session_state.is_collecting
except Exception as e:
    st.error(f"❌ 连接失败：{str(e)}")
    eeg_thread = None

# ---- 侧边栏：控制中心 ----
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/brain--v1.png", width=80)
    st.title("🧠 监测控制台")
    st.markdown("---")

    status_placeholder = st.empty()
    if eeg_thread:
        if st.session_state.is_collecting:
            status_placeholder.success(f"✅ 设备已连接 ({eeg_thread.com}) - 采集中")
        else:
            status_placeholder.warning(f"⏸️ 设备已连接 ({eeg_thread.com}) - 已暂停")
    else:
        status_placeholder.info("⏳ 等待设备连接...")

    # 采集控制
    st.markdown("### 🎛️ 采集控制")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶️ 开始采集", width='stretch', type="primary"):
            st.session_state.is_collecting = True
            st.rerun()
    with col_btn2:
        if st.button("⏸️ 暂停采集", width='stretch'):
            st.session_state.is_collecting = False
            st.rerun()

    # 回放控制
    st.markdown("### 📼 历史回放")
    # 使用 session_state 记住复选框状态
    playback_check = st.checkbox("开启回放模式", value=st.session_state.playback_mode)
    if playback_check != st.session_state.playback_mode:
        st.session_state.playback_mode = playback_check
        st.rerun()

    # 从线程获取数据长度
    epoch_count = len(eeg_thread.epochs) if eeg_thread else 0
    st.caption(f"当前历史数据段数：{epoch_count}")

    current_playback_idx = 0
    if st.session_state.playback_mode and epoch_count > 0:
        current_playback_idx = st.slider(
            "选择历史时段（30秒/段）",
            min_value=0,
            max_value=epoch_count - 1,
            value=0,
            format="第 %d 段"
        )
        selected_epoch = eeg_thread.epochs[current_playback_idx]
        st.caption(
            f"时间范围：{selected_epoch['start'].strftime('%H:%M:%S')} - {selected_epoch['end'].strftime('%H:%M:%S')}")

    st.markdown("### ⚙️ 系统设置")
    refresh_rate = st.slider("刷新频率 (秒)", 0.1, 1.0, 0.2)
    run_monitoring = st.toggle("开启实时监测", value=True)

# ---- 主界面标题 ----
st.title("🧠 单通道睡眠监测与闭环调控系统")
st.markdown("通过串口实时获取并分析 EEG 信号，展示专注度与放松度趋势、PSD 功率谱及频段能量。")
st.markdown("---")

# ---- 顶部指标卡片 ----
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: metric_relax = st.empty()
with col_m2: metric_focus = st.empty()
with col_m3: metric_epoch = st.empty()
with col_m4: metric_alpha = st.empty()

# ---- 绘图区域 ----
st.markdown("### 📊 实时数据展示（30秒/帧）")
col_plot1, col_plot2 = st.columns(2)
st.markdown("### 📈 功率谱密度分析")
col_plot3, col_plot4 = st.columns([0.8, 0.2])

with col_plot1: plot_placeholder1 = st.empty()
with col_plot2: plot_placeholder2 = st.empty()
with col_plot3: plot_placeholder3 = st.empty()
with col_plot4:
    st.markdown("#### 📝 频段说明")
    st.write("""
    - **Delta (0.5-4Hz)**：深度睡眠
    - **Theta (4-8Hz)**：浅睡眠/冥想
    - **Alpha (8-13Hz)**：放松清醒
    - **Spindle (12-14Hz)**：睡眠纺锤波
    """)
    st.markdown("#### 📏 单位说明")
    st.write("""
    - 幅值：微伏 (µV)
    - 功率谱密度：µV²/Hz
    """)


# -------------------------- 核心逻辑：数据展示与循环 --------------------------
def draw_charts():
    """封装绘图逻辑，保证暂停时也能调用"""
    if not eeg_thread:
        return

    # 获取数据源 (从线程中读取)
    if st.session_state.playback_mode and len(eeg_thread.epochs) > 0:
        epoch = eeg_thread.epochs[current_playback_idx]
        raw_data = epoch['raw']
        relax_data = epoch['relax']
        focus_data = epoch['focus']
        timestamps = epoch['timestamps']
        start_time = epoch['start']
        end_time = epoch['end']
        psd_data = epoch['psd']
        # 回放模式下，时间是完整的30秒
        current_duration = EPOCH_DURATION
    else:
        # 实时模式：使用线程中的 current_epoch
        curr = eeg_thread.current_epoch
        raw_data = curr['raw_data']
        relax_data = curr['relax_data']
        focus_data = curr['focus_data']
        timestamps = curr['timestamps']

        # 确定开始时间
        start_time = curr['start_time']
        if start_time is None:
            start_time = datetime.now()
            current_duration = 0
        else:
            # 计算当前过去了多少秒
            current_duration = (datetime.now() - start_time).total_seconds()
            # 防止稍微溢出
            if current_duration > EPOCH_DURATION:
                current_duration = EPOCH_DURATION

        end_time = start_time + timedelta(seconds=EPOCH_DURATION)
        # 实时计算 PSD
        psd_data = eeg_thread._calculate_psd(raw_data)

    # 1. 更新指标
    last_relax = relax_data[-1] if relax_data else 0
    last_focus = focus_data[-1] if focus_data else 0
    epoch_cnt = len(eeg_thread.epochs)
    alpha_energy = round(psd_data['Alpha'], 2) if psd_data.get('Alpha') else 0

    metric_relax.metric("😌当前放松指数", f"{last_relax}",
                        delta=f"{last_relax - (relax_data[-2] if len(relax_data) > 1 else 0):+.1f}")
    metric_focus.metric("🧐当前专注指数", f"{last_focus}",
                        delta=f"{last_focus - (focus_data[-2] if len(focus_data) > 1 else 0):+.1f}")
    metric_epoch.metric("📈已采集帧数", f"{epoch_cnt}", delta="实时更新")
    metric_alpha.metric("Alpha频段能量", f"{alpha_energy}", delta="实时更新")

    # -------------------------------------------------------------------------
    # 2. 绘图1：原始脑电波
    # -------------------------------------------------------------------------
    fig1, ax1 = plt.subplots(figsize=(8, 4), facecolor='white')
    ax1.set_title(f"原始脑电波信号 | {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}",
                  fontweight='bold', pad=15)
    ax1.set_xlabel("时间 (秒)")
    ax1.set_ylabel("幅值 (μV)")

    # 使用计算出的 current_duration 生成横坐标
    x_raw = np.linspace(0, current_duration, len(raw_data)) if raw_data else []

    # 长度对齐保护
    min_len = min(len(x_raw), len(raw_data))
    if min_len > 0:
        ax1.plot(x_raw[:min_len], raw_data[:min_len], color='#E74C3C', linewidth=1.2, alpha=0.8, label='脑电波信号')

    # 锁定横坐标范围为 0-30s
    ax1.set_xlim(0, EPOCH_DURATION)

    # 【需求1实现】：固定纵坐标范围为 -100 到 100
    ax1.set_ylim(-100, 100)

    ax1.grid(True, which='major', axis='x', linestyle='-', alpha=0.6)

    # 正负双参考线
    ax1.axhline(y=75, color='#27AE60', linestyle=':', linewidth=2, label='±75μV 参考线')
    ax1.axhline(y=-75, color='#27AE60', linestyle=':', linewidth=2)

    ax1.legend(loc='upper right')
    plot_placeholder1.pyplot(fig1, clear_figure=True)
    plt.close(fig1)

    # -------------------------------------------------------------------------
    # 3. 绘图2：趋势图
    # -------------------------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(8, 4), facecolor='white')
    ax2.set_title("专注/放松指数趋势", fontweight='bold', pad=15)
    ax2.set_xlabel("时间 (秒)")
    ax2.set_ylabel("指数值")

    x_trend = np.linspace(0, current_duration, len(relax_data)) if relax_data else []

    min_len = min(len(x_trend), len(relax_data), len(focus_data))
    if min_len > 0:
        ax2.plot(x_trend[:min_len], relax_data[:min_len], color='#27AE60', label='放松值', linewidth=2)
        ax2.plot(x_trend[:min_len], focus_data[:min_len], color='#3498DB', label='专注值', linewidth=2)
        ax2.fill_between(x_trend[:min_len], relax_data[:min_len], color='#27AE60', alpha=0.1)
        ax2.fill_between(x_trend[:min_len], focus_data[:min_len], color='#3498DB', alpha=0.1)

    ax2.set_xlim(0, EPOCH_DURATION)
    ax2.legend(loc='upper left')
    plot_placeholder2.pyplot(fig2, clear_figure=True)
    plt.close(fig2)

    # -------------------------------------------------------------------------
    # 4. 绘图3：PSD (修改部分)
    # -------------------------------------------------------------------------
    fig3, ax3 = plt.subplots(figsize=(10, 4), facecolor='white')
    ax3.set_title("脑电波频段能量分布 (PSD)", fontweight='bold', pad=15)

    # 原始标签顺序: ['Delta', 'Theta', 'Alpha', 'Spindle']
    bands = list(BANDS.keys())

    #######
    # 获取原始数值
    val_delta = psd_data.get('Delta', 0)
    val_theta = psd_data.get('Theta', 0)
    val_alpha = psd_data.get('Alpha', 0)
    val_spindle = psd_data.get('Spindle', 0)

    energies = [val_alpha, val_theta, val_delta, val_spindle]

    colors = ['#3498DB', '#E67E22', '#27AE60', '#9B59B6']
    bars = ax3.bar(bands, energies, color=colors, alpha=0.8, edgecolor='black', width=0.6)

    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.2f}', ha='center', va='bottom', fontsize=9)
    plot_placeholder3.pyplot(fig3, clear_figure=True)
    plt.close(fig3)

# -------------------------- 主循环 --------------------------
if run_monitoring:
    while True:
        draw_charts()
        time.sleep(refresh_rate)
else:
    st.warning("⚠️ 实时监测已暂停")
    # 即使暂停，也画一次图，防止白屏
    draw_charts()