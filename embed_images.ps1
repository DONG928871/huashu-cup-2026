
$word = New-Object -ComObject Word.Application
$word.Visible = $false

$doc = $word.Documents.Open('C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\docx输出\第一问_PAGCM完整建模报告_四模块.docx')

$sel = $word.Selection
# Go to end of document
$sel.EndKey(6)  # wdStory

# Add images
$imgDir = 'C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\docx输出\图片\'

$images = @(
    @('图0_PAGCM建模流程图.png', '图0 PAGCM建模流程图（10步核心模块，四色阶段分组）'),
    @('图1_连通性热力图.png', '图1 连通性判定热力图（红色=连通，蓝色=不连通）'),
    @('图2_MC连通概率.png', '图2 蒙特卡洛连通概率（M=200, sigma=12.5）'),
    @('图3_PAGCM_vs_GPNM对比.png', '图3 PAGCM vs GPNM 连通方向数对比'),
    @('图4_alpha敏感度曲线.png', '图4 alpha参数敏感度扫描曲线'),
    @('图5_连通分量统计.png', '图5 连通分量统计与等效半径分布'),
    @('图6_性能与验证.png', '图6 求解性能与交叉验证')
)

foreach ($img in $images) {
    $sel.TypeParagraph()
    $sel.Font.Size = 10
    $sel.Font.Bold = $true
    $sel.ParagraphFormat.Alignment = 1
    $sel.TypeText($img[1])
    $sel.TypeParagraph()
    
    $imgPath = $imgDir + $img[0]
    if (Test-Path $imgPath) {
        $sel.InlineShapes.AddPicture($imgPath)
        $sel.TypeParagraph()
    }
}

$outPath = 'C:\Users\31670\OneDrive\Desktop\华数杯数学建模比赛\docx输出\第一问_PAGCM完整报告_含图表.docx'
$doc.SaveAs($outPath)
$doc.Close()
$word.Quit()
Write-Output "DONE: $outPath"
