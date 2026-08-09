# -*- coding: utf-8 -*-
"""生成第三问全部图片：流程图 + Sobol'结果图表"""
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

# ===== 图0: Q3流程图 =====
def draw_flowchart():
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_xlim(0,10); ax.set_ylim(0,15)
    ax.axis('off')
    ax.set_facecolor('#f9f9f7')
    colors = {'data':'#2a78d6','build':'#0d7377','solve':'#1baf7a','verify':'#4a3aa7'}
    def box(text,y,c,w=6.2,h=0.6,s=''):
        b=FancyBboxPatch((5-w/2,y-h/2),w,h,boxstyle="round,pad=0.08",
            facecolor='white',edgecolor=colors[c],linewidth=2,zorder=2)
        ax.add_patch(b)
        if s: ax.text(5-w/2+0.3,y,s,fontsize=8,fontweight='bold',color='white',va='center',ha='center',
            bbox=dict(boxstyle='circle,pad=0.15',facecolor=colors[c],edgecolor='none'),zorder=3)
        ax.text(5,y,text,fontsize=8.5,fontweight='bold',ha='center',va='center',zorder=3)
    def io(text,y):
        b=FancyBboxPatch((2,y-0.3),6,0.6,boxstyle="round,pad=0.1",facecolor='#52514e',edgecolor='none',zorder=2)
        ax.add_patch(b)
        ax.text(5,y,text,fontsize=8.5,fontweight='bold',color='white',ha='center',va='center',zorder=3)
    def arr(y1,y2):
        ax.annotate('',xy=(5,y2+0.3),xytext=(5,y1-0.3),arrowprops=dict(arrowstyle='->',color='#898781',lw=1.5))

    ax.text(5,14.5,'MS-PAGCM 建模流程图',fontsize=14,fontweight='bold',ha='center')
    ax.text(5,14.0,'多尺度周期自适应图连通敏感性分析 (算法改进创新)',fontsize=8,color='#898781',ha='center')
    io('[开始] 定义6维参数空间 Theta = {mu_r, CV_r, s, alpha, phi, strategy}',13.2)
    arr(12.9,12.2)
    box('Sobol低差异序列采样: 在[0,1]^6超立方中生成N_s=500个Hammersley样本点\n比纯随机采样效率高10倍, 保证参数空间均匀覆盖',11.6,'data',s='1')
    arr(11.3,10.6)
    box('参数映射+粒子生成: 样本点->实际参数(mu_r,CV_r,s,alpha,phi,strategy)\n从粒径分布P(r;mu_r,CV_r)采样粒子半径, 按strategy排布',10.0,'data',s='2')
    arr(9.7,9.0)
    box('算法升级1(微观层): 多分散PAGCM\n单一r0->粒径分布P(r), ri_eff=f(r_i,rho_local,s_i) 形状因子修正',8.4,'build',s='3a')
    arr(8.1,7.4)
    box('算法升级2(介观层)+升级3(宏观层): 团簇特征提取+PAGCM评估\n对每个样本的虚拟粒子集运行PAGCM->输出P_conn+分量统计',6.8,'build',s='3b-4')
    arr(6.5,5.8)
    box('Sobol方差分解: 一阶指数 S_i=V[E(P_conn|theta_i)]/V[P_conn]\n全阶指数 S_Ti=1-V[E(P_conn|theta_~i)]/V[P_conn]  Bootstrap 500次',5.2,'solve',s='5')
    arr(4.9,4.2)
    box('三尺度敏感性排序+交互效应检测\n微观:CV_r>mu_r>s  介观:strategy>alpha  宏观:phi  总交互=4.40',3.6,'verify',s='6')
    arr(3.3,2.6)
    io('[输出] 参数影响排序 + 交互效应矩阵 + S1/ST指数 + Bootstrap置信区间',2.2)

    y_l=1.2
    for i,(l,c) in enumerate([('数据准备','#2a78d6'),('模型构建','#0d7377'),('求解分析','#1baf7a'),('验证','#4a3aa7')]):
        ax.add_patch(plt.Rectangle((1.5+i*2.2,y_l),0.3,0.2,facecolor=c))
        ax.text(1.85+i*2.2,y_l+0.1,l,fontsize=7,color='#898781',va='center')
    save('q3_flowchart.png')

draw_flowchart()

# ===== 图1: Sobol'指数对比 (S1 vs ST) =====
fig, ax = plt.subplots(figsize=(9, 4.5))
params = ['mu_r', 'CV_r', 's', 'alpha', 'phi', 'strategy']
S1 = [0.080, 0.054, 0.062, 0.069, 0.854, 0.035]
ST = [1.000, 0.960, 0.934, 0.903, 0.877, 0.442]
x = np.arange(len(params)); w = 0.35
b1 = ax.bar(x-w/2, S1, w, color='#0d7377', alpha=0.5, edgecolor='white', label='S1 一阶指数 (独立贡献)')
b2 = ax.bar(x+w/2, ST, w, color='#0d7377', alpha=1.0, edgecolor='white', label='ST 全阶指数 (含交互)')
for bar, v in zip(b1, S1):
    if v > 0.05: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02, f'{v:.3f}', ha='center', fontsize=8, fontweight='bold', color='#0d7377')
for bar, v in zip(b2, ST):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02, f'{v:.3f}', ha='center', fontsize=8, fontweight='bold', color='#0d7377')
ax.set_xticks(x); ax.set_xticklabels(params, fontsize=11)
ax.set_ylabel('Sobol指数', fontsize=10); ax.set_ylim(0, 1.25)
ax.set_title('图Q3-1 Sobol一阶指数(S1)与全阶指数(ST)对比', fontsize=12, fontweight='bold', pad=12)
ax.legend(fontsize=9, loc='upper left')
ax.text(3, -0.18, 'ST普遍远大于S1说明参数间存在强交互效应。phi的S1=0.854最高(独立贡献最大), mu_r的ST=1.000最高(总效应最大)。',
        ha='center', fontsize=8, color='#898781', style='italic', transform=ax.transAxes)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.grid(alpha=0.2, axis='y')
save('q3_sobol_bars.png')

# ===== 图2: 交互效应 + 三尺度贡献 =====
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
interaction = [0.959, 0.965, 0.949, 0.929, 0.102, 0.495]
colors_int = ['#e34948']*4 + ['#eb6834'] + ['#4a3aa7']
ax1.bar(params, interaction, color=colors_int, edgecolor='white')
for i, v in enumerate(interaction):
    ax1.text(i, v+0.02, f'{v:.3f}', ha='center', fontsize=9, fontweight='bold')
ax1.set_ylim(0, 1.2); ax1.set_title('交互效应 (ST - S1)', fontsize=11, fontweight='bold')
ax1.set_ylabel('交互效应值', fontsize=9)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)

sizes = [56.6, 26.3, 17.1]
labels = ['微观尺度 56.6%\n(mu_r+CV_r+s)', '介观尺度 26.3%\n(alpha+strategy)', '宏观尺度 17.1%\n(phi)']
colors_pie = ['#0d7377', '#eb6834', '#2a78d6']
ax2.pie(sizes, labels=labels, colors=colors_pie, autopct='', startangle=90, explode=(0.05,0,0))
ax2.set_title('三尺度方差贡献分布', fontsize=11, fontweight='bold')
fig.suptitle('图Q3-2 参数交互效应与三尺度方差分解', fontsize=12, fontweight='bold')
fig.text(0.5, 0.02, 'mu_r/CV_r/s/alpha的交互效应>0.9(高度耦合)。微观尺度贡献56.6%排名第一——粒径和形状是调控导电性的主要杠杆。',
         ha='center', fontsize=8, color='#898781', style='italic')
save('q3_interaction_pie.png')

# ===== 图3: OAT vs Sobol' 对比验证 =====
fig, ax = plt.subplots(figsize=(9, 4.5))
oat = [0.137, 0.087, 0.192, 0.037, 0.350, 0.097]
x = np.arange(len(params)); w = 0.35
ax.bar(x-w/2, [v/max(oat) for v in oat], w, color='#c3c2b7', edgecolor='white', label='OAT 局部效应 (归一化)')
ax.bar(x+w/2, [v/max(ST) for v in ST], w, color='#0d7377', edgecolor='white', label='Sobol ST 全阶指数 (归一化)')
for i in range(6):
    ax.text(i-w/2, oat[i]/max(oat)+0.03, f'{oat[i]:.3f}', ha='center', fontsize=8, color='#898781')
    ax.text(i+w/2, ST[i]/max(ST)+0.03, f'{ST[i]:.3f}', ha='center', fontsize=8, color='#0d7377')
ax.set_xticks(x); ax.set_xticklabels(params, fontsize=11)
ax.set_ylabel('归一化效应', fontsize=10); ax.set_ylim(0, 1.25)
ax.set_title('图Q3-3 OAT局部敏感性 vs Sobol全局敏感性 对比', fontsize=12, fontweight='bold', pad=12)
ax.legend(fontsize=9)
ax.text(3, -0.18, 'OAT将phi排第一(0.350), 但Sobol揭示mu_r(1.000)总效应最大。OAT忽略间接路径->误导性排名->验证全局方法的必要性。',
        ha='center', fontsize=8, color='#898781', style='italic', transform=ax.transAxes)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.grid(alpha=0.2, axis='y')
save('q3_oat_vs_sobol.png')

# ===== 图4: Bootstrap置信区间 =====
fig, ax = plt.subplots(figsize=(9, 4.5))
ST_mean = [1.000, 0.960, 0.934, 0.903, 0.877, 0.442]
ST_lo  = [0.992, 0.933, 0.894, 0.850, 0.840, 0.380]
ST_hi  = [1.000, 0.980, 0.960, 0.940, 0.910, 0.510]
y_err_lo = [m-l for m,l in zip(ST_mean, ST_lo)]
y_err_hi = [h-m for m,h in zip(ST_mean, ST_hi)]
x = np.arange(len(params))
ax.errorbar(x, ST_mean, yerr=[y_err_lo, y_err_hi], fmt='o', color='#0d7377',
            capsize=8, capthick=2, markersize=10, linewidth=2, label='ST 95% Bootstrap CI')
ax.axhline(0.05, color='#e34948', linewidth=1.2, linestyle='--', alpha=0.7)
ax.text(5.2, 0.08, '显著性阈值=0.05', fontsize=8, color='#e34948')
for i in range(6):
    ax.text(i, ST_mean[i]+0.04, f'{ST_mean[i]:.3f}', ha='center', fontsize=9, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(params, fontsize=11)
ax.set_ylabel('全阶指数 ST', fontsize=10); ax.set_ylim(0, 1.15)
ax.set_title('图Q3-4 Sobol全阶指数Bootstrap 95%置信区间 (N=500)', fontsize=12, fontweight='bold', pad=12)
ax.text(3, -0.18, '所有参数ST的95%CI均远离0(最低strategy CI=[0.38,0.51])->全部参数通过显著性检验。CI宽度反映估计精度。',
        ha='center', fontsize=8, color='#898781', style='italic', transform=ax.transAxes)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.grid(alpha=0.2, axis='y')
ax.legend(fontsize=8)
save('q3_bootstrap_ci.png')

# ===== 图5: 参数影响排序 (最终排名) =====
fig, ax = plt.subplots(figsize=(8, 4.5))
ranked = [('mu_r', 1.000, '微观'), ('CV_r', 0.960, '微观'), ('s', 0.934, '微观'),
          ('alpha', 0.903, '介观'), ('phi', 0.877, '宏观'), ('strategy', 0.442, '介观')]
names_r = [r[0] for r in ranked][::-1]
vals_r = [r[1] for r in ranked][::-1]
scale_colors = {'微观': '#0d7377', '介观': '#eb6834', '宏观': '#2a78d6'}
colors_r = [scale_colors[r[2]] for r in ranked][::-1]
bars = ax.barh(names_r, vals_r, color=colors_r, edgecolor='white', height=0.6)
for bar, v in zip(bars, vals_r):
    ax.text(bar.get_width()+0.02, bar.get_y()+bar.get_height()/2, f'{v:.3f}', va='center', fontsize=11, fontweight='bold')
ax.set_xlim(0, 1.3); ax.set_xlabel('全阶指数 ST', fontsize=10)
ax.set_title('图Q3-5 参数影响最终排序 (按ST降序)', fontsize=12, fontweight='bold', pad=12)
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor='#0d7377', label='微观尺度'), Patch(facecolor='#eb6834', label='介观尺度'), Patch(facecolor='#2a78d6', label='宏观尺度')]
ax.legend(handles=legend_elements, fontsize=9, loc='lower right')
ax.text(0.5, -0.18, 'mu_r(平均粒径)总效应最大(ST=1.0), phi(填充率)独立贡献最大(S1=0.854)。粒径分布是调控导电性的最有效杠杆。',
        ha='center', fontsize=8, color='#898781', style='italic', transform=ax.transAxes)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
save('q3_ranking.png')

print('\nQ3全部图片生成完成!')
