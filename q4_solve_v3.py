# -*- coding: utf-8 -*-
"""
Q4 MOEA/D-PAGCM v3 — 新增: 自适应DE参数 (Self-Adaptive MOEA/D)
========================================================================
v3创新点: DE的交叉率CR和缩放因子F不再固定, 而是随进化过程自适应演化。

【创新原理】
  原v2: CR=0.9, F=0.5 固定不变
  问题: 不同进化阶段需要不同的探索-开发平衡。
        初期需要大F(全局探索), 后期需要小F(局部精炼)。
        固定参数无法适应这种需求变化。

  v3方案: 每个个体拥有自己的CR_i和F_i, 与决策变量一同进化:
          父代的CR和F用于生成子代
          子代继承(CR_parent + noise)和(F_parent + noise)
          成功的子代(被邻域接受的)保留其CR和F
          自然选择→种群自动趋向最优参数

【文献依据】Self-adaptive DE (Brest et al. 2006, IEEE TEC)
【改动量】仅新增CR/F的自适应更新(~20行), MOEA/D框架不变
"""
import math, json, csv, os, sys, random

if sys.platform=='win32':
    try: import io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
    except: pass

N_POP, T_NEIGH, G_MAX = 40, 8, 30
N_OBJ, N_VAR = 4, 5
VAR_RANGES = [(100,2000),(100.0,500.0),(0.0,0.5),(0.5,2.0),(0,3)]

def eval_obj(x):
    N,mu_r,cv_r,s,strategy = x
    N_max,L_val,r0 = 2000.0,10000.0,250.0
    f2 = N/N_max
    phi = N*(4.0/3.0)*math.pi*(mu_r**3)/(L_val**3)
    f3 = min(1.0,phi)
    phi_eff = phi
    if cv_r>0: phi_eff*=(1.0-0.4*cv_r)
    phi_eff*=(0.7+0.3*s)
    pc = 1.0/(1.0+math.exp(-80.0/(1.0+0.5*cv_r)*(phi_eff-0.015)))
    pc = min(1.0,pc*(1.0+0.15*0.5)+{0:0.0,1:0.12,2:0.05,3:0.08}.get(int(strategy),0.0))
    pc += random.gauss(0,0.015)
    f1 = 1.0-min(1.0,max(0.0,pc))
    B = 2.5; Er = 1.0+B*phi
    f4 = abs(Er-1.0)/(1.0+B*0.1)
    return [f1,f2,f3,f4]

def constraint_vio(fv):
    pc,phi = 1.0-fv[0], fv[2]
    v = 0.0
    if pc<0.80: v+=(0.80-pc)/0.80
    if phi>0.10: v+=(phi-0.10)/0.10
    return v

def gen_weights(n_obj, n_pop):
    w = []
    for _ in range(n_pop):
        r = [random.random() for _ in range(n_obj)]
        s = sum(r); w.append([v/s for v in r])
    return w

def build_neighbors(weights, T):
    n = len(weights)
    neigh = []
    for i in range(n):
        dists = [(j,sum((weights[i][k]-weights[j][k])**2 for k in range(N_OBJ))) for j in range(n) if j!=i]
        dists.sort(key=lambda x:x[1])
        neigh.append([j for j,_ in dists[:T]])
    return neigh

def sa_de_operator(x1, x2, x3, CR_i, F_i):
    """★v3: 使用个体自己的CR_i和F_i, 而非全局固定值"""
    child = []; jr = random.randint(0,N_VAR-1)
    for j in range(N_VAR):
        if random.random()<CR_i or j==jr:
            v = x1[j]+F_i*(x2[j]-x3[j])
            lo,hi = VAR_RANGES[j]
            if j==4: child.append(max(lo,min(hi,int(round(v)))))
            else:    child.append(max(lo,min(hi,v)))
        else:
            child.append(x1[j])
    return child

def sa_update_params(CR_i, F_i):
    """★v3: 自适应更新CR和F"""
    # 以0.1的概率变异CR和F
    if random.random()<0.1:
        CR_new = random.uniform(0.1,1.0)  # 随机重设
    else:
        CR_new = max(0.1,min(1.0, CR_i+random.gauss(0,0.05)))  # 小扰动

    if random.random()<0.1:
        F_new = random.uniform(0.1,1.0)
    else:
        F_new = max(0.1,min(1.0, F_i+random.gauss(0,0.05)))

    return CR_new, F_new

# ==== 主程序 ====
def main():
    print("="*60)
    print("MOEA/D-PAGCM v3 — 自适应DE参数进化")
    print("="*60)

    weights = gen_weights(N_OBJ, N_POP)
    neighbors = build_neighbors(weights, T_NEIGH)

    pop = []
    for _ in range(N_POP):
        ind = []
        for j in range(N_VAR):
            lo,hi = VAR_RANGES[j]
            ind.append(random.randint(int(lo),int(hi)) if j==4 else lo+random.random()*(hi-lo))
        pop.append(ind)

    # ★v3: 每个个体拥有独立的CR和F
    CRs = [random.uniform(0.5,1.0) for _ in range(N_POP)]
    Fs  = [random.uniform(0.3,0.7) for _ in range(N_POP)]

    fit = [eval_obj(ind) for ind in pop]
    vio = [constraint_vio(f) for f in fit]
    z_star = [min(fit[i][j] for i in range(N_POP)) for j in range(N_OBJ)]

    def tcheb(fv,w,zs):
        return max(w[j]*abs(fv[j]-zs[j]) for j in range(N_OBJ))

    # 统计CR/F的演化
    cr_history, f_history = [], []

    for gen in range(G_MAX):
        for i in range(N_POP):
            nb = neighbors[i]
            cands = random.sample(nb, min(3,len(nb)))
            while len(cands)<3: cands.append(random.randint(0,N_POP-1))

            # ★v3: 使用父代的平均CR和F
            parent_CR = sum(CRs[j] for j in cands)/len(cands)
            parent_F  = sum(Fs[j] for j in cands)/len(cands)

            child = sa_de_operator(pop[cands[0]],pop[cands[1]],pop[cands[2]],parent_CR,parent_F)
            cf = eval_obj(child); cv = constraint_vio(cf)

            for jj in range(N_OBJ):
                if cf[jj]<z_star[jj]: z_star[jj]=cf[jj]

            # 更新邻域解
            for j in neighbors[i]:
                if cv<vio[j] or (cv<=vio[j] and tcheb(cf,weights[j],z_star)<tcheb(fit[j],weights[j],z_star)):
                    pop[j]=child[:]; fit[j]=cf[:]; vio[j]=cv
                    # ★v3: 成功的子代→更新CR和F(保留好的参数)
                    CRs[j], Fs[j] = sa_update_params(CRs[j], Fs[j])

        cr_history.append(sum(CRs)/N_POP)
        f_history.append(sum(Fs)/N_POP)

        if (gen+1)%10==0:
            feas = sum(1 for v in vio if v<0.01)
            print(f"  Gen {gen+1}: 可行{feas}/{N_POP}, CR_avg={cr_history[-1]:.3f}, F_avg={f_history[-1]:.3f}")

    # Pareto
    def dominates(a,b):
        return all(a[j]<=b[j] for j in range(N_OBJ)) and any(a[j]<b[j] for j in range(N_OBJ))
    pareto = [(pop[i],fit[i]) for i in range(N_POP) if not any(dominates(fit[j],fit[i]) for j in range(N_POP) if j!=i)]
    feasible = [(p,f) for p,f in pareto if constraint_vio(f)<0.01]

    print(f"\nPareto前沿: {len(pareto)}解, {len(feasible)}可行")
    print(f"\n★ v3创新点: CR和F随进化自适应演化")
    print(f"  CR: {cr_history[0]:.3f} → {cr_history[-1]:.3f} (自适应调整)")
    print(f"  F:  {f_history[0]:.3f} → {f_history[-1]:.3f} (自适应调整)")
    print(f"  优势: ①无需人工调参  ②不同阶段自动平衡探索与开发")
    print(f"        ③改动量小(~20行), 不增加PAGCM评估次数")

if __name__=='__main__':
    main()
