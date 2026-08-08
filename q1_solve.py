# -*- coding: utf-8 -*-
"""
A题 第一问 完整求解代码 (纯Python标准库版)
===========================================
PAGCM：周期边界自适应图连通判定模型
依赖：仅 Python 标准库 (math, json, csv, os, random, time, collections)
"""
import math, json, csv, os, sys, random, time
from collections import deque, defaultdict, Counter

# Fix encoding
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except: pass

# ============================================================
# 0. 配置参数
# ============================================================
R0      = 250.0     # 粒子基础几何半径
ALPHA   = 0.5       # 自适应系数
L       = 10000.0   # RVE 边长
R_SEARCH = 1500.0   # 局部密度搜索半径
MC_ROUNDS = 200     # MC轮数
MC_SIGMA  = 0.05 * R0  # 扰动标准差(粒子半径的5%)

# ============================================================
# 1. 工具函数
# ============================================================
def torus_dist(pi, pj, Lval=L):
    """环面距离 (周期感知欧氏距离)"""
    d2 = 0.0
    for dim in range(3):
        diff = abs(pi[dim] - pj[dim])
        d2 += min(diff, Lval - diff) ** 2
    return math.sqrt(d2)

def torus_kvec(pi, pj, Lval=L):
    """周期偏移矢量"""
    k = [0, 0, 0]
    for dim in range(3):
        diff = pj[dim] - pi[dim]
        if diff > Lval / 2:
            k[dim] = -1
        elif diff < -Lval / 2:
            k[dim] = +1
    return tuple(k)

def gauss_random(sigma):
    """Box-Muller 正态随机数 (无numpy)"""
    u1 = random.random()
    u2 = random.random()
    return sigma * math.sqrt(-2.0 * math.log(max(u1, 1e-10))) * math.cos(2.0 * math.pi * u2)

# ============================================================
# 2. PAGCM 核心类
# ============================================================
class PAGCM:
    """周期边界自适应图连通判定模型 (纯Python实现)"""

    def __init__(self, points_3d, r0=R0, alpha=ALPHA, Lval=L, r_search=R_SEARCH):
        self.pts_raw = [(float(p[0]), float(p[1]), float(p[2])) for p in points_3d]
        self.N       = len(self.pts_raw)
        self.r0      = r0
        self.alpha   = alpha
        self.L       = Lval
        self.r_search = r_search

        # 平移至 [0, L]
        shift = Lval / 2.0
        self.pts = [(x + shift, y + shift, z + shift) for x, y, z in self.pts_raw]

        # 结果存储
        self.r_eff         = [r0] * self.N
        self.adj_edges     = []
        self.parent        = list(range(self.N))
        self.rank          = [0] * self.N
        self.components    = [-1] * self.N
        self.n_components  = 0
        self.connectivity  = {}
        self.shortest_path = {}
        self.build_time    = 0.0
        self.solve_time    = 0.0
        self._grid         = None
        self._cell_size    = 0.0

    # ---- 2.1 自适应等效半径 ----
    def compute_adaptive_radius(self):
        rho_global = self.N / (self.L ** 3)
        r_eff = []

        for i in range(self.N):
            pi = self.pts[i]
            count = 0
            for j in range(self.N):
                if i == j: continue
                d = torus_dist(pi, self.pts[j], self.L)
                if d <= self.r_search:
                    count += 1

            if self.r_search > 0:
                vol = (4.0/3.0) * math.pi * (self.r_search ** 3)
                rho_local = count / vol if vol > 0 else rho_global
            else:
                rho_local = rho_global

            ratio = rho_local / max(rho_global, 1e-30)
            re = self.r0 * (1.0 + self.alpha * (ratio - 1.0))
            re = max(0.5 * self.r0, min(3.0 * self.r0, re))
            r_eff.append(re)

        self.r_eff = r_eff
        return r_eff

    # ---- 2.2 空间网格加速（替代KD-Tree）----
    def _build_grid(self, max_radius):
        """构建简单空间网格用于加速近邻搜索"""
        self._cell_size = max(2.0 * max_radius, self.L / 50.0)
        n_cells = max(1, int(self.L / self._cell_size))
        grid = {}
        for i, pt in enumerate(self.pts):
            cx = int(pt[0] / self._cell_size) % n_cells
            cy = int(pt[1] / self._cell_size) % n_cells
            cz = int(pt[2] / self._cell_size) % n_cells
            key = (cx, cy, cz)
            grid.setdefault(key, []).append(i)
        self._grid = grid

    def _query_neighbors(self, pi, radius):
        """网格查询近邻粒子索引"""
        if self._grid is None:
            return list(range(self.N))

        neighbors = set()
        n_cells = max(1, int(self.L / self._cell_size))
        cx = int(pi[0] / self._cell_size) % n_cells
        cy = int(pi[1] / self._cell_size) % n_cells
        cz = int(pi[2] / self._cell_size) % n_cells

        # 搜索相邻27个格元
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    key = ((cx + dx) % n_cells, (cy + dy) % n_cells, (cz + dz) % n_cells)
                    for j in self._grid.get(key, []):
                        neighbors.add(j)

        return list(neighbors)

    # ---- 2.3 图构建 ----
    def build_graph(self):
        t0 = time.time()
        edges = []

        max_r = max(self.r_eff) if self.r_eff else self.r0
        self._build_grid(3.0 * max_r)

        for i in range(self.N):
            pi = self.pts[i]
            ri = self.r_eff[i]
            neighbors = self._query_neighbors(pi, 3.0 * max_r)

            for j in neighbors:
                if j <= i: continue
                pj = self.pts[j]
                rj = self.r_eff[j]
                d = torus_dist(pi, pj, self.L)

                if d <= ri + rj:
                    kvec = torus_kvec(pi, pj, self.L)
                    edges.append((i, j, kvec, d))

        self.adj_edges = edges
        self.build_time = time.time() - t0
        return edges

    # ---- 2.4 并查集 ----
    def union_find_cluster(self):
        t0 = time.time()
        n = self.N
        self.parent = list(range(n))
        self.rank = [0] * n

        def find(x):
            while self.parent[x] != x:
                self.parent[x] = self.parent[self.parent[x]]
                x = self.parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx == ry: return
            if self.rank[rx] < self.rank[ry]:
                self.parent[rx] = ry
            elif self.rank[rx] > self.rank[ry]:
                self.parent[ry] = rx
            else:
                self.parent[ry] = rx
                self.rank[rx] += 1

        for i, j, kvec, d in self.adj_edges:
            union(i, j)

        comp_labels = [find(i) for i in range(n)]
        roots = list(set(comp_labels))
        root_map = {r: idx for idx, r in enumerate(roots)}
        self.components = [root_map[c] for c in comp_labels]
        self.n_components = len(roots)
        self.solve_time = time.time() - t0
        return self.components

    # ---- 2.5 方向连通判定 ----
    def check_connectivity(self, direction='X'):
        dim_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis = dim_map[direction]

        lo_set = set()
        hi_set = set()
        for i in range(self.N):
            coord = self.pts[i][axis]
            ri = self.r_eff[i]
            if coord - ri <= 0:         lo_set.add(i)
            if coord + ri >= self.L:    hi_set.add(i)

        for i in lo_set:
            ci = self.components[i]
            for j in hi_set:
                if ci == self.components[j]:
                    self.connectivity[direction] = True
                    self.shortest_path[direction] = self._bfs_path(i, j)
                    return True

        self.connectivity[direction] = False
        self.shortest_path[direction] = []
        return False

    def _bfs_path(self, source, target):
        adj = [[] for _ in range(self.N)]
        for i, j, kvec, d in self.adj_edges:
            adj[i].append(j)
            adj[j].append(i)

        queue = deque([source])
        visited = {source: None}
        found = False
        while queue:
            u = queue.popleft()
            if u == target:
                found = True
                break
            for v in adj[u]:
                if v not in visited:
                    visited[v] = u
                    queue.append(v)

        if not found:
            return []
        path = []
        cur = target
        while cur is not None:
            path.append(cur)
            cur = visited[cur]
        path.reverse()
        return path

    # ---- 2.6 完整求解 ----
    def solve(self, verbose=True):
        if verbose:
            print(f"  [PAGCM] N={self.N} ...")
        t0 = time.time()

        self.compute_adaptive_radius()
        if verbose:
            mean_re = sum(self.r_eff) / self.N
            print(f"    r_eff: mean={mean_re:.1f}, min={min(self.r_eff):.1f}, max={max(self.r_eff):.1f}")

        self.build_graph()
        if verbose:
            print(f"    edges: {len(self.adj_edges)}, build={self.build_time:.3f}s")

        self.union_find_cluster()
        if verbose:
            print(f"    components: {self.n_components}, solve={self.solve_time:.3f}s")

        for d in ['X', 'Y', 'Z']:
            conn = self.check_connectivity(d)
            plen = len(self.shortest_path.get(d, []))
            if verbose:
                print(f"    {d}: {'连通' if conn else '不连通'} (path={plen})")

        if verbose:
            print(f"    total={time.time()-t0:.3f}s")
        return self.connectivity

    def solve_quiet(self):
        """静默求解"""
        self.compute_adaptive_radius()
        self.build_graph()
        self.union_find_cluster()
        for d in ['X', 'Y', 'Z']:
            self.check_connectivity(d)

    # ---- 2.7 统计 ----
    def stats(self):
        cnt = Counter(self.components)
        sizes = list(cnt.values())
        return {
            'N': self.N,
            'n_components': self.n_components,
            'max_cluster': max(sizes) if sizes else 0,
            'min_cluster': min(sizes) if sizes else 0,
            'mean_cluster': sum(sizes)/len(sizes) if sizes else 0,
            'singletons': sum(1 for s in sizes if s == 1),
            'n_edges': len(self.adj_edges),
            'r_eff_mean': sum(self.r_eff)/len(self.r_eff) if self.r_eff else 0,
            'r_eff_std': (sum((x - sum(self.r_eff)/len(self.r_eff))**2 for x in self.r_eff)/len(self.r_eff))**0.5 if self.r_eff else 0,
        }

    # ---- 2.8 蒙特卡洛 ----
    def mc_perturbation(self, n_rounds=MC_ROUNDS, sigma=MC_SIGMA):
        results = {d: 0 for d in ['X', 'Y', 'Z']}
        pts = self.pts_raw
        N = self.N
        Lval = self.L

        for rnd in range(n_rounds):
            perturb = []
            for x, y, z in pts:
                nx = x + gauss_random(sigma)
                ny = y + gauss_random(sigma)
                nz = z + gauss_random(sigma)
                half = Lval / 2.0
                perturb.append((
                    max(-half, min(half, nx)),
                    max(-half, min(half, ny)),
                    max(-half, min(half, nz))
                ))

            m = PAGCM(perturb, self.r0, self.alpha, Lval, self.r_search)
            m.solve_quiet()
            for d in ['X', 'Y', 'Z']:
                if m.connectivity.get(d, False):
                    results[d] += 1

        probs = {d: results[d] / n_rounds for d in results}
        return probs, results


# ============================================================
# 3. GPNM 基础模型（暴力对比）
# ============================================================
class GPNM:
    def __init__(self, points_3d, r0=R0, Lval=L):
        self.pts_raw = [(float(p[0]), float(p[1]), float(p[2])) for p in points_3d]
        self.N = len(self.pts_raw)
        self.r0 = r0
        self.L = Lval
        shift = Lval / 2.0
        self.pts = [(x + shift, y + shift, z + shift) for x, y, z in self.pts_raw]
        self.connectivity = {}

    def solve(self):
        N = self.N
        r0 = self.r0
        Lval = self.L
        adj = [[] for _ in range(N)]

        for i in range(N):
            pi = self.pts[i]
            for j in range(i+1, N):
                d = torus_dist(pi, self.pts[j], Lval)
                if d <= 2 * r0:
                    adj[i].append(j)
                    adj[j].append(i)

        visited = [False] * N
        comp = [-1] * N
        cid = 0
        for i in range(N):
            if not visited[i]:
                stack = [i]
                visited[i] = True
                while stack:
                    u = stack.pop()
                    comp[u] = cid
                    for v in adj[u]:
                        if not visited[v]:
                            visited[v] = True
                            stack.append(v)
                cid += 1

        for d in ['X', 'Y', 'Z']:
            axis = {'X':0, 'Y':1, 'Z':2}[d]
            lo = {i for i in range(N) if self.pts[i][axis] - r0 <= 0}
            hi = {i for i in range(N) if self.pts[i][axis] + r0 >= Lval}
            conn = False
            for i in lo:
                for j in hi:
                    if comp[i] == comp[j]:
                        conn = True
                        break
                if conn: break
            self.connectivity[d] = conn

        return self.connectivity


# ============================================================
# 4. 数据加载
# ============================================================
JSON_PATH = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\预处理输出\all_datasets.json"

def load_data():
    if not os.path.exists(JSON_PATH):
        # 回退：直接读取
        print("[WARN] 预处理JSON未找到，请先运行 preprocess.py")
        sys.exit(1)
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

print("=" * 70)
print("PAGCM 第一问完整求解 — 纯Python标准库实现")
print("=" * 70)
print(f"参数: r0={R0}, alpha={ALPHA}, L={L}, MC rounds={MC_ROUNDS}")
print()

all_data = load_data()
for k, v in all_data.items():
    print(f"  {k}: N={v['N']}")
print()

# ============================================================
# 5. 运行求解
# ============================================================
print("=" * 70)
print("阶段一：PAGCM求解（全部6个数据集）")
print("=" * 70)

all_results = {}
all_stats_data = {}

for name, ds in all_data.items():
    print(f"\n--- {name} ---")
    pts = list(zip(ds['X'], ds['Y'], ds['Z']))

    # PAGCM
    m = PAGCM(pts, r0=R0, alpha=ALPHA, Lval=L)
    m.solve(verbose=True)
    all_results[name] = {
        'PAGCM': dict(m.connectivity),
        'stats': m.stats(),
        'paths': {d: m.shortest_path.get(d, []) for d in ['X','Y','Z']},
    }

    # GPNM
    g = GPNM(pts, r0=R0, Lval=L)
    g.solve()
    all_results[name]['GPNM'] = dict(g.connectivity)
    all_stats_data[name] = m.stats()

    p_str = '/'.join(['1' if m.connectivity.get(d) else '0' for d in ['X','Y','Z']])
    g_str = '/'.join(['1' if g.connectivity.get(d) else '0' for d in ['X','Y','Z']])
    print(f"  => PAGCM=[{p_str}]  GPNM=[{g_str}]  edges={m.stats()['n_edges']}  comps={m.stats()['n_components']}")

# 交叉验证
print("\n--- 交叉验证 (PAGCM vs GPNM) ---")
mismatch = 0
for name in all_data:
    for d in ['X','Y','Z']:
        if all_results[name]['PAGCM'][d] != all_results[name]['GPNM'][d]:
            print(f"  [不匹配!] {name} {d}: PAGCM={all_results[name]['PAGCM'][d]}, GPNM={all_results[name]['GPNM'][d]}")
            mismatch += 1
if mismatch == 0:
    print("  [OK] 全部18个方向判定一致")

# ============================================================
# 6. 蒙特卡洛
# ============================================================
print("\n" + "=" * 70)
print("阶段二：蒙特卡洛扰动分析")
print("=" * 70)

mc_data = {}
for name in ['组1_场景A', '组1_场景B', '组3_场景A']:
    ds = all_data[name]
    pts = list(zip(ds['X'], ds['Y'], ds['Z']))
    m = PAGCM(pts, r0=R0, alpha=ALPHA, Lval=L)
    m.solve_quiet()
    probs, counts = m.mc_perturbation(n_rounds=MC_ROUNDS)
    mc_data[name] = {'probs': probs, 'counts': counts}
    print(f"  {name}: P_conn[X]={probs['X']:.3f}  P_conn[Y]={probs['Y']:.3f}  P_conn[Z]={probs['Z']:.3f}")

# ============================================================
# 7. 敏感性
# ============================================================
print("\n" + "=" * 70)
print("阶段三：参数敏感性分析")
print("=" * 70)

for name in ['组1_场景A', '组3_场景A']:
    ds = all_data[name]
    pts = list(zip(ds['X'], ds['Y'], ds['Z']))
    base_conn = all_results[name]['PAGCM']
    print(f"\n  [{name}] 基准: ", base_conn)

    # Alpha +/-20%
    for a_val, a_lbl in [(ALPHA*0.8, '-20%'), (ALPHA*1.2, '+20%')]:
        m = PAGCM(pts, r0=R0, alpha=a_val, Lval=L)
        m.solve_quiet()
        chg = [d for d in ['X','Y','Z'] if base_conn[d] != m.connectivity[d]]
        st = f"变化:{','.join(chg)}" if chg else "稳定"
        print(f"    alpha{a_lbl}({a_val:.1f}): {st}  conn={m.connectivity}")

    # r0 +/-10%
    for r_val, r_lbl in [(R0*0.9, '-10%'), (R0*1.1, '+10%')]:
        m = PAGCM(pts, r0=r_val, alpha=ALPHA, Lval=L)
        m.solve_quiet()
        chg = [d for d in ['X','Y','Z'] if base_conn[d] != m.connectivity[d]]
        st = f"变化:{','.join(chg)}" if chg else "稳定"
        print(f"    r0{r_lbl}({r_val:.1f}): {st}  conn={m.connectivity}")

# ============================================================
# 8. 结果汇总
# ============================================================
print("\n" + "=" * 70)
print("结果汇总表")
print("=" * 70)

hdr = f"{'数据集':20s} {'N':>5s} {'X':>6s} {'Y':>6s} {'Z':>6s} {'边数':>7s} {'分量':>5s} {'最大簇':>6s}"
print(hdr)
print("-" * len(hdr))
for name in all_data:
    s = all_stats_data[name]
    c = all_results[name]['PAGCM']
    print(f"{name:20s} {s['N']:5d} {'通' if c['X'] else '断':>6s} "
          f"{'通' if c['Y'] else '断':>6s} {'通' if c['Z'] else '断':>6s} "
          f"{s['n_edges']:7d} {s['n_components']:5d} {s['max_cluster']:6d}")

# ============================================================
# 9. 保存结果
# ============================================================
OUT_DIR = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\求解输出"
os.makedirs(OUT_DIR, exist_ok=True)

out = {
    'parameters': {'r0': R0, 'alpha': ALPHA, 'L': L, 'MC_rounds': MC_ROUNDS},
    'connectivity': {n: all_results[n]['PAGCM'] for n in all_results},
    'GPNM_verify': {n: all_results[n]['GPNM'] for n in all_results},
    'stats': {n: all_stats_data[n] for n in all_stats_data},
    'mc_probabilities': {n: mc_data[n]['probs'] for n in mc_data},
}

with open(os.path.join(OUT_DIR, 'pagcm_results.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# 汇总CSV
csv_path = os.path.join(OUT_DIR, 'connectivity_summary.csv')
with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['数据集', 'N', 'X连通', 'Y连通', 'Z连通', '边数', '连通分量数', '最大簇大小',
                'r_eff均值', 'MC_Pconn_X', 'MC_Pconn_Y', 'MC_Pconn_Z'])
    for name in all_data:
        s = all_stats_data[name]
        c = all_results[name]['PAGCM']
        mc = mc_data.get(name, {}).get('probs', {})
        w.writerow([name, s['N'], c['X'], c['Y'], c['Z'], s['n_edges'], s['n_components'],
                    s['max_cluster'], f"{s['r_eff_mean']:.1f}",
                    f"{mc.get('X',0):.3f}", f"{mc.get('Y',0):.3f}", f"{mc.get('Z',0):.3f}"])

print(f"\n[OK] 结果保存至: {OUT_DIR}")
print(f"     - pagcm_results.json")
print(f"     - connectivity_summary.csv")
print("\n" + "=" * 70)
print("PAGCM 第一问求解完成!")
print("=" * 70)
