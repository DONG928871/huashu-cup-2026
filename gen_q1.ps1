
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Add()
$doc.PageSetup.PaperSize = 9
$doc.PageSetup.TopMargin = 72
$doc.PageSetup.BottomMargin = 72
$doc.PageSetup.LeftMargin = 90
$doc.PageSetup.RightMargin = 90

$sel = $word.Selection

# Title
$sel.Font.Name = '黑体'
$sel.Font.Size = 16
$sel.Font.Bold = $true
$sel.ParagraphFormat.Alignment = 1
$sel.TypeText('A题 微构体中填充导电介质的仿真优化——第一问 完整建模报告')
$sel.TypeParagraph()
$sel.Font.Size = 14
$sel.TypeText('PAGCM——周期边界自适应图连通判定模型')
$sel.TypeParagraph()
$sel.TypeParagraph()

# Module 1
$sel.Font.Size = 14
$sel.Font.Bold = $true
$sel.ParagraphFormat.Alignment = 0
$sel.TypeText('模块一：模型建立与公式推导')
$sel.TypeParagraph()

$sel.Font.Size = 12
$sel.Font.Bold = $true
$sel.TypeText('1.1 变量定义三线表')
$sel.TypeParagraph()

# Create table
$sel.Font.Size = 10
$sel.Font.Bold = $false
$tbl = $doc.Tables.Add($sel.Range, 16, 6)
$tbl.Style = '网格表'
$headers = @('变量符号','变量名称','变量类型','单位','取值范围','现实场景含义')
$data = @(
    @('p_i=(x_i,y_i,z_i)','粒子中心坐标','已知参数','坐标单位','[-5000,5000]^3','导电填料在RVE中的空间位置，由附件直接读取'),
    @('N','粒子总数','已知参数','个','{12,49,535}','微构体中导电填料粒子总数量'),
    @('L','RVE边长','已知参数','坐标单位','10000','代表体积单元立方体边长，从坐标极差推断'),
    @('r0','粒子基础几何半径','★待校准参数','坐标单位','[50,500]','导电填料物理半径，需据题目场景假设'),
    @('alpha','自适应强度系数','★待校准参数','无量纲','[0,2]','控制密度感知对等效半径的调节强度'),
    @('R_search','局部密度搜索半径','中间变量','坐标单位','1500','估算局部数密度时的球形搜索域半径'),
    @('rho_global','全局平均数密度','中间变量','L^-3','N/L^3','RVE内粒子平均空间密度'),
    @('rho_local(i)','粒子i局部数密度','中间变量','L^-3','[0,+inf)','搜索半径内近邻粒子数密度'),
    @('ri_eff','密度感知等效半径','中间变量','坐标单位','[0.5r0,3r0]','经局部密度修正的有效作用半径'),
    @('d_T(pi,pj)','环面距离','中间变量','坐标单位','[0,L*sqrt3/2]','周期边界下两粒子最短距离'),
    @('k_ij','周期偏移矢量','中间变量','Z^3','{-1,0,+1}^3','边(i,j)跨越周期边界的次数和方向'),
    @('G=(V,E)','周期图','决策变量','—','|V|=N','定义在3-环面T^3上的无向图'),
    @('C_k','第k个连通分量','决策变量','—','|Ck| in [1,N]','图的极大连通子图'),
    @('conn_dir','方向性连通判定','★目标变量','布尔','{0,1}','判定dir方向贯穿导电通路'),
    @('P_conn(dir)','连通概率','★目标变量','—','[0,1]','MC扰动后统计的连通概率')
)
for($c=0;$c -lt 6;$c++){$tbl.Cell(1,$c+1).Range.Text=$headers[$c];$tbl.Cell(1,$c+1).Range.Font.Bold=$true;$tbl.Cell(1,$c+1).Range.Font.Size=9;$tbl.Cell(1,$c+1).Shading.BackgroundPatternColor=15132390}
for($r=0;$r -lt 15;$r++){for($c=0;$c -lt 6;$c++){$tbl.Cell($r+2,$c+1).Range.Text=$data[$r][$c];$tbl.Cell($r+2,$c+1).Range.Font.Size=8}}
$sel.TypeParagraph()

$outDir = 'C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\docx输出'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$path = "$outDir\第一问_PAGCM完整建模报告.docx"
$doc.SaveAs($path)
$doc.Close()
$word.Quit()
Write-Output "DONE: $path"
