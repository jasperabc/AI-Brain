# 🧠 脑电波实时监测与闭环调控系统 (EEG Monitoring System)

这是一个基于 Python 的脑电波（EEG）实时监测与可视化平台。系统通过串口连接脑电设备（如 NeuroSky 模块），利用多线程读取数据，并使用 **Streamlit** 构建 Web 界面，实时展示专注度、放松度以及原始脑波波形。

## ✨ 功能特性

* **实时串口通信**：自动解析 EEG 硬件传输的数据包。
* **多维度指标**：实时计算并显示**专注度 (Focus)** 和 **放松度 (Relax)** 指数。
* **动态可视化**：
    * 使用 Matplotlib 绘制实时的专注/放松趋势图。
    * 显示原始脑电波形。
* **现代化 UI**：基于 Streamlit 的响应式界面，包含侧边栏控制和亮色模式优化。

---

## 🛠️ 环境搭建与安装 (Installation)

建议使用 Python 的虚拟环境（venv）来管理项目依赖，以避免与系统环境冲突。

### 第一步：激活虚拟环境
* 请根据你的操作系统（Windows/Mac/Linux）自行百度如何创建和激活 Python 虚拟环境。

### 第二步：安装依赖库
在虚拟环境激活的状态下，确保当前目录下有 `requirements.txt` 文件，然后运行以下命令一键安装所有依赖：

```bash
pip install -r requirements.txt
```

## 🚀 运行项目 (Running the App)

* 确保虚拟环境已激活，在终端中运行以下命令启动 Streamlit 服务：

```bash
streamlit run app.py
```