
from fpdf import FPDF
import datetime

class PDF(FPDF):
    def header(self):
        # Arial bold 15
        self.set_font('SimHei', '', 10)
        # Title
        self.cell(0, 10, '自动化耳机测试与数据上传软件 - 项目实施方案与报价书', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('SimHei', '', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

    def chapter_title(self, num, label):
        # Arial 12
        self.set_font('SimHei', '', 14)
        # Background color
        self.set_fill_color(200, 220, 255)
        # Title
        self.cell(0, 10, 'Section %d : %s' % (num, label), 0, 1, 'L', 1)
        # Line break
        self.ln(4)

    def chapter_body(self, body):
        # Times 12
        self.set_font('SimHei', '', 11)
        # Output justified text
        self.multi_cell(0, 8, body)
        # Line break
        self.ln()

pdf = PDF()
pdf.alias_nb_pages()
pdf.add_font('SimHei', '', r'C:\Windows\Fonts\simhei.ttf', uni=True)
pdf.add_page()

# Title Page
pdf.set_font('SimHei', '', 24)
pdf.cell(0, 60, '', 0, 1)
pdf.cell(0, 20, '自动化耳机测试与数据上传软件', 0, 1, 'C')
pdf.set_font('SimHei', '', 18)
pdf.cell(0, 20, '项目实施方案与报价书', 0, 1, 'C')
pdf.set_font('SimHei', '', 12)
pdf.cell(0, 20, '日期: ' + datetime.date.today().strftime("%Y-%m-%d"), 0, 1, 'C')
pdf.add_page()

# Executive Summary
pdf.chapter_title(0, '执行摘要 (Executive Summary)')
pdf.chapter_body(
    "本项目旨在开发一套用于耳机生产线及实验室的自动化测试软件，涵盖频响、失真、相位、冲击响应及动态线性偏离等核心声学指标测试，并支持数据自动上传至指定服务器。\n\n"
    "核心功能：\n"
    "- 自动化音量校准（94dB SPL对准）\n"
    "- 全频段声学参数测试（20Hz-20kHz）\n"
    "- 产品信息录入与照片上传\n"
    "- 测试数据云端同步\n\n"
    "关键指标预测：\n"
    "- 总工时预估：约 80 - 120 人时\n"
    "- 交付周期：10 - 14 周（按每日投入 0.5-1 小时计算）\n"
    "- 报价区间：24,000 元 - 45,000 元 (CNY)\n"
    "- 主要风险：ASIO驱动兼容性、声卡硬件延迟稳定性、校准算法收敛速度。"
)

# 1. Technical Feasibility
pdf.chapter_title(1, '技术可行性评估')
pdf.chapter_body(
    "1.1 需求拆解与难点分析\n"
    "- 音频I/O：需支持ASIO以保证低延迟和采样同步。Python的sounddevice或C#的NAudio均可实现。\n"
    "- 实时校准：需构建闭环控制系统，实时分析麦克风输入并调整输出增益。难点在于算法的稳定性与收敛速度。\n"
    "- 信号处理：FFT变换、THD计算、相位展开及脉冲响应计算需高精度算法库支持。\n"
    "- 动态线性偏离：需在不同电平下多次测量并精确对齐频响曲线。\n\n"
    "1.2 推荐技术栈方案\n"
    "方案 A：Python 生态（推荐，开发效率高）\n"
    "- UI框架：PyQt6 或 PySide6 (现代、跨平台、响应式)\n"
    "- 音频核心：sounddevice (PortAudio封装, 支持ASIO) + PyAudio\n"
    "- 数据处理：NumPy (矩阵运算), SciPy (信号处理), Matplotlib (图表绘制)\n"
    "- 数据上传：Requests (HTTP库)\n"
    "- 部署：PyInstaller 打包为独立EXE\n\n"
    "方案 B：C# .NET 生态（性能与系统集成度高）\n"
    "- UI框架：WPF (Windows Presentation Foundation) 或 WinForms\n"
    "- 音频核心：NAudio (成熟的.NET音频库, 支持ASIO)\n"
    "- 数据处理：MathNet.Numerics (FFT, 线性代数)\n"
    "- 图表控件：OxyPlot 或 LiveCharts\n\n"
    "1.3 第三方依赖与授权\n"
    "- PortAudio (Python方案底层): MIT/Open Source\n"
    "- ASIO SDK: Steinberg License (需注意商用条款，通常开发免费)\n"
    "- NumPy/SciPy: BSD License (允许商用)\n"
    "- Qt (PyQt/PySide): LGPL (动态链接允许商用，静态链接需授权)\n"
    "潜在费用：若需购买商用图表库或特定ASIO驱动授权（通常声卡自带）。本项目推荐使用开源免费库。"
)

# 2. Detailed Implementation
pdf.chapter_title(2, '详细实施方案 (WBS)')
pdf.chapter_body(
    "2.1 模块分解 (WBS)\n"
    "M1. 硬件接口层 (15%)\n"
    "- 设备枚举与选择 (ASIO/WASAPI)\n"
    "- 采样率/缓冲区配置\n"
    "- 输入/输出通道映射\n"
    "M2. 核心测量引擎 (30%)\n"
    "- 信号发生器 (正弦扫频, 脉冲)\n"
    "- 采集同步与对齐\n"
    "- 自动增益控制 (AGC) 算法 (94dB校准)\n"
    "- FFT分析与指标计算 (FR, THD, Phase)\n"
    "M3. 业务逻辑层 (20%)\n"
    "- 测试流程控制 (状态机)\n"
    "- 动态线性偏离测试逻辑 (3次测量+差分)\n"
    "- 数据校验与异常处理\n"
    "M4. 用户界面 (25%)\n"
    "- 仪表盘与实时波形显示\n"
    "- 产品信息录入表单\n"
    "- 结果图表渲染\n"
    "M5. 数据与网络 (10%)\n"
    "- JSON序列化\n"
    "- HTTP/REST API 上传模块\n\n"
    "2.2 迭代计划\n"
    "版本 V0.1 (原型): 完成硬件连接与简单的回环测试。\n"
    "版本 V0.5 (核心): 完成校准功能与频响测试，数据本地保存。\n"
    "版本 V0.8 (完整): 加入THD/相位/线性度测试，完善UI交互。\n"
    "版本 V1.0 (交付): 集成数据上传，完成最终测试与打包。"
)

# 3. Development Timeline
pdf.chapter_title(3, '开发周期估算')
pdf.chapter_body(
    "假设资源投入：1人，兼职 (0.5 - 1 小时/工作日 + 周末少量)\n"
    "折算全职人天：约 10-15 人天\n"
    "实际跨度：10 - 14 周\n\n"
    "阶段规划 (甘特图模拟):\n"
    "Week 1-2:  需求确认, 技术选型, 环境搭建, 硬件接口联调 [关键路径]\n"
    "Week 3-5:  核心测量算法实现 (扫频, FFT, 校准) [关键路径]\n"
    "Week 6-8:  UI界面开发, 波形显示, 交互逻辑\n"
    "Week 9-10: 高级测试项 (线性偏离, 冲击响应) 实现\n"
    "Week 11:   数据上传接口对接, 本地存储\n"
    "Week 12:   系统集成测试, Bug修复, 文档编写\n\n"
    "注：核心测量算法与硬件接口联调为高风险任务，不可并行。"
)

# 4. Quotation
pdf.chapter_title(4, '报价模型')
pdf.chapter_body(
    "计费标准：按功能点与预估工时计费 (参考时薪: 300元/小时)\n\n"
    "方案 A：基础版 (MVP) - 报价: 24,000 元\n"
    "- 包含：硬件连接, 自动校准, 频响测试, THD测试, 本地CSV保存。\n"
    "- 不含：动态线性偏离, 冲击响应, HTTP上传, 复杂图表交互。\n\n"
    "方案 B：标准版 (完整功能) - 报价: 35,000 元\n"
    "- 包含：所有需求文档中的测试项目 (含线性偏离/冲击响应)。\n"
    "- 包含：HTTP数据上传, JSON导出, 完整UI交互。\n"
    "- 交付：可执行程序, 用户手册。\n\n"
    "方案 C：高级版 (源码交付) - 报价: 48,000 元\n"
    "- 包含：标准版所有功能。\n"
    "- 交付：完整源代码 (Python/C#工程), 详细开发文档, 二次开发指导。\n"
    "- 服务：6个月免费远程维护与Bug修复。\n\n"
    "付款方式：\n"
    "- 预付款 (30%): 项目启动\n"
    "- 进度款 (40%): 完成核心测试功能演示 (V0.8)\n"
    "- 尾款 (30%): 验收合格并交付最终版本\n"
    "超出范围变更：300元/小时 或 协商一口价。"
)

# 5. Delivery & Maintenance
pdf.chapter_title(5, '交付与维护条款')
pdf.chapter_body(
    "5.1 交付物清单\n"
    "- 软件安装包 (Setup.exe / Portable Zip)\n"
    "- 用户操作手册 (PDF)\n"
    "- 部署配置说明 (含硬件连接指南)\n"
    "- (高级版) 源代码与API接口文档\n\n"
    "5.2 维护服务\n"
    "- 质保期：验收后 3 个月内，因软件本身缺陷导致的Bug提供免费修复。\n"
    "- 响应时效：工作日 24小时内响应，重大故障 48小时内提供解决方案。\n"
    "- 维护范围：不包含因操作系统升级、硬件更换或第三方API变更导致的系统不可用。\n\n"
    "5.3 合同条款摘要\n"
    "- 知识产权：除高级版外，软件著作权归开发者所有，甲方拥有永久使用权。\n"
    "- 保密协议：开发者承诺对甲方提供的产品数据、API接口信息严格保密。\n"
    "- 验收标准：以《软件需求规格说明书》及双方确认的测试用例为准。"
)

pdf.output('Project_Proposal.pdf')
