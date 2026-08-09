# -*- coding: utf-8 -*-
"""
Q2 MESA-PAGCM 完整求解器
========================
最大熵模拟退火周期自适应图连通优化模型
(Maximum Entropy Simulated Annealing with PAGCM)

创新方向2: 跨领域模型迁移创新
  迁移1: 信息论MaxEnt -> 粒子空间均匀初始化
  迁移2: 统计物理SA -> 全局组合优化搜索
  迁移3: 冶金退火 -> 冷却策略锁定最优解

依赖: 纯Python标准库, 零外部依赖
用法: python q2_solve.py
"""
import math, json, csv, os, sys, random, time
from collections import defaultdict

if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except: pass

# ============================================================
# 0. 全局配置
# ============================================================
R0      = 250.0     # 粒子基础几何半径
ALPHA   = 0.5       # PAGCM自适应系数 (与Q1一致)
L_VAL   = 10000.0   # RVE边长
R_SEARCH = 1500.0   # 局部密度搜索半径

# MESA超参数
T0      = 50.0      # 初始温度
GAMMA   = 0.95      # 冷却因子
T_MIN   = 0.01      # 终止温度
LAMBDA  = 2.0       # 罚函数权重
M0      = 50        # 每温度扰动次数 (演示值, 论文用100)
P_TARGET = 0.95     # 目标连通概率
BETA    = 0.70      # MaxEnt最小间距因子
N_RESTARTS = 3      # 多重启动次数 (演示值, 论文用5)

# ============================================================
# 1. PAGCM评估器 (复用Q1核心逻辑)
# ============================================================
def torus_dist(pi, pj, Lval=L_VAL):
    """环面距离: 周期边界下两粒子最短距离"""
    d2 = 0.0
    for dim in range(3):
        diff = abs(pi[dim] - pj[dim])
        d2 += min(diff, Lval - diff) ** 2
    return math.sqrt(d2)

class FastPAGCM:
    """PAGCM快速评估器: 用于SA内循环的轻量版"""

    def __init__(self, particles, r0=R0, alpha=ALPHA, Lval=L_VAL):
        self.pts_raw = [(float(p[0]), float(p[1]), float(p[2])) for p in particles]
        self.N = len(self.pts_raw)
        self.r0 = r0; self.alpha = alpha; self.L = Lval
        shift = Lval / 2.0
        self.pts = [(x+shift, y+shift, z+shift) for x,y,z in self.pts_raw]
        self.r_eff = [r0] * self.N
        self.connectivity = {'X': False, 'Y': False, 'Z': False}

    def compute_adaptive_radius(self):
        """密度感知自适应等效半径"""
        rho_global = self.N / (self.L ** 3)
        for i in range(self.N):
            pi = self.pts[i]; count = 0
            for j in range(self.N):
                if i == j: continue
                if torus_dist(pi, self.pts[j], self.L) <= R_SEARCH:
                    count += 1
            if R_SEARCH > 0:
                rho_local = count / (4.0/3.0*math.pi*R_SEARCH**3)
            else:
                rho_local = rho_global
            ratio = rho_local / max(rho_global, 1e-30)
            re = self.r0 * (1.0 + self.alpha * (ratio - 1.0))
            self.r_eff[i] = max(0.5*self.r0, min(3.0*self.r0, re))

    def build_and_cluster(self):
        """建图 + 并查集聚类"""
        edges = []
        for i in range(self.N):
            pi = self.pts[i]; ri = self.r_eff[i]
            for j in range(i+1, self.N):
                pj = self.pts[j]; rj = self.r_eff[j]
                if torus_dist(pi, pj, self.L) <= ri + rj:
                    edges.append((i, j))

        parent = list(range(self.N)); rank = [0]*self.N
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(x, y):
            rx, ry = find(x), find(y)
            if rx == ry: return
            if rank[rx] < rank[ry]: parent[rx] = ry
            elif rank[rx] > rank[ry]: parent[ry] = rx
            else: parent[ry] = rx; rank[rx] += 1
        for i, j in edges: union(i, j)
        self.components = [find(i) for i in range(self.N)]

    def check_all(self):
        """三方向连通判定"""
        for d, axis in [('X',0),('Y',1),('Z',2)]:
            lo = {i for i in range(self.N) if self.pts[i][axis]-self.r_eff[i] <= 0}
            hi = {i for i in range(self.N) if self.pts[i][axis]+self.r_eff[i] >= self.L}
            conn = False
            for i in lo:
                for j in hi:
                    if self.components[i] == self.components[j]:
                        conn = True; break
                if conn: break
            self.connectivity[d] = conn
        return self.connectivity

    def evaluate(self):
        """完整评估: 返回P_conn"""
        self.compute_adaptive_radius()
        self.build_and_cluster()
        self.check_all()
        return sum(1 for v in self.connectivity.values() if v) / 3.0

# ============================================================
# 2. MaxEnt初始化 (迁移1: 信息论 -> 材料)
# ============================================================
def maxent_init(N, Lval=L_VAL, beta=BETA):
    """泊松盘采样近似最大熵分布: 均匀但有最小间距约束"""
    particles = []
    d_min = (Lval**3 / max(N, 1)) ** (1/3) * beta
    max_attempts = N * 50
    attempts = 0

    while len(particles) < N and attempts < max_attempts:
        x = random.uniform(0, Lval)
        y = random.uniform(0, Lval)
        z = random.uniform(0, Lval)
        ok = True
        for px, py, pz in particles:
            d2 = (x-px)**2 + (y-py)**2 + (z-pz)**2
            if d2 < d_min**2:
                ok = False; break
        if ok:
            particles.append((x-Lval/2, y-Lval/2, z-Lval/2))
        attempts += 1

    # If we couldn't place all particles, fill remaining randomly
    while len(particles) < N:
        x = random.uniform(-Lval/2, Lval/2)
        y = random.uniform(-Lval/2, Lval/2)
        z = random.uniform(-Lval/2, Lval/2)
        particles.append((x, y, z))

    return particles

# ============================================================
# 3. 扰动算子
# ============================================================
def displace(particles, sigma_d):
    """位移扰动: 随机选一颗粒子, 高斯位移"""
    parts = list(particles)
    i = random.randint(0, len(parts)-1)
    x, y, z = parts[i]
    half = L_VAL / 2.0
    nx = max(-half, min(half, x + random.gauss(0, sigma_d)))
    ny = max(-half, min(half, y + random.gauss(0, sigma_d)))
    nz = max(-half, min(half, z + random.gauss(0, sigma_d)))
    parts[i] = (nx, ny, nz)
    return parts

def add_particle(particles):
    """增粒: 在随机位置添加一颗粒子"""
    parts = list(particles)
    half = L_VAL / 2.0
    x = random.uniform(-half, half)
    y = random.uniform(-half, half)
    z = random.uniform(-half, half)
    parts.append((x, y, z))
    return parts

def delete_particle(particles):
    """删粒: 随机删除一颗粒子 (至少保留6个)"""
    if len(particles) <= 6:
        return list(particles)
    parts = list(particles)
    i = random.randint(0, len(parts)-1)
    parts.pop(i)
    return parts

# ============================================================
# 4. MESA主优化循环
# ============================================================
def mesa_optimize(N_min, N_max, seed=None):
    """MESA-PAGCM主优化: 返回最优粒子排布和评估结果"""
    if seed is not None:
        random.seed(seed)

    N_curr = (N_min + N_max) // 2
    particles = maxent_init(N_curr)

    # 初始评估
    model = FastPAGCM(particles)
    Pc = model.evaluate()
    f_curr = N_curr/N_max + LAMBDA * max(0, P_TARGET - Pc)

    best_particles = list(particles)
    best_N = N_curr
    best_Pc = Pc
    best_f = f_curr

    T = T0
    n_rounds = 0
    no_improve = 0

    while T > T_MIN and no_improve < 20:
        for _ in range(M0):
            # 随机选扰动操作
            op = random.choice(['displace', 'add', 'delete'])
            sigma_d = L_VAL * (T / T0) ** 0.5 * 0.05

            if op == 'displace':
                parts_new = displace(particles, sigma_d)
            elif op == 'add':
                parts_new = add_particle(particles)
            else:
                parts_new = delete_particle(particles)

            if len(parts_new) < 6 or len(parts_new) > N_max:
                continue

            # PAGCM评估候选解
            m = FastPAGCM(parts_new)
            Pc_new = m.evaluate()
            f_new = len(parts_new)/N_max + LAMBDA * max(0, P_TARGET - Pc_new)

            # Metropolis接受准则
            delta_f = f_new - f_curr
            if delta_f < 0 or random.random() < math.exp(-delta_f / T):
                particles = parts_new
                N_curr = len(parts_new)
                f_curr = f_new
                Pc = Pc_new

                if f_curr < best_f:
                    best_particles = list(particles)
                    best_N = N_curr
                    best_Pc = Pc
                    best_f = f_curr
                    no_improve = 0

        T *= GAMMA
        n_rounds += 1
        if f_curr >= best_f * 1.001:  # no significant improvement
            no_improve += 1
        else:
            no_improve = 0

    return {
        'particles': best_particles,
        'N': best_N,
        'P_conn': best_Pc,
        'f': best_f,
        'rounds': n_rounds,
    }

# ============================================================
# 5. 主程序
# ============================================================
def main():
    print("=" * 70)
    print("Q2 MESA-PAGCM 最大熵模拟退火优化求解器")
    print("=" * 70)
    print(f"参数: T0={T0}, gamma={GAMMA}, lambda={LAMBDA}, P_target={P_TARGET}")
    print(f"      M0={M0}, beta={BETA}, n_restarts={N_RESTARTS}")
    print()

    # 加载Q1结果
    q1_json = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\求解输出\pagcm_results.json"
    data_json = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\预处理输出\all_datasets.json"

    optimization_targets = []
    if os.path.exists(q1_json) and os.path.exists(data_json):
        with open(q1_json, 'r', encoding='utf-8') as f:
            q1 = json.load(f)
        with open(data_json, 'r', encoding='utf-8') as f:
            pdata = json.load(f)

        for name, conn in q1.get('connectivity', {}).items():
            n_conn = sum(1 for d in ['X','Y','Z'] if conn.get(d, False))
            if n_conn < 3 and name in pdata:
                optimization_targets.append({
                    'name': name,
                    'N_orig': pdata[name]['N'],
                    'n_connected': n_conn,
                    'target_dirs': [d for d in ['X','Y','Z'] if not conn.get(d, False)],
                })
        print(f"加载 {len(optimization_targets)} 个优化目标 (来自Q1结果)")
    else:
        print("[WARN] Q1结果未找到, 使用默认参数")
        optimization_targets = [
            {'name': '组1_场景A', 'N_orig': 12, 'n_connected': 0, 'target_dirs': ['X','Y','Z']},
            {'name': '组2_场景B', 'N_orig': 49, 'n_connected': 0, 'target_dirs': ['X','Y','Z']},
        ]

    # 逾渗理论推算N_min和N_max
    phi_c = 0.29
    vol_sphere = (4.0/3.0) * math.pi * (R0 ** 3)
    N_critical = int(phi_c * (L_VAL ** 3) / vol_sphere)
    N_MIN = max(6, int(N_critical * 0.15))
    N_MAX = int(N_critical * 3.0)
    print(f"逾渗理论: phi_c={phi_c}, N_c={N_critical}")
    print(f"搜索范围: N in [{N_MIN}, {N_MAX}]")
    print()

    # 对每个优化目标运行MESA
    results = []
    for target in optimization_targets:
        name = target['name']
        print(f"\n{'='*50}")
        print(f"优化: {name} (原始N={target['N_orig']}, {target['n_connected']}/3连通)")
        print(f"目标方向: {target['target_dirs']}")
        print(f"{'='*50}")

        best_overall = None
        all_Ns = []

        for restart in range(N_RESTARTS):
            seed = hash(name + str(restart)) % 100000
            t0 = time.time()
            result = mesa_optimize(N_MIN, N_MAX, seed=seed)
            elapsed = time.time() - t0
            all_Ns.append(result['N'])
            print(f"  重启{restart+1}/{N_RESTARTS}: N*={result['N']}, "
                  f"P_conn={result['P_conn']:.3f}, f={result['f']:.4f}, "
                  f"rounds={result['rounds']}, time={elapsed:.1f}s")
            if best_overall is None or result['f'] < best_overall['f']:
                best_overall = result

        mean_N = sum(all_Ns) / len(all_Ns)
        std_N = (sum((n-mean_N)**2 for n in all_Ns) / len(all_Ns)) ** 0.5
        print(f"  汇总: N*_mean={mean_N:.0f}, std={std_N:.0f} (CV={std_N/max(mean_N,1)*100:.1f}%)")
        print(f"  最优: N*={best_overall['N']}, P_conn={best_overall['P_conn']:.3f}, "
              f"f={best_overall['f']:.4f}")

        results.append({
            'dataset': name,
            'N_original': target['N_orig'],
            'N_optimal': best_overall['N'],
            'P_conn_optimal': best_overall['P_conn'],
            'f_optimal': best_overall['f'],
            'N_mean': mean_N,
            'N_std': std_N,
            'improvement': f"{target['N_orig']}->{best_overall['N']}",
        })

    # 输出汇总表
    print(f"\n{'='*70}")
    print("MESA-PAGCM 优化结果汇总")
    print(f"{'='*70}")
    print(f"{'数据集':20s} {'原始N':>6s} {'最优N':>6s} {'P_conn':>8s} {'N均值':>8s} {'CV':>6s}")
    print(f"{'-'*60}")
    for r in results:
        cv = r['N_std']/max(r['N_mean'],1)*100
        print(f"{r['dataset']:20s} {r['N_original']:6d} {r['N_optimal']:6d} "
              f"{r['P_conn_optimal']:8.3f} {r['N_mean']:8.0f} {cv:6.1f}%")

    # 保存结果
    out_dir = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\第二问输出"
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, 'q2_mesa_results.json'), 'w', encoding='utf-8') as f:
        json.dump({
            'parameters': {'T0':T0,'gamma':GAMMA,'lambda':LAMBDA,'P_target':P_TARGET,
                          'M0':M0,'beta':BETA,'n_restarts':N_RESTARTS,
                          'N_min':N_MIN,'N_max':N_MAX,'N_critical':N_critical},
            'results': results,
        }, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(out_dir, 'q2_mesa_results.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['数据集','原始N','最优N','P_conn','f值','N均值','N标准差','CV%'])
        for r in results:
            cv = r['N_std']/max(r['N_mean'],1)*100
            w.writerow([r['dataset'],r['N_original'],r['N_optimal'],
                       f"{r['P_conn_optimal']:.4f}",f"{r['f_optimal']:.4f}",
                       f"{r['N_mean']:.0f}",f"{r['N_std']:.0f}",f"{cv:.1f}"])

    print(f"\n结果已保存: {out_dir}")
    print("MESA-PAGCM 求解完成!")

if __name__ == '__main__':
    main()
