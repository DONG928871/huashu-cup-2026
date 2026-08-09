# -*- coding: utf-8 -*-
"""
Q3 MS-PAGCM v3 — 新增: PAWN密度敏感性分析 (双指标互补验证)
========================================================================
v3创新点: 在Sobol'方差分解基础上, 引入PAWN (density-based)敏感性指标。

【创新原理】
  Sobol'方法基于方差分解——它衡量的是参数对输出"波动幅度"的贡献。
  但如果某个参数改变了输出的"分布形状"而不改变方差呢?
  (比如使P_conn从均匀分布变成双峰分布, 但方差不变)

  PAWN方法基于累积分布函数(CDF)的偏移量:
  PAWN_i = max |CDF_{uncond}(y) - CDF_{cond}(y|theta_i)|
  它衡量的是参数对输出"整体分布"的影响, 而不仅仅是方差。

  Sobol'+PAWN双指标:
  - Sobol'显著但PAWN不显著→参数影响输出的波动幅度, 但分布形状稳定
  - PAWN显著但Sobol'不显著→参数改变输出分布形状, 但方差变化不大
  - 两者都显著→参数具有稳健的重要影响(最可靠)

【文献依据】Pianosi & Wagener (2015), Env Mod & Software
【改动量】仅新增PAWN计算函数(~40行), Sobol'核心不变
"""
import math, json, csv, os, sys, random

if sys.platform=='win32':
    try: import io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
    except: pass

N_SAMPLES, DIM = 300, 6
PRIMES = [2,3,5,7,11,13]

PARAMS = [
    {'name':'mu_r','lo':100.0,'hi':500.0,'label':'平均粒径','scale':'微观'},
    {'name':'CV_r','lo':0.0,'hi':0.5,'label':'粒径变异系数','scale':'微观'},
    {'name':'s','lo':0.5,'hi':2.0,'label':'形状因子','scale':'微观'},
    {'name':'alpha','lo':0.0,'hi':2.0,'label':'自适应系数','scale':'介观'},
    {'name':'phi','lo':0.001,'hi':0.05,'label':'体积填充率','scale':'宏观'},
    {'name':'strategy','lo':0,'hi':3,'label':'排布策略','scale':'介观(离散)'},
]

def halton(i, base):
    r, f = 0.0, 1.0/base
    while i>0: r+=f*(i%base); i//=base; f/=base
    return r

def gen_samples(n, dim):
    samples = []
    for i in range(1,n+1):
        s = [i/n]
        for d in range(1,dim): s.append(halton(i,PRIMES[d-1]))
        samples.append(s)
    return samples

def map_space(samples):
    mapped = []
    for s in samples:
        row = []
        for d in range(DIM):
            lo,hi = PARAMS[d]['lo'],PARAMS[d]['hi']
            row.append(int(lo+s[d]*(hi-lo+1))if d==5 else lo+s[d]*(hi-lo))
        mapped.append(row)
    return mapped

def eval_pconn(theta):
    mu_r,cv_r,sv,alpha,phi,strategy = theta
    phi_eff = phi
    if cv_r>0: phi_eff*=(1.0-0.4*cv_r)
    phi_eff*=(0.7+0.3*sv)
    p=1.0/(1.0+math.exp(-80.0/(1.0+0.5*cv_r)*(phi_eff-0.015)))
    p=min(1.0,p*(1.0+0.15*alpha))
    p=min(1.0,p+{0:0.0,1:0.12,2:0.05,3:0.08}.get(int(strategy),0.0))
    p=min(1.0,max(0.0,p+(mu_r/250.0-1.0)*0.1))
    return min(1.0,max(0.0,p+random.gauss(0,0.02)))

def sobol_indices(samples, f_vals):
    N = len(samples); D = len(samples[0])
    f_mean = sum(f_vals)/N
    V_total = sum((v-f_mean)**2 for v in f_vals)/N
    if V_total<1e-12: return [0.0]*D, [0.0]*D
    S1 = [0.0]*D; ST = [0.0]*D
    for d in range(D):
        data = [(s[d],v) for s,v in zip(samples,f_vals)]
        data.sort(key=lambda x:x[0])
        n_bin = max(5,min(50,N//10))
        bin_size = N//n_bin
        cond_means = []
        for b in range(n_bin):
            chunk = data[b*bin_size:(b+1)*bin_size]
            if chunk: cond_means.append(sum(v for _,v in chunk)/len(chunk))
        if cond_means:
            V_cond = sum((m-f_mean)**2 for m in cond_means)/len(cond_means)
            S1[d] = min(1.0,max(0.0,V_cond/V_total))
        other = sum(S1[j] for j in range(D) if j!=d)
        ST[d] = max(S1[d],min(1.0,1.0-other*0.5))
    return S1, ST

# ★v3新增: PAWN密度敏感性分析
def pawn_indices(samples, f_vals, n_intervals=10):
    """
    PAWN (density-based) 敏感性指数

    【计算步骤】
    1. 计算无条件CDF: 用所有样本的f_vals构建经验CDF
    2. 对每个参数i:
       a. 将参数i的取值范围等分为n_intervals个区间
       b. 对每个区间, 仅用该区间内的样本构建条件CDF
       c. 计算条件CDF与无条件CDF的K-S距离(最大偏差)
       d. PAWN_i = 所有区间中最大的K-S距离
    3. PAWN越大→参数对输出分布的整体形状影响越大

    【与Sobol的互补性】
    Sobol'捕获方差变化, PAWN捕获分布形状变化。
    两者结合提供更全面的敏感性画像。
    """
    N = len(samples); D = len(samples[0])
    f_sorted = sorted(f_vals)

    # 无条件CDF
    def ecdf(x, data):
        return sum(1 for v in data if v<=x)/len(data)

    PAWN = [0.0]*D
    for d in range(D):
        vals_d = [s[d] for s in samples]
        lo, hi = PARAMS[d]['lo'], PARAMS[d]['hi']
        interval_w = (hi-lo)/n_intervals

        max_ks = 0.0
        for k in range(n_intervals):
            # 条件子集: 参数d在第k个区间内的样本
            cond_f = [f_vals[i] for i in range(N)
                      if lo+k*interval_w <= vals_d[i] < lo+(k+1)*interval_w]
            if len(cond_f) < 5: continue  # 样本太少不可靠

            # 计算K-S距离: max|CDF_cond(x) - CDF_uncond(x)|
            ks = 0.0
            for fv in f_sorted:
                ks = max(ks, abs(ecdf(fv, cond_f)-ecdf(fv, f_vals)))
            max_ks = max(max_ks, ks)

        PAWN[d] = max_ks  # 取所有区间中最大的K-S距离

    return PAWN

# ==== 主程序 ====
def main():
    print("="*60)
    print("MS-PAGCM v3 — Sobol + PAWN 双指标敏感性分析")
    print("="*60)

    raw = gen_samples(N_SAMPLES, DIM)
    samples = map_space(raw)
    f_vals = [eval_pconn(s) for s in samples]

    # Sobol
    S1, ST = sobol_indices(samples, f_vals)

    # ★v3: PAWN
    PAWN = pawn_indices(samples, f_vals)

    # 双指标对比输出
    print(f"\n{'参数':12s} {'S1(Sobol)':>10s} {'ST(Sobol)':>10s} {'PAWN':>10s} {'类型判断':>20s}")
    print('-'*70)
    for i,p in enumerate(PARAMS):
        s1_str = '高独立' if S1[i]>0.1 else '低独立'
        st_str = '高交互' if ST[i]-S1[i]>0.5 else ('高总效' if ST[i]>0.5 else '低')
        pawn_str = '高' if PAWN[i]>0.3 else ('中' if PAWN[i]>0.15 else '低')

        # ★双指标综合判断
        if ST[i]>0.5 and PAWN[i]>0.3:
            verdict = '★稳健重要参数'
        elif ST[i]>0.5:
            verdict = '方差敏感(分布稳定)'
        elif PAWN[i]>0.3:
            verdict = '分布敏感(方差稳定)'
        else:
            verdict = '影响较小'

        print(f"{p['name']:12s} {S1[i]:10.4f} {ST[i]:10.4f} {PAWN[i]:10.4f} {verdict:>20s}")

    print(f"\n★ v3创新点: Sobol+PAWN双指标互补验证")
    print(f"  Sobol捕获方差变化 | PAWN捕获分布形状变化")
    print(f"  两者都显著的参数具有最稳健的重要性结论")

if __name__=='__main__':
    main()
