# -*- coding: utf-8 -*-
"""
Q4 MOEA/D-PAGCM 完整求解器
==========================
多目标进化分解优化：同时优化导电性+成本+重量+力学
纯Python标准库实现，零外部依赖
"""
import math, json, csv, os, sys, random, time
from collections import OrderedDict

if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except: pass

# ============================================================
# 0. 配置
# ============================================================
N_POP    = 50       # 种群规模（演示用50，实际论文用100）
T_NEIGH  = 10       # 邻域大小
G_MAX    = 50       # 进化代数（演示用50，实际论文用200）
CR       = 0.9      # DE交叉率
F_MUT    = 0.5      # DE缩放因子
N_OBJ    = 4        # 目标数
N_VAR    = 5        # 决策变量数：[N, mu_r, cv_r, s, strategy]

# 决策变量范围
VAR_RANGES = [
    (100, 2000),     # N: 粒子数
    (100.0, 500.0),  # mu_r: 平均粒径
    (0.0, 0.5),      # cv_r: 粒径变异系数
    (0.5, 2.0),      # s: 形状因子
    (0, 3),          # strategy: 排布策略
]

OUT_DIR = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\第三四问输出"
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# 1. PAGCM代理评估（4目标函数）
# ============================================================
def evaluate_objectives(x):
    """
    评估4个目标函数
    x = [N, mu_r, cv_r, s, strategy]
    返回: [f1, f2, f3, f4]
      f1 = 1 - P_conn  (导电性损失，最小化)
      f2 = N / N_max   (材料成本，最小化)
      f3 = phi         (重量/体积，最小化)
      f4 = 1 - E/E0    (模量损失，最小化)
    """
    N, mu_r, cv_r, s, strategy = x
    N_max = 2000.0
    L_val = 10000.0
    r0 = 250.0

    # f2: 归一化材料成本
    f2 = N / N_max

    # f3: 体积填充率
    vol_particle = (4.0/3.0) * math.pi * (mu_r ** 3)
    phi = N * vol_particle / (L_val ** 3)
    f3 = min(1.0, phi)

    # f1: 导电性（代理模型，与Q3一致但用实际N而非phi推导）
    phi_c = 0.015
    if cv_r > 0:
        phi_eff = phi * (1.0 - 0.4 * cv_r)
    else:
        phi_eff = phi
    phi_eff *= (0.7 + 0.3 * s)
    steepness = 80.0 / (1.0 + 0.5 * cv_r)
    p_conn = 1.0 / (1.0 + math.exp(-steepness * (phi_eff - phi_c)))
    size_factor = (mu_r / 250.0 - 1.0) * 0.1
    p_conn = min(1.0, max(0.0, p_conn + size_factor))
    strat_boost = {0: 0.0, 1: 0.12, 2: 0.05, 3: 0.08}
    p_conn = min(1.0, p_conn + strat_boost.get(int(strategy), 0.0))
    p_conn += random.gauss(0, 0.015)
    p_conn = min(1.0, max(0.0, p_conn))
    f1 = 1.0 - p_conn

    # f4: 力学性能（Guth-Gold代理：E/E0 = 1 + 2.5*phi）
    B = 2.5
    E_ratio = 1.0 + B * phi
    # 填料过多→模量变化大（此处定义损失为偏离1的归一化值）
    f4 = abs(E_ratio - 1.0) / (1.0 + B * 0.1)  # 以phi=0.1时归一化

    return [f1, f2, f3, f4]

def constraint_violation(x, f_vals):
    """约束违反度：P_conn>=0.8, phi<=0.1"""
    p_conn = 1.0 - f_vals[0]
    phi = f_vals[2]
    vio = 0.0
    if p_conn < 0.80:
        vio += (0.80 - p_conn) / 0.80
    if phi > 0.10:
        vio += (phi - 0.10) / 0.10
    return vio

# ============================================================
# 2. MOEA/D核心算法
# ============================================================
def generate_weight_vectors(n_obj, n_pop):
    """Das-Dennis方法生成均匀权重向量"""
    if n_obj == 4:
        # 简化：使用预设的均匀分布权重
        weights = []
        for i in range(n_pop):
            # 从Dirichlet分布近似
            w = [random.random() for _ in range(n_obj)]
            s = sum(w)
            w = [v/s for v in w]
            weights.append(w)
        return weights
    return []

def generate_neighbors(weights, T):
    """基于权重向量欧氏距离构建邻域"""
    n = len(weights)
    neighbors = []
    for i in range(n):
        dists = []
        for j in range(n):
            if i == j: continue
            d = sum((weights[i][k]-weights[j][k])**2 for k in range(len(weights[i])))
            dists.append((j, d))
        dists.sort(key=lambda x: x[1])
        neighbors.append([j for j, _ in dists[:T]])
    return neighbors

def de_operator(x_r1, x_r2, x_r3, cr, f_mut):
    """差分进化算子：DE/rand/1/bin"""
    child = []
    j_rand = random.randint(0, N_VAR-1)
    for j in range(N_VAR):
        if random.random() < cr or j == j_rand:
            if j == 4:  # strategy 离散
                v = int(round(x_r1[j] + f_mut * (x_r2[j] - x_r3[j])))
                lo, hi = VAR_RANGES[j]
                child.append(max(lo, min(hi, v)))
            else:
                v = x_r1[j] + f_mut * (x_r2[j] - x_r3[j])
                lo, hi = VAR_RANGES[j]
                child.append(max(lo, min(hi, v)))
        else:
            child.append(x_r1[j])
    return child

# ============================================================
# 3. 主优化流程
# ============================================================
print("=" * 70)
print("Q4 MOEA/D-PAGCM 多目标优化求解器")
print("=" * 70)
print(f"N_pop={N_POP}, T={T_NEIGH}, G_max={G_MAX}, CR={CR}, F={F_MUT}")
print()

# 3.1 初始化权重和邻域
print("阶段一：初始化MOEA/D种群...")
weights = generate_weight_vectors(N_OBJ, N_POP)
neighbors = generate_neighbors(weights, T_NEIGH)

# 初始化种群
population = []
for _ in range(N_POP):
    ind = []
    for j in range(N_VAR):
        lo, hi = VAR_RANGES[j]
        if j == 4:
            ind.append(random.randint(int(lo), int(hi)))
        else:
            ind.append(lo + random.random() * (hi - lo))
    population.append(ind)

# 评估初始种群
fitness = []
violations = []
for ind in population:
    fv = evaluate_objectives(ind)
    fitness.append(fv)
    violations.append(constraint_violation(ind, fv))

# 理想点 z* = min fⱼ (每个目标的最小值)
z_star = [min(fitness[i][j] for i in range(N_POP)) for j in range(N_OBJ)]

print(f"  种群初始化完成, z*={[round(v,3) for v in z_star]}")

# 3.2 进化主循环
print(f"\n阶段二：MOEA/D进化 (G_max={G_MAX})...")
hv_history = []
t0 = time.time()

for gen in range(G_MAX):
    for i in range(N_POP):
        # 从邻域中选3个不同父代
        nb = neighbors[i]
        candidates = random.sample(nb, min(3, len(nb)))
        while len(candidates) < 3:
            c = random.randint(0, N_POP-1)
            if c != i and c not in candidates:
                candidates.append(c)

        # DE生成子代
        child = de_operator(population[candidates[0]],
                           population[candidates[1]],
                           population[candidates[2]], CR, F_MUT)

        # 评估子代
        child_fv = evaluate_objectives(child)
        child_vio = constraint_violation(child, child_fv)

        # 更新理想点
        for j in range(N_OBJ):
            if child_fv[j] < z_star[j]:
                z_star[j] = child_fv[j]

        # 切比雪夫聚合函数
        def tchebycheff(fv, w, zs):
            return max(w[j] * abs(fv[j] - zs[j]) for j in range(N_OBJ))

        # 更新邻域解
        for j in neighbors[i]:
            # 约束处理：优先选择约束违反小的
            if child_vio < violations[j] or (child_vio <= violations[j] and
               tchebycheff(child_fv, weights[j], z_star) <
               tchebycheff(fitness[j], weights[j], z_star)):
                population[j] = child[:]
                fitness[j] = child_fv[:]
                violations[j] = child_vio

    # 统计
    if (gen+1) % 10 == 0:
        # 可行解比例
        feasible = sum(1 for v in violations if v < 0.01)
        print(f"  Gen {gen+1:3d}/{G_MAX}: feasible={feasible}/{N_POP}, z*={[round(v,3) for v in z_star]}")

print(f"  进化完成, 耗时{time.time()-t0:.2f}s")

# 3.3 非支配排序提取Pareto前沿
print("\n阶段三：非支配排序 + Pareto前沿提取...")
def dominates(fa, fb):
    """fa dominates fb if all fa_j <= fb_j and at least one <"""
    better = False
    for j in range(N_OBJ):
        if fa[j] > fb[j]:
            return False
        if fa[j] < fb[j]:
            better = True
    return better

# 去重
unique_pop = []
unique_fit = []
seen = set()
for i, ind in enumerate(population):
    key = tuple(round(v, 3) for v in fitness[i])
    if key not in seen:
        seen.add(key)
        unique_pop.append(ind)
        unique_fit.append(fitness[i])

# 提取非支配前沿
pareto_idx = []
for i in range(len(unique_fit)):
    dominated = False
    for j in range(len(unique_fit)):
        if i != j and dominates(unique_fit[j], unique_fit[i]):
            dominated = True
            break
    if not dominated:
        pareto_idx.append(i)

pareto_front = [(unique_pop[i], unique_fit[i], violations[population.index(unique_pop[i])]
                 if unique_pop[i] in population else 0.0)
                for i in pareto_idx]

# 筛选可行解（约束满足）
feasible_pareto = [(pop, fit, vio) for pop, fit, vio in pareto_front if vio < 0.01]
print(f"  Pareto前沿: {len(pareto_front)}个非支配解, {len(feasible_pareto)}个可行")

# 3.4 TOPSIS决策
print("\n阶段四：TOPSIS决策推荐...")

if len(feasible_pareto) >= 3:
    # 熵权法
    n_sol = len(feasible_pareto)
    fits = [fp[1] for fp in feasible_pareto]

    # 归一化
    min_f = [min(fits[i][j] for i in range(n_sol)) for j in range(N_OBJ)]
    max_f = [max(fits[i][j] for i in range(n_sol)) for j in range(N_OBJ)]
    norm_f = []
    for i in range(n_sol):
        row = []
        for j in range(N_OBJ):
            if max_f[j] - min_f[j] > 1e-12:
                row.append((fits[i][j] - min_f[j]) / (max_f[j] - min_f[j]))
            else:
                row.append(0.5)
        norm_f.append(row)

    # 熵值
    entropies = []
    for j in range(N_OBJ):
        p_sum = sum(max(norm_f[i][j], 1e-12) for i in range(n_sol))
        H = 0.0
        if p_sum > 0:
            for i in range(n_sol):
                p = norm_f[i][j] / p_sum
                if p > 1e-12:
                    H -= p * math.log(p)
        entropies.append(H / math.log(n_sol) if n_sol > 1 else 0.0)

    # 权重
    w_raw = [1.0 - e for e in entropies]
    w_sum = sum(w_raw)
    weights_entropy = [w / w_sum for w in w_raw]

    # TOPSIS
    # 加权归一化矩阵
    weighted = []
    for i in range(n_sol):
        row = [norm_f[i][j] * weights_entropy[j] for j in range(N_OBJ)]
        weighted.append(row)

    # 理想解和负理想解
    ideal_pos = [min(weighted[i][j] for i in range(n_sol)) for j in range(N_OBJ)]
    ideal_neg = [max(weighted[i][j] for i in range(n_sol)) for j in range(N_OBJ)]

    # 距离
    D_pos = [math.sqrt(sum((weighted[i][j]-ideal_pos[j])**2 for j in range(N_OBJ)))
             for i in range(n_sol)]
    D_neg = [math.sqrt(sum((weighted[i][j]-ideal_neg[j])**2 for j in range(N_OBJ)))
             for i in range(n_sol)]

    # 相对贴近度
    C = [D_neg[i] / (D_pos[i] + D_neg[i]) for i in range(n_sol)]

    # 最佳方案
    best_idx = C.index(max(C))
    best_solution = feasible_pareto[best_idx]
    print(f"  熵权: {[round(w,3) for w in weights_entropy]}")
    print(f"  TOPSIS最佳方案: idx={best_idx}, C={C[best_idx]:.4f}")
    print(f"    决策变量: N={best_solution[0][0]:.0f}, mu_r={best_solution[0][1]:.0f}, "
          f"cv_r={best_solution[0][2]:.2f}, s={best_solution[0][3]:.2f}, "
          f"strategy={int(best_solution[0][4])}")
    print(f"    目标值: f1(1-P_conn)={best_solution[1][0]:.4f}, f2(N/Nmax)={best_solution[1][1]:.4f}, "
          f"f3(phi)={best_solution[1][2]:.4f}, f4(1-E/E0)={best_solution[1][3]:.4f}")
    print(f"    解读: P_conn={1-best_solution[1][0]:.2%}, N={best_solution[0][0]:.0f}, "
          f"phi={best_solution[1][2]:.3f}, E/E0={1-best_solution[1][3]:.3f}")
else:
    weights_entropy = [0.25]*N_OBJ
    best_solution = None
    C = []
    print("  可行解不足3个，跳过TOPSIS")

# ============================================================
# 4. 保存结果
# ============================================================
print("\n阶段五：保存结果...")

results = {
    'method': 'MOEA/D-PAGCM',
    'parameters': {'N_pop': N_POP, 'T': T_NEIGH, 'G_max': G_MAX, 'CR': CR, 'F': F_MUT},
    'n_objectives': N_OBJ,
    'objectives': ['f1=1-P_conn', 'f2=N/N_max', 'f3=phi', 'f4=1-E/E0'],
    'pareto_front_size': len(pareto_front),
    'feasible_pareto_size': len(feasible_pareto),
    'ideal_point': [round(v, 4) for v in z_star],
    'entropy_weights': [round(w, 4) for w in weights_entropy],
    'topsis_scores': [round(c, 4) for c in C] if C else [],
    'best_solution': {
        'variables': {f'x{j}': best_solution[0][j] for j in range(N_VAR)} if best_solution else {},
        'objectives': {f'f{j}': best_solution[1][j] for j in range(N_OBJ)} if best_solution else {},
        'p_conn': 1 - best_solution[1][0] if best_solution else 0,
    } if best_solution else {},
    'pareto_front_sample': [
        {'variables': [round(v, 2) for v in pf[0]],
         'objectives': [round(v, 4) for v in pf[1]]}
        for pf in feasible_pareto[:20]
    ],
}

results_json = os.path.join(OUT_DIR, 'q4_moead_results.json')
with open(results_json, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"  [OK] {results_json}")

# Pareto CSV
csv_path = os.path.join(OUT_DIR, 'q4_pareto_front.csv')
with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['N','mu_r','cv_r','s','strategy','f1_1-P_conn','f2_N/Nmax','f3_phi','f4_1-E/E0','P_conn','feasible'])
    for pop, fit, vio in pareto_front:
        w.writerow([round(pop[0],1), round(pop[1],1), round(pop[2],3),
                    round(pop[3],3), int(pop[4]),
                    round(fit[0],6), round(fit[1],6), round(fit[2],6), round(fit[3],6),
                    round(1-fit[0],6), 1 if vio<0.01 else 0])
print(f"  [OK] {csv_path}")

# 图表数据
chart_data = {
    'pareto_f1': [round(pf[1][0], 4) for pf in feasible_pareto[:30]],
    'pareto_f2': [round(pf[1][1], 4) for pf in feasible_pareto[:30]],
    'pareto_f3': [round(pf[1][2], 4) for pf in feasible_pareto[:30]],
    'pareto_f4': [round(pf[1][3], 4) for pf in feasible_pareto[:30]],
    'pareto_pconn': [round(1-pf[1][0], 4) for pf in feasible_pareto[:30]],
    'pareto_n': [round(pf[0][0], 0) for pf in feasible_pareto[:30]],
    'entropy_weights': [round(w, 4) for w in weights_entropy],
    'ideal_point': [round(v, 4) for v in z_star],
    'n_feasible': len(feasible_pareto),
    'n_pareto': len(pareto_front),
}
chart_json = os.path.join(OUT_DIR, 'q4_chart_data.json')
with open(chart_json, 'w', encoding='utf-8') as f:
    json.dump(chart_data, f, ensure_ascii=False)
print(f"  [OK] {chart_json}")

# 结论
print(f"\n" + "=" * 70)
print("Q4 关键结论")
print("=" * 70)
print(f"""
1. Pareto前沿: {len(pareto_front)}个非支配解({len(feasible_pareto)}个可行)
   理想点 z* = {[round(v,4) for v in z_star]}

2. 熵权法客观权重:
   f1(导电性)={weights_entropy[0]:.3f}, f2(成本)={weights_entropy[1]:.3f},
   f3(重量)={weights_entropy[2]:.3f}, f4(力学)={weights_entropy[3]:.3f}
   → 数据驱动赋权，避免主观偏差

3. TOPSIS推荐方案:
""")
if best_solution:
    print(f"   N={best_solution[0][0]:.0f}, mu_r={best_solution[0][1]:.0f}, cv_r={best_solution[0][2]:.2f}, "
          f"s={best_solution[0][3]:.2f}, strategy={int(best_solution[0][4])}")
    print(f"   P_conn={1-best_solution[1][0]:.2%}, N/Nmax={best_solution[1][1]:.3f}, "
          f"phi={best_solution[1][2]:.3f}, E/E0={1-best_solution[1][3]:.3f}")
else:
    print("   (可行解不足，未生成推荐)")

print(f"""
4. 工程意义:
   - Pareto前沿给出了"导电性-成本-重量-力学"的完整权衡曲面
   - 工程师可根据实际预算/重量限制在Pareto前沿上选择方案
   - TOPSIS推荐方案在四个目标之间实现了最优平衡
""")

print("=" * 70)
print("Q4 MOEA/D-PAGCM 求解完成!")
print("=" * 70)
