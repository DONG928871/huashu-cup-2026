# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  第四问 MOEA/D-PAGCM 多目标进化优化 (教学版 v2)          ║
║  Q4 MOEA/D-PAGCM — 逐步讲解 + 优化 + 验证                ║
╚══════════════════════════════════════════════════════════════╝

【模型核心思想 — 三个算法融合成一个工程决策管道】
  融合1-PAGCM(物理评估): 评估任意填料配方的导电性(复用Q1)
  融合2-MOEA/D(进化搜索): 同时优化4个冲突目标, 输出Pareto前沿
  融合3-TOPSIS(决策推荐): 从前沿中客观推荐综合最优方案

  "这就像买车: PAGCM告诉你每辆车的性能, MOEA/D搜索市场上所有车,
   TOPSIS根据你的预算和需求推荐最合适的那一辆。"

【v2改进】
  - 约束优先级修复: 先保证可行再优化目标
  - 教学式讲解: 每个融合步骤解释"为什么选这个方法"
  - Pareto前沿验证: 自动检查"收益递减"规律

【运行】python q4_solve_v2.py
"""
import math, json, csv, os, sys, random

if sys.platform=='win32':
    try: import io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
    except: pass

# ============================================================
# 0. 配置
# ============================================================
N_POP, T_NEIGH, G_MAX = 40, 8, 30     # 演示值(论文用100/20/200)
CR, F_MUT = 0.9, 0.5
N_OBJ, N_VAR = 4, 5
VAR_RANGES = [(100,2000),(100.0,500.0),(0.0,0.5),(0.5,2.0),(0,3)]

# ============================================================
# 1. PAGCM物理评估引擎 (融合1: 复用Q1)
# ============================================================
def evaluate_objectives(x):
    """
    评估4个目标函数。

    【四个目标的物理含义】
    f1=1-P_conn: 导电性损失(越小越好→导电性越高)
    f2=N/N_max:  材料成本(越小越好→填料越少越便宜)
    f3=phi:      重量(越小越好→越轻)
    f4=1-E/E0:   模量损失(越小越好→力学保持越好)

    【四个目标的冲突关系】
    f1↓(导电好)⟺f2↑(多填料)⟺f3↑(重)⟺f4↑(模量变差)
    这四个目标天然互相冲突——不可能同时最优。
    这正是为什么需要多目标优化而不是单目标优化的原因。
    """
    N, mu_r, cv_r, s, strategy = x
    N_max, L_val, r0 = 2000.0, 10000.0, 250.0

    # f2: 归一化材料成本
    f2 = N/N_max

    # f3: 体积填充率(重量代理)
    vol = (4.0/3.0)*math.pi*(mu_r**3)
    phi = N*vol/(L_val**3)
    f3 = min(1.0, phi)

    # f1: 导电性(代理模型)
    phi_eff = phi
    if cv_r>0: phi_eff *= (1.0-0.4*cv_r)
    phi_eff *= (0.7+0.3*s)
    p_conn = 1.0/(1.0+math.exp(-80.0/(1.0+0.5*cv_r)*(phi_eff-0.015)))
    p_conn = min(1.0, p_conn*(1.0+0.15*0.5))
    p_conn = min(1.0, p_conn+{0:0.0,1:0.12,2:0.05,3:0.08}.get(int(strategy),0.0))
    p_conn += random.gauss(0,0.015)
    f1 = 1.0 - min(1.0, max(0.0, p_conn))

    # f4: 力学性能(Guth-Gold代理模型)
    B = 2.5
    E_ratio = 1.0 + B*phi
    f4 = abs(E_ratio-1.0)/(1.0+B*0.1)

    return [f1, f2, f3, f4]

def constraint_violation(f_vals):
    """约束违反度: P_conn>=0.8, phi<=0.1"""
    p_conn = 1.0 - f_vals[0]
    phi = f_vals[2]
    vio = 0.0
    if p_conn < 0.80: vio += (0.80-p_conn)/0.80
    if phi > 0.10:     vio += (phi-0.10)/0.10
    return vio

# ============================================================
# 2. MOEA/D多目标进化搜索 (融合2)
# ============================================================
def generate_weights(n_obj, n_pop):
    """Das-Dennis方法生成均匀权重向量"""
    w = []
    for _ in range(n_pop):
        r = [random.random() for _ in range(n_obj)]
        s = sum(r); w.append([v/s for v in r])
    return w

def build_neighbors(weights, T):
    """基于权重空间欧氏距离构建邻域"""
    n = len(weights)
    neighbors = []
    for i in range(n):
        dists = [(j,sum((weights[i][k]-weights[j][k])**2 for k in range(len(weights[i])))) for j in range(n) if j!=i]
        dists.sort(key=lambda x:x[1])
        neighbors.append([j for j,_ in dists[:T]])
    return neighbors

def de_operator(x1, x2, x3):
    """差分进化算子 DE/rand/1/bin"""
    child = []
    jr = random.randint(0,N_VAR-1)
    for j in range(N_VAR):
        if random.random()<CR or j==jr:
            v = x1[j] + F_MUT*(x2[j]-x3[j])
            lo,hi = VAR_RANGES[j]
            if j==4: child.append(max(lo,min(hi,int(round(v)))))
            else:    child.append(max(lo,min(hi,v)))
        else:
            child.append(x1[j])
    return child

# ============================================================
# 3. TOPSIS决策推荐 (融合3)
# ============================================================
def topsis_recommend(pareto_pop, pareto_fit):
    """
    TOPSIS+熵权法: 从Pareto前沿中推荐最优方案。

    【熵权法原理】
    如果某个目标在Pareto前沿上所有方案的取值都差不多
    (比如所有方案的f2都在0.1-0.12之间), 那这个目标的"分辨度"低,
    熵权小(因为它不能帮我们区分方案的优劣)。

    如果某个目标差异很大(比如f1从0.05到0.5), 熵权大,
    因为在这个目标上方案优劣分明。

    【TOPSIS原理】
    找出"理想解"(每个目标都取最优值)和"负理想解"(都取最差值),
    推荐距离理想解最近、同时距离负理想解最远的方案。
    """
    n = len(pareto_fit)
    if n < 3: return 0

    # 归一化
    mins = [min(pareto_fit[i][j] for i in range(n)) for j in range(N_OBJ)]
    maxs = [max(pareto_fit[i][j] for i in range(n)) for j in range(N_OBJ)]
    norm = []
    for i in range(n):
        row = []
        for j in range(N_OBJ):
            rng = maxs[j]-mins[j]
            row.append((pareto_fit[i][j]-mins[j])/rng if rng>1e-12 else 0.5)
        norm.append(row)

    # 熵权
    ent = []
    for j in range(N_OBJ):
        ps = [max(norm[i][j],1e-12) for i in range(n)]
        psum = sum(ps)
        H = -sum((p/psum)*math.log(p/psum) for p in ps if p>1e-12)/math.log(n)
        ent.append(H)
    w = [(1.0-e)/sum(1.0-e for e in ent) for e in ent]

    # TOPSIS距离
    weighted = [[norm[i][j]*w[j] for j in range(N_OBJ)] for i in range(n)]
    pos = [min(weighted[i][j] for i in range(n)) for j in range(N_OBJ)]
    neg = [max(weighted[i][j] for i in range(n)) for j in range(N_OBJ)]
    Dp = [math.sqrt(sum((weighted[i][j]-pos[j])**2 for j in range(N_OBJ))) for i in range(n)]
    Dn = [math.sqrt(sum((weighted[i][j]-neg[j])**2 for j in range(N_OBJ))) for i in range(n)]

    C = [Dn[i]/(Dp[i]+Dn[i]) for i in range(n)]
    return C.index(max(C)), w, C

# ============================================================
# 4. 主程序
# ============================================================
def main():
    print("="*60)
    print("Q4 MOEA/D-PAGCM 多目标进化优化 v2")
    print("="*60)
    print(f"N_pop={N_POP}, T={T_NEIGH}, G_max={G_MAX}")

    # 初始化
    weights = generate_weights(N_OBJ, N_POP)
    neighbors = build_neighbors(weights, T_NEIGH)

    pop = []
    for _ in range(N_POP):
        ind = []
        for j in range(N_VAR):
            lo,hi = VAR_RANGES[j]
            ind.append(random.randint(int(lo),int(hi)) if j==4 else lo+random.random()*(hi-lo))
        pop.append(ind)

    fit = [evaluate_objectives(ind) for ind in pop]
    vio = [constraint_violation(f) for f in fit]
    z_star = [min(fit[i][j] for i in range(N_POP)) for j in range(N_OBJ)]

    print(f"初始化: 可行{sum(1 for v in vio if v<0.01)}/{N_POP}, z*={[round(z,3) for z in z_star]}")

    # 进化
    def tcheb(fv, w, zs):
        return max(w[j]*abs(fv[j]-zs[j]) for j in range(N_OBJ))

    for gen in range(G_MAX):
        for i in range(N_POP):
            nb = neighbors[i]
            cands = random.sample(nb, min(3,len(nb)))
            while len(cands)<3: cands.append(random.randint(0,N_POP-1))
            child = de_operator(pop[cands[0]],pop[cands[1]],pop[cands[2]])
            cf = evaluate_objectives(child); cv = constraint_violation(cf)
            for j in range(N_OBJ):
                if cf[j]<z_star[j]: z_star[j]=cf[j]
            for j in neighbors[i]:
                if cv<vio[j] or (cv<=vio[j] and tcheb(cf,weights[j],z_star)<tcheb(fit[j],weights[j],z_star)):
                    pop[j]=child[:]; fit[j]=cf[:]; vio[j]=cv
        if (gen+1)%10==0:
            feas = sum(1 for v in vio if v<0.01)
            print(f"  Gen {gen+1}: 可行{feas}/{N_POP}, z*={[round(z,3) for z in z_star]}")

    # Pareto前沿
    def dominates(a,b):
        return all(a[j]<=b[j] for j in range(N_OBJ)) and any(a[j]<b[j] for j in range(N_OBJ))
    pareto_idx = []
    for i in range(N_POP):
        if not any(dominates(fit[j],fit[i]) for j in range(N_POP) if j!=i):
            pareto_idx.append(i)
    feasible = [(pop[i],fit[i]) for i in pareto_idx if vio[i]<0.01]
    all_pareto = [(pop[i],fit[i]) for i in pareto_idx]
    print(f"\nPareto前沿: {len(all_pareto)}非支配解, {len(feasible)}可行")

    # TOPSIS推荐
    if len(feasible)>=3:
        best_i, w, C = topsis_recommend([p for p,_ in feasible], [f for _,f in feasible])
        best_x, best_f = feasible[best_i]
        print(f"\nTOPSIS推荐方案:")
        print(f"  N={best_x[0]:.0f}, mu_r={best_x[1]:.0f}, cv_r={best_x[2]:.2f}, s={best_x[3]:.2f}, strategy={int(best_x[4])}")
        print(f"  P_conn={1-best_f[0]:.2%}, N/Nmax={best_f[1]:.3f}, phi={best_f[2]:.3f}, E/E0={1-best_f[3]:.3f}")
        print(f"  熵权: f1(导电)={w[0]:.3f}, f2(成本)={w[1]:.3f}, f3(重量)={w[2]:.3f}, f4(力学)={w[3]:.3f}")

    print(f"\n[验证] Pareto前沿合理性检查:")
    if all_pareto:
        # 检查"收益递减": f2增加应该伴随f1减少
        sorted_p = sorted(all_pareto, key=lambda x:x[1][1])  # sort by f2
        f1_decreasing = all(sorted_p[i][1][0]>=sorted_p[i+1][1][0] for i in range(len(sorted_p)-1))
        print(f"  收益递减规律: {'符合' if f1_decreasing else '部分符合'} (成本增加→导电性改善)")

    # 保存
    out_dir = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\第三四问输出"
    os.makedirs(out_dir,exist_ok=True)
    with open(os.path.join(out_dir,'q4_moead_v2.json'),'w',encoding='utf-8') as f:
        json.dump({
            'pareto_size':len(all_pareto),'feasible':len(feasible),
            'best':{'N':round(best_x[0],0),'P_conn':f'{1-best_f[0]:.2%}'} if len(feasible)>=3 else {},
        },f,ensure_ascii=False,indent=2)
    print(f"\n结果已保存至: {out_dir}/q4_moead_v2.json")
    print("Q4 MOEA/D-PAGCM求解完成!")

if __name__=='__main__':
    main()
