# -*- coding: utf-8 -*-
"""生成第二问全部图片：流程图 + 结果图表"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np, os

OUT = r'C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\docx输出\图片'
os.makedirs(OUT, exist_ok=True)
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ===== 图0: Q2流程图 =====
def draw_flowchart():
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_xlim(0, 10); ax.set_ylim(0, 15)
    ax.axis('off')
    ax.set_facecolor('#f9f9f7')
    fig.patch.set_facecolor('#f9f9f7')
    colors = {'init':'#2a78d6','build':'#eb6834','solve':'#1baf7a','verify':'#4a3aa7'}

    def box(text, y, c, w=6.2, h=0.6, s=''):
        b = FancyBboxPatch((5-w/2, y-h/2), w, h, boxstyle="round,pad=0.08",
                           facecolor='white', edgecolor=colors[c], linewidth=2, zorder=2)
        ax.add_patch(b)
        if s:
            ax.text(5-w/2+0.3, y, s, fontsize=8, fontweight='bold', color='white', va='center', ha='center',
                    bbox=dict(boxstyle='circle,pad=0.15', facecolor=colors[c], edgecolor='none'), zorder=3)
        ax.text(5, y, text, fontsize=8.5, fontweight='bold', ha='center', va='center', zorder=3)

    def io_box(text, y):
        b = FancyBboxPatch((2, y-0.3), 6, 0.6, boxstyle="round,pad=0.1",
                           facecolor='#52514e', edgecolor='none', linewidth=0, zorder=2)
        ax.add_patch(b)
        ax.text(5, y, text, fontsize=8.5, fontweight='bold', color='white', ha='center', va='center', zorder=3)

    def arr(y1, y2):
        ax.annotate('', xy=(5, y2+0.3), xytext=(5, y1-0.3),
                    arrowprops=dict(arrowstyle='->', color='#898781', lw=1.5))

    ax.text(5, 14.5, 'MESA-PAGCM 建模流程图', fontsize=14, fontweight='bold', ha='center')
    ax.text(5, 14.0, '最大熵模拟退火优化模型 (跨领域迁移创新)', fontsize=8, color='#898781', ha='center')

    io_box('[开始] 输入优化参数: phi_target, P_target, L, r0', 13.2)
    arr(12.9, 12.2)
    box('场景抽象: 填料优化问题->带PAGCM评估器的组合优化\n决策变量 X=[{p_i},N], 目标 f=N/Nmax+lambda*max(0,P_target-P_conn)', 11.6, 'init', s='1-2')
    arr(11.3, 10.6)
    box('MaxEnt初始化 (迁移1-信息论) : 最大化空间配置熵\n泊松盘采样(beta=0.7) 生成均匀初始粒子排布', 10.0, 'build', s='3')
    arr(9.7, 9.0)
    box('SA全局搜索 (迁移2-统计物理) : T=T0=50开始\n扰动操作(位移/增粒/删粒) -> PAGCM评估 -> Metropolis接受/拒绝', 8.4, 'build', s='4')
    arr(8.1, 7.4)
    box('PAGCM快速评估 (融合层) : O(N log N)评估连通性\n输出 P_conn -> 计算 f(X) = N/Nmax + lambda*penalty', 6.8, 'solve', s='5')
    arr(6.5, 5.8)
    box('降温迭代: T=gamma*T (gamma=0.95, 166轮)\n高温探索 -> 低温锁定。收敛? -> 输出最优方案', 5.2, 'solve', s='6')
    arr(4.9, 4.2)
    box('结果验证: 5次独立SA多重启动 + Pareto前沿提取\n降温曲线收敛分析 + 与Q1交叉验证', 3.6, 'verify', s='7-8')
    arr(3.3, 2.8)
    io_box('[输出] 最优N*+{p_i*}+P_conn* + Pareto前沿 + 降温曲线', 2.4)

    # Legend
    y_l = 1.4
    for i, (l, c) in enumerate([('初始化','#2a78d6'),('模型构建','#eb6834'),('求解迭代','#1baf7a'),('验证','#4a3aa7')]):
        ax.add_patch(plt.Rectangle((1.5+i*2.2, y_l), 0.3, 0.2, facecolor=c))
        ax.text(1.85+i*2.2, y_l+0.1, l, fontsize=7, color='#898781', va='center')

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '图Q2_0_MESA流程图.png'), dpi=200, bbox_inches='tight', facecolor='#f9f9f7')
    plt.close()
    print('[OK] Q2流程图')

draw_flowchart()

# ===== 图1: MESA参数配置表可视化 =====
def draw_params():
    fig, ax = plt.subplots(figsize=(9, 4.5))
    params = ['T0', 'gamma', 'T_min', 'lambda', 'M0', 'P_target', 'beta', 'sigma', 'n_restarts', 'K_conv']
    values = [50, 0.95, 0.01, 2.0, 100, 0.95, 0.70, 0.05, 5, 20]
    ranges_lo = [10, 0.85, 0.001, 0.5, 50, 0.80, 0.50, 0.01, 3, 10]
    ranges_hi = [100, 0.99, 0.1, 5.0, 500, 0.99, 0.90, 0.15, 10, 50]
    norm_vals = [(v-lo)/(hi-lo) for v, lo, hi in zip(values, ranges_lo, ranges_hi)]

    colors = ['#e34948' if v < 0.3 else '#eb6834' if v < 0.6 else '#2a78d6' for v in norm_vals]
    bars = ax.barh(params, norm_vals, color=colors, edgecolor='white', height=0.7)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width()+0.02, bar.get_y()+bar.get_height()/2, str(v),
                va='center', fontsize=9, fontweight='bold')
    ax.set_xlim(0, 1.3)
    ax.set_title('图Q2-1 MESA超参数配置', fontsize=12, fontweight='bold', pad=12)
    ax.text(0.5, -0.12, '红色=低值区, 橙色=中值区, 蓝色=高值区。P_target=0.95(IPC-4101标准), gamma=0.95(166轮降温)',
            ha='center', fontsize=8, color='#898781', style='italic', transform=ax.transAxes)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '图Q2_1_MESA参数配置.png'), dpi=200, bbox_inches='tight', facecolor='#fcfcfb')
    plt.close()
    print('[OK] 参数图')

draw_params()

# ===== 图2: 优化目标搜索空间 =====
def draw_search():
    fig, ax = plt.subplots(figsize=(8, 4.5))
    targets = ['组1_场景A', '组1_场景B', '组2_场景A', '组2_场景B']
    n_orig = [12, 12, 49, 49]
    n_min = [664, 664, 664, 664]
    n_max = [13290, 13290, 13290, 13290]
    n_c = 4430
    x = np.arange(len(targets))
    ax.bar(x-0.25, n_orig, 0.2, color='#2a78d6', edgecolor='white', label='原始N')
    ax.bar(x, n_min, 0.2, color='#eb6834', edgecolor='white', label='N_min=664')
    ax.bar(x+0.25, n_max, 0.2, color='#1baf7a', edgecolor='white', label='N_max=13290')
    ax.axhline(n_c, color='#e34948', linewidth=2, linestyle='--', label='N_c=4430 (理论)')
    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(targets, fontsize=9)
    ax.set_ylabel('粒子数 N (log)', fontsize=9)
    ax.set_title('图Q2-2 优化目标与搜索空间', fontsize=12, fontweight='bold', pad=12)
    ax.legend(fontsize=8, loc='upper left')
    ax.text(0.5, -0.15, '搜索下界664=N_c*15% (PAGCM自适应可低于经典阈值), 上界13290=N_c*3 (充分保证可行)',
            ha='center', fontsize=8, color='#898781', style='italic', transform=ax.transAxes)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '图Q2_2_搜索空间.png'), dpi=200, bbox_inches='tight', facecolor='#fcfcfb')
    plt.close()
    print('[OK] 搜索空间')

draw_search()

# ===== 图3: 退火冷却曲线 =====
def draw_cooling():
    fig, ax = plt.subplots(figsize=(8, 4))
    T = 50; temps = []
    while T > 0.01: temps.append(T); T *= 0.95
    temps.append(0.01)
    colors = ['#e34948' if t > 10 else '#eb6834' if t > 1 else '#2a78d6' for t in temps]
    ax.scatter(range(len(temps)), temps, c=colors, s=5, alpha=0.7)
    ax.plot(range(len(temps)), temps, color='#2a78d6', alpha=0.3, linewidth=1)
    ax.set_yscale('log')
    ax.set_xlabel('降温轮次 k', fontsize=9)
    ax.set_ylabel('温度 T', fontsize=9)
    ax.set_title('图Q2-3 模拟退火冷却曲线 (T0=50, gamma=0.95)', fontsize=12, fontweight='bold', pad=12)
    ax.axvspan(0, 40, alpha=0.06, color='#e34948')
    ax.axvspan(140, 170, alpha=0.06, color='#2a78d6')
    ax.text(15, 30, '探索期\n(高接受率)', fontsize=8, color='#e34948', ha='center')
    ax.text(152, 30, '锁定期\n(低接受率)', fontsize=8, color='#2a78d6', ha='center')
    ax.text(0.5, -0.15, '共166轮降温。高温区(T>10)充分探索; 低温区(T<1)微调锁定。每轮100次PAGCM评估x5重启=83k评估。',
            ha='center', fontsize=8, color='#898781', style='italic', transform=ax.transAxes)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '图Q2_3_冷却曲线.png'), dpi=200, bbox_inches='tight', facecolor='#fcfcfb')
    plt.close()
    print('[OK] 冷却曲线')

draw_cooling()

# ===== 图4: 跨领域迁移映射 =====
def draw_transfer():
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_facecolor('#fcfcfb')

    # Source domains
    for i, (x, label, color) in enumerate([(1.5, '信息论\n(Shannon 1948)', '#2a78d6'),
                                            (5.0, '统计物理\n(Metropolis 1953)', '#eb6834'),
                                            (8.5, '冶金学\n(Kirkpatrick 1983)', '#1baf7a')]):
        box = FancyBboxPatch((x-1, 3.8), 2, 1.2, boxstyle="round,pad=0.1", facecolor=color, alpha=0.15, edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x, 4.4, label, fontsize=9, fontweight='bold', ha='center', va='center', color=color)

    # Arrows down
    for x in [1.5, 5.0, 8.5]:
        ax.annotate('', xy=(x, 2.3), xytext=(x, 3.5), arrowprops=dict(arrowstyle='->', color='#898781', lw=2))

    # Target domain
    box = FancyBboxPatch((2.5, 0.8), 5, 1.2, boxstyle="round,pad=0.1", facecolor='#4a3aa7', alpha=0.1, edgecolor='#4a3aa7', linewidth=2.5)
    ax.add_patch(box)
    ax.text(5, 1.4, 'MESA-PAGCM', fontsize=12, fontweight='bold', ha='center', va='center', color='#4a3aa7')
    ax.text(5, 1.0, '最大熵初始化 + 模拟退火 + PAGCM评估', fontsize=8, ha='center', va='center', color='#898781')

    # Mapping labels
    ax.text(1.5, 2.9, '最大熵原理\n-> 粒子均匀初始化', fontsize=7, ha='center', color='#2a78d6', style='italic')
    ax.text(5.0, 2.9, 'Metropolis准则\n-> 接受/拒绝候选解', fontsize=7, ha='center', color='#eb6834', style='italic')
    ax.text(8.5, 2.9, '退火冷却策略\n-> 全局搜索锁定', fontsize=7, ha='center', color='#1baf7a', style='italic')

    ax.set_title('图Q2-4 跨领域模型迁移映射', fontsize=12, fontweight='bold', pad=8)
    ax.text(5, 0.3, '创新方向2: 跨领域模型迁移创新——信息论+统计物理+冶金学 -> 材料填料优化',
            ha='center', fontsize=8, color='#898781', style='italic')

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '图Q2_4_跨领域迁移.png'), dpi=200, bbox_inches='tight', facecolor='#fcfcfb')
    plt.close()
    print('[OK] 迁移图')

draw_transfer()

print('\nQ2全部图片生成完成!')
for f in sorted(os.listdir(OUT)):
    if 'Q2' in f:
        print('  %s (%.0f KB)' % (f, os.path.getsize(os.path.join(OUT, f))/1024))
