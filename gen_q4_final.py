# -*- coding: utf-8 -*-
"""Q4最终补充：MOEA/D算法流程图 + 参数全景 + 代码片段 + 更新docx到v2"""
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

# ===== 图8: MOEA/D算法伪代码流程 =====
fig, ax = plt.subplots(figsize=(9, 7.5))
ax.set_xlim(0,9); ax.set_ylim(0,10); ax.axis('off')
ax.set_facecolor('#fcfcfb')
colors = {'init':'#2a78d6','loop':'#e34948','end':'#1baf7a'}

steps = [
    (9.0, 'init', '初始化', 'Das-Dennis生成N_pop组权重向量; 随机初始化种群; PAGCM评估; 构建T邻域'),
    (7.8, 'loop', 'for gen=1:G_max', '进化主循环开始'),
    (6.8, 'loop', 'for i=1:N_pop (每个子问题)', '从邻域选3父代 -> DE/rand/1/bin变异+交叉 -> 生成子代'),
    (5.8, 'loop', 'PAGCM评估子代', '计算P_conn -> [f1=1-P_conn, f2=N/Nmax, f3=phi, f4=1-E/E0]'),
    (4.8, 'loop', '更新理想点z*', 'z*_j = min(z*_j, child_f_j) for j=1..4'),
    (3.8, 'loop', '更新邻域解', 'for j in neighbors(i): 若g^{tch}(child|lambda_j,z*)<g^{tch}(x_j|lambda_j,z*), 则替换'),
    (2.6, 'loop', 'end for (子问题); end for (代数)', '非支配排序提取Pareto前沿'),
    (1.5, 'end', 'TOPSIS决策输出', '熵权法客观赋权 -> 计算相对贴近度C_i -> 推荐max(C_i)方案'),
]
for i,(y,c,title,desc) in enumerate(steps):
    b = FancyBboxPatch((0.3, y-0.5), 8.4, 0.75, boxstyle="round,pad=0.06",
        facecolor='white', edgecolor=colors[c], linewidth=2, zorder=2)
    ax.add_patch(b)
    ax.text(0.6, y+0.05, title, fontsize=9, fontweight='bold', va='center', color=colors[c])
    ax.text(3.5, y+0.05, desc, fontsize=8, va='center', color='#52514e')
    if i < len(steps)-1:
        ax.annotate('', xy=(4.5, steps[i+1][0]+0.6), xytext=(4.5, y-0.5),
                    arrowprops=dict(arrowstyle='->', color='#898781', lw=1.5))

ax.text(4.5, 9.7, 'Q4 补充图: MOEA/D-PAGCM 算法伪代码流程', fontsize=13, fontweight='bold', ha='center', color='#e34948')
y_l = 0.5
for i,(l,c) in enumerate([('初始化','#2a78d6'),('进化循环','#e34948'),('决策输出','#1baf7a')]):
    ax.add_patch(plt.Rectangle((1.5+i*2.5, y_l), 0.25, 0.18, facecolor=c))
    ax.text(1.75+i*2.5, y_l+0.09, l, fontsize=7, color='#898781', va='center')
save('q4_algo_flow.png')

# ===== 图9: Q4参数配置全景 =====
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.set_xlim(0,10); ax.set_ylim(0,7); ax.axis('off')
ax.set_facecolor('#fcfcfb')
ax.text(5, 6.6, 'MOEA/D-PAGCM 配置参数全景', fontsize=13, fontweight='bold', ha='center', color='#e34948')

groups = [
    (0.5, 4.5, '#e34948', 'MOEA/D算法参数', [('N_pop','50/100','种群规模'),('T','10/20','邻域大小'),('G_max','50/200','进化代数')]),
    (3.5, 4.5, '#eb6834', '差分进化参数', [('CR','0.9','交叉率'),('F','0.5','缩放因子')]),
    (6.0, 4.5, '#1baf7a', '工程约束', [('P_target','>=0.80','导电可靠性'),('phi_max','<=0.10','填充率上限')]),
    (0.5, 2.2, '#2a78d6', 'PAGCM评估参数', [('r0','250','基础半径'),('alpha','0.5','自适应系数'),('L','10000','RVE边长')]),
    (3.5, 2.2, '#4a3aa7', 'Guth-Gold代理', [('B','2.5(球体)','Guth系数'),('E/E0','1+B*phi','模量模型')]),
    (6.0, 2.2, '#eda100', 'TOPSIS决策', [('w_j','熵权法','客观权重'),('C_i','贴近度','排序准则')]),
]
for x,y,c,title,params in groups:
    b = FancyBboxPatch((x,y), 2.5, 1.6, boxstyle="round,pad=0.08", facecolor=c, alpha=0.08, edgecolor=c, linewidth=2)
    ax.add_patch(b)
    ax.text(x+1.25, y+1.3, title, fontsize=9, fontweight='bold', ha='center', color=c)
    for j,(pname,pval,pdesc) in enumerate(params):
        ax.text(x+0.2, y+0.9-j*0.4, f'{pname}={pval}', fontsize=7.5, fontweight='bold', color='#52514e')
        ax.text(x+1.2, y+0.9-j*0.4, pdesc, fontsize=7, color='#898781', style='italic')

ax.text(5, 1.2, '三模型融合: PAGCM提供物理评估 + MOEA/D搜索Pareto前沿 + TOPSIS推荐最优方案 | 总评估2500次(50x50)约50秒',
        ha='center', fontsize=8, color='#898781', style='italic')
save('q4_params_overview.png')

print('Q4补充图片生成完成!')
