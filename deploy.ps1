# =============================================================
# HandsFree 远程 Linux 打包部署（SSH 用户名密码，交互式输入）
# 用法: .\deploy.ps1 [-Message "提交说明"] [-SkipCommit] [-SkipFetch]
# 流程: 自动提交 -> git archive 快照 -> scp 上传 -> ssh 远程打包 -> scp 下载产物
# 注意: 每步连接都要输一次密码（共3次），Windows OpenSSH 不支持连接复用
#       打包脚本 deploy/build_remote.sh 需已提交（首次部署前先正常提交一次）
# =============================================================
param(
    [string]$Message = "",
    [switch]$SkipCommit,
    [switch]$SkipFetch
)

# ===== 默认值（交互输入时直接回车即用默认） =====
$DefaultHost = "192.168.242.130"
$DefaultUser = "xingqi"
# ==============================================

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$inHost = Read-Host "服务器IP（回车=$DefaultHost）"
if (-not $inHost) { $inHost = $DefaultHost }
$inUser = Read-Host "SSH用户名（回车=$DefaultUser）"
if (-not $inUser) { $inUser = $DefaultUser }
$Server = "${inUser}@${inHost}"
$BuildDir = "handsfree-src"   # 服务器家目录下的代码解压目录

$Branch = (git branch --show-current).Trim()
Write-Host "==> 当前分支: $Branch" -ForegroundColor Cyan

# 1. 自动提交本地变更
if (-not $SkipCommit) {
    git add -A
    $staged = @(git diff --cached --name-only)
    if ($staged.Count -gt 0) {
        if (-not $Message) {
            $Message = "deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        }
        git commit -m $Message
    } else {
        Write-Host "==> 无本地变更，跳过提交"
    }
}

# 2. git archive 生成当前提交的代码快照
$Tar = Join-Path $env:TEMP "handsfree_deploy.tar.gz"
git archive --format=tar.gz -o $Tar HEAD
if ($LASTEXITCODE -ne 0) { throw "git archive 失败" }

# 3. 上传快照（第1次输密码）
Write-Host "==> 上传代码快照..." -ForegroundColor Cyan
scp $Tar "${Server}:handsfree_deploy.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "上传失败，请检查服务器地址/网络" }

# 4. 远程解压并打包（第2次输密码）
# sed 先去除可能的 \r（防止 Windows 换行符混入 .sh 导致 bash 报错）
Write-Host "==> 远程打包中（首次会创建虚拟环境并安装依赖，较慢）..." -ForegroundColor Cyan
$Cmd = "mkdir -p ~/$BuildDir && tar -xzf ~/handsfree_deploy.tar.gz -C ~/$BuildDir --overwrite && cd ~/$BuildDir && sed -i 's/\r$//' deploy/build_remote.sh && bash deploy/build_remote.sh"
ssh $Server $Cmd
if ($LASTEXITCODE -ne 0) { throw "远程打包失败" }

# 5. 下载产物（第3次输密码）
if (-not $SkipFetch) {
    $OutDir = Join-Path $PSScriptRoot "dist-linux"
    if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
    Write-Host "==> 下载产物到 $OutDir ..." -ForegroundColor Cyan
    scp "${Server}:${BuildDir}/dist/HandsFree" $OutDir
    if ($LASTEXITCODE -ne 0) { throw "产物下载失败" }
    Remove-Item $Tar -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "==> 部署完成 ✓ 产物: $OutDir\HandsFree" -ForegroundColor Green
