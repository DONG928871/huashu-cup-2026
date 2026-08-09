# -*- coding: utf-8 -*-
"""Q3最终补充：参数空间全景图 + 代码片段 + 更新docx到v3"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch
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

# ===== 图9: 参数空间全景 =====
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_xlim(0,10); ax.set_ylim(0,6); ax.axis('off')
ax.set_facecolor('#fcfcfb')

# Title
ax.text(5, 5.6, 'MS-PAGCM 六维参数空间全景', fontsize=14, fontweight='bold', ha='center', color='#0d7377')
ax.text(5, 5.2, '三层算法升级：多分散性支持 + Sobol全局敏感性 + 分尺度分析', fontsize=9, ha='center', color='#898781')

# Three scale layers
layers = [
    (0.8, 1.5, 8.4, 1.2, '#0d7377', '微观层 (粒子尺度)', 'mu_r in [100,500]  |  CV_r in [0,0.5]  |  s in [0.5,2.0]', '粒径分布P(r;mu_r,CV_r) + 形状因子s修正等效接触面积'),
    (0.8, 2.9, 8.4, 1.2, '#eb6834', '介观层 (团簇尺度)', 'alpha in [0,2]  |  strategy in {0,1,2,3}', 'PAGCM自适应系数 + 排布策略(随机/链状/层状/MaxEnt)'),
    (0.8, 4.3, 8.4, 1.2, '#2a78d6', '宏观层 (RVE尺度)', 'phi in [0.001, 0.05]', '体积填充率——粒子总体积/RVE体积'),
]
for x,y,w,h,c,title,params,desc in layers:
    b = FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.08", facecolor=c, alpha=0.08, edgecolor=c, linewidth=2)
    ax.add_patch(b)
    ax.text(x+0.3, y+h-0.3, title, fontsize=10, fontweight='bold', color=c, va='top')
    ax.text(x+0.3, y+h-0.65, params, fontsize=8, color='#52514e', va='top')
    ax.text(x+0.3, y+h-0.95, desc, fontsize=7.5, color='#898781', va='top', style='italic')

save('q3_parameter_space.png')

# ===== 图10: Q3算法流程图(简化版) =====
fig, ax = plt.subplots(figsize=(8, 6))
ax.set_xlim(0,8); ax.set_ylim(0,9); ax.axis('off')
ax.set_facecolor('#f9f9f7')
colors = {'data':'#2a78d6', 'build':'#0d7377', 'solve':'#1baf7a', 'verify':'#4a3aa7'}

steps = [
    (7.8, 'data', '1', '定义6维参数空间 Theta', 'mu_r, CV_r, s, alpha, phi, strategy各设上下界'),
    (6.8, 'data', '2', 'Hammersley序列采样', 'N_s=2000个6维低差异样本点, 保证均匀覆盖'),
    (5.8, 'build', '3a', '多分散PAGCM评估(微观升级)', '从P(r;mu_r,CV_r)采样半径 -> ri_eff=f(ri,s_i)'),
    (4.8, 'build', '3b', '团簇特征提取(介观升级)', '连通分量大小分布+分形维度+各向异性比'),
    (3.8, 'solve', '4', 'PAGCM连通评估(宏观升级)', '对每个样本运行PAGCM -> P_conn + 分量统计'),
    (2.8, 'solve', '5', 'Sobol方差分解', 'S_i=V[E(P_conn|theta_i)]/V, S_Ti=1-V[E|theta_~i]/V'),
    (1.8, 'verify', '6', 'Bootstrap + OAT验证 + 三尺度排序', '500次重采样CI + OAT对比 + 微观/介观/宏观汇总'),
]
for i,(y,c,s,title,desc) in enumerate(steps):
    b = FancyBboxPatch((0.8, y-0.35), 6.4, 0.7, boxstyle="round,pad=0.06",
        facecolor='white', edgecolor=colors[c], linewidth=2, zorder=2)
    ax.add_patch(b)
    ax.text(1.1, y, s, fontsize=8, fontweight='bold', color='white', va='center', ha='center',
            bbox=dict(boxstyle='circle,pad=0.12', facecolor=colors[c], edgecolor='none'), zorder=3)
    ax.text(2.0, y+0.1, title, fontsize=9, fontweight='bold', va='center')
    ax.text(2.0, y-0.15, desc, fontsize=7, color='#898781', va='center')
    if i < len(steps)-1:
        ax.annotate('', xy=(4, steps[i+1][0]+0.7), xytext=(4, y-0.35),
                    arrowprops=dict(arrowstyle='->', color='#898781', lw=1.5))

ax.text(4, 8.5, 'MS-PAGCM 求解流程', fontsize=13, fontweight='bold', ha='center', color='#0d7377')
y_l = 0.8
for i,(l,c) in enumerate([('采样','#2a78d6'),('模型升级','#0d7377'),('求解','#1baf7a'),('验证','#4a3aa7')]):
    ax.add_patch(plt.Rectangle((1.2+i*1.8, y_l), 0.25, 0.18, facecolor=c))
    ax.text(1.45+i*1.8, y_l+0.09, l, fontsize=7, color='#898781', va='center')

save('q3_solve_flow.png')

print('Q3最终补充图片生成完成!')
