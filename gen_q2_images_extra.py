# -*- coding: utf-8 -*-
"""补充Q2遗漏图片"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np, os

OUT = r'C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\docx输出\图片'
os.makedirs(OUT, exist_ok=True)
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def save(name):
    path = os.path.join(OUT, name)
    plt.tight_layout(pad=1.5)
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#fcfcfb')
    print('[OK] %s (%.0f KB)' % (name, os.path.getsize(path)/1024))
    plt.close('all')

# ===== 图5: 优化目标热力图 =====
fig, ax = plt.subplots(figsize=(8, 3.5))
data = np.array([[0,0,0],[0,0,0],[1,0,0],[0,0,0],[1,1,1],[1,1,1]])
names = ['组1_A (HIGH)', '组1_B (HIGH)', '组2_A (MED)', '组2_B (HIGH)', '组3_A (基准)', '组3_B (基准)']
cmap = matplotlib.colors.ListedColormap(['#2a78d6', '#e34948'])
ax.imshow(data, cmap=cmap, aspect='auto')
for i in range(6):
    for j in range(3):
        ax.text(j, i, '连通' if data[i,j] else '不连通', ha='center', va='center', fontsize=10, fontweight='bold', color='white')
ax.set_xticks(range(3)); ax.set_xticklabels(['X','Y','Z'], fontsize=10)
ax.set_yticks(range(6)); ax.set_yticklabels(names, fontsize=9)
ax.set_title('图Q2-5 优化目标识别——Q1连通性判定', fontsize=12, fontweight='bold', pad=12)
ax.text(1.5, 6.3, '红色=不连通(需MESA优化)  蓝色=连通(基准参考)  4优化目标+2基准',
        ha='center', fontsize=8, color='#898781', style='italic')
save('q2_heatmap_targets.png')

# ===== 图6: 逾渗理论曲线 =====
fig, ax = plt.subplots(figsize=(8, 4))
r0, L = 250, 10000
vol = (4/3)*np.pi*r0**3
Ns_arr = np.linspace(100, 15000, 200)
phis_arr = Ns_arr * vol / L**3
ax.plot(Ns_arr, phis_arr, color='#52514e', linewidth=2, label='N vs phi')
ax.axhline(0.29, color='#e34948', linewidth=1.2, linestyle='--', alpha=0.7, label='phi_c=0.29')
ax.axvline(4430, color='#e34948', linewidth=1.2, linestyle='--', alpha=0.7, label='N_c=4430')
ax.axvspan(664, 13290, alpha=0.06, color='#2a78d6')
ax.text(7000, 0.08, 'MESA搜索范围\n[664, 13290]', fontsize=9, color='#2a78d6', ha='center')
orig_N = [12, 12, 49, 49, 535, 535]
orig_phi = [n*vol/L**3 for n in orig_N]
ax.scatter(orig_N, orig_phi, c=['#e34948','#e34948','#eb6834','#e34948','#1baf7a','#1baf7a'], s=60, zorder=5, edgecolors='white')
ax.set_xlabel('粒子数 N', fontsize=10); ax.set_ylabel('体积填充率 phi', fontsize=10)
ax.set_xlim(0, 14500); ax.set_ylim(0, 1.0)
ax.set_title('图Q2-6 逾渗理论曲线——N vs phi', fontsize=12, fontweight='bold', pad=12)
ax.legend(fontsize=8, loc='upper left')
ax.grid(alpha=0.2)
save('q2_percolation_curve.png')

# ===== 图7: 计算成本 =====
fig, ax = plt.subplots(figsize=(8, 4))
targets = ['组1_A\n(N=12)', '组1_B\n(N=12)', '组2_A\n(N=49)', '组2_B\n(N=49)']
times = [6.6, 6.6, 27.1, 27.1]
colors = ['#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7']
bars = ax.bar(range(4), times, color=colors, edgecolor='white', width=0.6)
for bar, t in zip(bars, times):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5, f'{t:.1f} min',
            ha='center', fontsize=11, fontweight='bold')
ax.set_xticks(range(4)); ax.set_xticklabels(targets, fontsize=9)
ax.set_ylabel('预估计算时间 (min)', fontsize=10); ax.set_ylim(0, 35)
ax.set_title('图Q2-7 优化任务预估计算成本', fontsize=12, fontweight='bold', pad=12)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
save('q2_cost.png')

# ===== 图8: SA收敛曲线 =====
fig, ax = plt.subplots(figsize=(8, 4))
np.random.seed(42)
x = np.arange(166)
f_vals = 1.2 * np.exp(-x/40) + 0.1 + np.random.normal(0, 0.03, 166)
for i in range(1, len(f_vals)):
    if f_vals[i] > f_vals[i-1]: f_vals[i] = f_vals[i-1]
f_vals[140:] = 0.1 + np.random.normal(0, 0.008, 26)
for i in range(141, len(f_vals)):
    if f_vals[i] > f_vals[i-1]: f_vals[i] = f_vals[i-1]

ax.plot(x, f_vals, color='#2a78d6', linewidth=1.5)
ax.fill_between(x, f_vals, alpha=0.1, color='#2a78d6')
ax.axhline(0.1, color='#e34948', linewidth=1.2, linestyle='--', alpha=0.7)
ax.axvspan(0, 40, alpha=0.04, color='#e34948')
ax.axvspan(140, 166, alpha=0.04, color='#2a78d6')
ax.text(15, 1.08, '探索期(高温)', fontsize=8, color='#e34948', ha='center')
ax.text(152, 1.08, '锁定期(低温)', fontsize=8, color='#2a78d6', ha='center')
ax.text(150, 0.15, '收敛~0.10', fontsize=9, color='#e34948')
ax.set_xlabel('降温轮次 k', fontsize=10); ax.set_ylabel('目标函数 f(X)', fontsize=10)
ax.set_ylim(0, 1.3)
ax.set_title('图Q2-8 SA收敛曲线 (示意)', fontsize=12, fontweight='bold', pad=12)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.grid(alpha=0.2, axis='y')
save('q2_convergence.png')

# ===== 图9: 优化前后对比 =====
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
ax1.bar(['X','Y','Z'], [0,0,0], color='#2a78d6', edgecolor='white')
ax1.set_ylim(0, 1.2); ax1.set_title('优化前: 组1_A (N=12)', fontsize=11, fontweight='bold')
ax1.set_ylabel('连通性', fontsize=9)
ax1.text(0, 0.15, '0/3 连通\n全绝缘', ha='center', fontsize=10, fontweight='bold', color='#e34948')
ax1.text(1, 0.6, 'phi=0.08%', ha='center', fontsize=8, color='#898781')

ax2.bar(['X','Y','Z'], [1,1,1], color='#1baf7a', edgecolor='white')
ax2.axhline(0.95, color='#e34948', linewidth=1.2, linestyle='--', alpha=0.7)
ax2.text(1, 1.05, 'P_target=0.95', fontsize=8, color='#e34948', ha='center')
ax2.set_ylim(0, 1.2); ax2.set_title('优化后: MESA推荐 (N~680)', fontsize=11, fontweight='bold')
ax2.text(0, 0.15, '3/3 连通\nP_conn>=95%', ha='center', fontsize=10, fontweight='bold', color='#1baf7a')
ax2.text(1, 0.6, 'phi=4.5%', ha='center', fontsize=8, color='#898781')

fig.suptitle('图Q2-9 MESA优化前后对比', fontsize=12, fontweight='bold')
save('q2_before_after.png')

print('\nQ2补充图片全部生成完成!')
