# -*- coding: utf-8 -*-
"""
Q1 PAGCM v3 — 新增: 量子隧穿概率层 (Tunneling-Augmented PAGCM)
========================================================================
v3创新点: 在二值接触判据(d_T <= ri+rj)之上叠加一层基于量子隧穿的
          概率连接模型, 将纯几何逾渗扩展为"几何+隧穿"混合逾渗。

【创新原理】
  原v1/v2: 粒子连接是二值的——碰到就连, 碰不到就断。
  问题: 真实纳米复合材料中, 即使两粒子间距超过几何接触距离,
        只要间距在隧穿截止距离内(约1-10nm), 电子仍可通过量子
        隧穿效应传导——这是一种"概率连接"。

  v3方案: 在几何边的基础上, 添加"隧穿边"。
          对间距在(ri+rj, ri+rj+xi_tunnel]范围内的粒子对,
          以概率p=exp(-d_ij/xi)建立连接。
          多轮采样统计平均连通概率。

【改动量】仅新增约30行, 核心PAGCM逻辑不变, 完全向后兼容(可关闭)
【文献依据】隧穿辅助逾渗模型 (Balberg 1987, Phys Rev B)
"""
import math, json, csv, os, sys, random, time
from collections import Counter

if sys.platform=='win32':
    try: import io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
    except: pass

# ==== 配置 ====
R0, ALPHA, L_VAL = 250.0, 0.5, 10000.0
R_SEARCH = 1500.0
XI_TUNNEL = 50.0    # ★v3新增: 隧穿特征长度(纳米填料约1-10nm, 微米填料取等效)
TUNNEL_SAMPLES = 50  # ★v3新增: 隧穿边采样轮数

# ==== 环面距离 ====
def torus_dist(pi, pj, Lval=L_VAL):
    d2 = 0.0
    for dim in range(3):
        direct = abs(pi[dim]-pj[dim])
        d2 += min(direct, Lval-direct)**2
    return math.sqrt(d2)

# ==== PAGCM v3 (含隧穿层) ====
class PAGCMv3:
    """
    v3新增: 量子隧穿概率连接层

    【隧穿物理】
    当两粒子间距d满足: ri+rj < d <= ri+rj+xi_tunnel 时,
    虽然没有几何接触, 但电子有一定概率通过量子隧穿传导。

    隧穿概率: p_tunnel(d) = exp(-(d - (ri+rj)) / xi_tunnel)

    xi_tunnel是隧穿特征长度, 取决于填料和基体的功函数差。
    典型值: 碳纳米管/聚合物约5-20nm, 金属/聚合物约1-5nm。
    在本题无量纲坐标系中取xi_tunnel=50(粒子半径250的20%)。
    """

    def __init__(self, points_3d, r0=R0, alpha=ALPHA, Lval=L_VAL,
                 xi_tunnel=XI_TUNNEL, use_tunnel=True):
        self.pts_raw = [(float(p[0]),float(p[1]),float(p[2]))for p in points_3d]
        self.N = len(self.pts_raw)
        self.r0, self.alpha, self.L = r0, alpha, Lval
        self.xi_tunnel = xi_tunnel
        self.use_tunnel = use_tunnel

        shift = Lval/2.0
        self.pts = [(x+shift,y+shift,z+shift)for x,y,z in self.pts_raw]
        self.r_eff = [r0]*self.N
        self.adj_edges = []    # 几何边
        self.tunnel_edges = [] # ★v3: 隧穿边(概率连接)
        self.components = [-1]*self.N
        self.n_components = 0
        self.connectivity = {'X':False,'Y':False,'Z':False}
        self.P_conn_tunnel = {'X':0.0,'Y':0.0,'Z':0.0} # ★v3: 隧穿连通概率

    def compute_adaptive_radius(self):
        rho_global = self.N/(self.L**3)
        for i in range(self.N):
            pi = self.pts[i]; count = 0
            for j in range(self.N):
                if i==j: continue
                if torus_dist(pi,self.pts[j],self.L)<=R_SEARCH: count+=1
            rho_local = count/(4.0/3.0*math.pi*R_SEARCH**3) if R_SEARCH>0 else rho_global
            ratio = rho_local/max(rho_global,1e-30)
            re = self.r0*(1.0+self.alpha*math.tanh(ratio-1.0))
            self.r_eff[i] = max(0.5*self.r0, min(3.0*self.r0, re))

    def build_graph(self):
        """建图: 几何边 + 隧穿候选边"""
        edges = []
        tunnel_candidates = []  # ★v3
        for i in range(self.N):
            pi,ri = self.pts[i],self.r_eff[i]
            for j in range(i+1,self.N):
                pj,rj = self.pts[j],self.r_eff[j]
                d = torus_dist(pi,pj,self.L)
                if d <= ri+rj:
                    edges.append((i,j))  # 确定性的几何边
                elif self.use_tunnel and d <= ri+rj+self.xi_tunnel:
                    p_t = math.exp(-(d-ri-rj)/self.xi_tunnel)  # ★隧穿概率
                    tunnel_candidates.append((i,j,p_t))

        self.adj_edges = edges
        self.tunnel_edges = tunnel_candidates

    def cluster_with_tunnel(self):
        """并查集聚类 + 多轮隧穿采样"""
        import copy
        n = self.N

        # 先做确定性几何边的聚类
        parent0, rank0 = list(range(n)), [0]*n
        def find(p,x):
            while p[x]!=x: p[x]=p[p[x]]; x=p[x]
            return x
        def union(p,r,x,y):
            rx,ry=find(p,x),find(p,y)
            if rx==ry: return
            if r[rx]<r[ry]: p[rx]=ry
            elif r[rx]>r[ry]: p[ry]=rx
            else: p[ry]=rx; r[rx]+=1

        for i,j in self.adj_edges:
            union(parent0,rank0,i,j)

        # 多轮隧穿采样: 每轮按概率激活隧穿边, 重新聚类, 统计连通性
        conn_counts = {'X':0,'Y':0,'Z':0}
        for _ in range(TUNNEL_SAMPLES):
            parent = list(parent0)  # 从几何边聚类结果开始
            rank   = list(rank0)
            for i,j,p_t in self.tunnel_edges:
                if random.random() < p_t:  # ★按照隧穿概率随机激活
                    union(parent,rank,i,j)

            comp = [find(parent,i) for i in range(n)]
            for d,axis in [('X',0),('Y',1),('Z',2)]:
                lo = {i for i in range(n) if self.pts[i][axis]-self.r_eff[i]<=0}
                hi = {i for i in range(n) if self.pts[i][axis]+self.r_eff[i]>=self.L}
                for i in lo:
                    for j in hi:
                        if comp[i]==comp[j]:
                            conn_counts[d] += 1; break
                    else: continue
                    break

        # 计算隧穿连通概率
        for d in ['X','Y','Z']:
            self.P_conn_tunnel[d] = conn_counts[d]/TUNNEL_SAMPLES
            self.connectivity[d] = self.P_conn_tunnel[d] > 0.5  # 超过50%概率认为连通

    def solve(self, verbose=True):
        if verbose:
            print(f"  [PAGCM v3] N={self.N}, xi_tunnel={self.xi_tunnel}"
                  f"{' (隧穿增强)' if self.use_tunnel else ''}")

        self.compute_adaptive_radius()
        if verbose:
            re_mean = sum(self.r_eff)/self.N
            print(f"    r_eff: 均值={re_mean:.1f}")

        self.build_graph()
        if verbose:
            n_geo = len(self.adj_edges)
            n_tun = len(self.tunnel_edges)
            print(f"    几何边={n_geo}, 隧穿候选边={n_tun}")

        self.cluster_with_tunnel()
        if verbose and self.use_tunnel:
            for d in ['X','Y','Z']:
                print(f"    方向{d}: P_tunnel={self.P_conn_tunnel[d]:.2f} "
                      f"→ {'连通' if self.connectivity[d] else '不连通'}")

        return self.connectivity


# ==== 主程序 ====
def main():
    print("="*60)
    print("PAGCM v3 — 量子隧穿增强型周期边界图连通模型")
    print(f"隧穿参数: xi_tunnel={XI_TUNNEL}, 采样轮数={TUNNEL_SAMPLES}")
    print("="*60)

    data_path = r"C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\预处理输出\all_datasets.json"
    if not os.path.exists(data_path):
        print("[错误] 请先运行 preprocess.py")
        return

    with open(data_path,'r',encoding='utf-8') as f:
        all_data = json.load(f)

    for name, ds in all_data.items():
        points = list(zip(ds['X'],ds['Y'],ds['Z']))
        print(f"\n--- {name} (N={ds['N']}) ---")

        # v3 隧穿增强
        m = PAGCMv3(points, use_tunnel=True)
        m.solve(verbose=True)

        if m.use_tunnel:
            for d in ['X','Y','Z']:
                if 0 < m.P_conn_tunnel[d] < 1:
                    print(f"    ★隧穿效应: {d}方向连通概率={m.P_conn_tunnel[d]:.2f}"
                          f"(介于0-1之间→隧穿提供了概率性导电通路)")

    print("\n"+"="*60)
    print("★ v3创新点验证: 隧穿层使纯几何逾渗升级为几何+隧穿混合逾渗")
    print("  优势: ①更贴合纳米复合材料实际(量子隧穿不可忽略)")
    print("        ②输出从二值→概率, 置信度信息更丰富")
    print("        ③xi_tunnel可标定至实验数据(物理可校准性)")
    print("="*60)

if __name__=='__main__':
    main()
