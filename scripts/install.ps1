# PositionalBinding = $false：所有参数一律具名。
# 否则 `-Target claude foo` 这类手滑会把多余的位置参数静默吞掉，
# 而 scripts/install.sh 是明确报错的，两个安装器的行为必须一致。
[CmdletBinding(PositionalBinding = $false)]
param(
    [ValidateSet(
        "codex", "claude", "claude-code", "cursor", "gemini-cli", "github-copilot",
        "windsurf", "opencode", "openclaw", "agents", "universal", "antigravity",
        "augment", "qwen-code", "trae", "roo", "crush", "goose", "droid",
        "continue", "openhands", "custom")]
    [string]$Target = "codex",

    [string]$Destination,

    [string]$BackupDir,

    [switch]$Verify,

    [switch]$Uninstall,

    [switch]$ListTarget,

    [switch]$Link,

    [switch]$Force,

    [switch]$Purge,

    [switch]$DryRun,

    [switch]$Quiet
)

# 把 computer-repair-skill 安装到某个 Agent 的 Skills 根目录。
#
# 设计约束（与 scripts/install.sh 保持一致）：
#   * 默认绝不覆盖已存在的安装，必须显式 -Force。
#   * 先完整复制到临时目录再一次性 Move-Item 生效，失败自动回滚。
#   * 安装后写出与 Bash 版逐行同构的清单，两个安装器可以互相校验。
#   * 兼容 Windows PowerShell 5.1：不使用三元运算符、?? 以及 .NET Core 专属 API。

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 预期内的失败（尚未安装、清单不匹配、参数互斥……）必须像 scripts/install.sh 的 fail()
# 一样，输出一行 "错误：…" 到 stderr 然后以 1 退出，而不是把 PowerShell 的异常堆栈
# 甩到用户脸上。两个安装器的失败体验必须一致。
#
# 这里用脚本作用域的 trap 而不是在末尾包一层 try/catch：本脚本的参数校验散落在函数
# 定义之间的主体代码里，无法被单个 try 块包住，而 trap 能同时覆盖主体和三个入口函数。
# trap 也不会打断函数内部已有的 try/finally 回滚 —— finally 在异常向外传播时先执行，
# trap 才拿到控制权。
trap {
    [Console]::Error.WriteLine("错误：" + $_.Exception.Message)
    exit 1
}

$SkillName = "computer-repair-skill"
$ManifestName = ".computer-repair-skill-install.json"
$BackupDirName = ".computer-repair-skill-backups"
$ManifestSchema = 1

$script:QuietOutput = $Quiet.IsPresent

# 把开关的取值提升到脚本作用域：函数里显式引用 $script:* 比依赖动态作用域更清晰，
# 也让 PSScriptAnalyzer 的 PSReviewUnusedParameter 能正确识别这些参数确实被使用。
$script:UseForce = $Force.IsPresent
$script:UseLink = $Link.IsPresent
$script:IsDryRun = $DryRun.IsPresent
$script:UsePurge = $Purge.IsPresent

function Write-Status {
    <# 输出面向用户的进度信息。

    刻意不用 Write-Host：它在没有 host 的运行环境（CI、计划任务、远程会话）里
    行为不确定，PSScriptAnalyzer 也会因此告警。也不用 Write-Output —— 那会把
    提示文字混进函数返回值。直接写 Console 的标准输出最可控。 #>
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)

    if (-not $script:QuietOutput) {
        [Console]::Out.WriteLine($Message)
    }
}

function Expand-InstallPath {
    <# 将环境变量、用户目录和相对路径转换为可审计的绝对路径；不触碰磁盘。 #>
    param([Parameter(Mandatory = $true)][string]$Path)

    $userProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
    $expanded = [Environment]::ExpandEnvironmentVariables($Path)

    if ($expanded -eq "~") {
        $expanded = $userProfile
    }
    elseif ($expanded.StartsWith("~/") -or $expanded.StartsWith("~\")) {
        $expanded = Join-Path $userProfile $expanded.Substring(2)
    }

    if (-not [IO.Path]::IsPathRooted($expanded)) {
        $expanded = Join-Path (Get-Location).Path $expanded
    }

    return [IO.Path]::GetFullPath($expanded)
}

function Get-ConfigHome {
    <# XDG 风格的配置根目录，缺省回落到 ~/.config，与 Bash 版一致。 #>
    $userProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
    if ($env:XDG_CONFIG_HOME) {
        return $env:XDG_CONFIG_HOME
    }
    return (Join-Path $userProfile ".config")
}

function Get-PresetRoot {
    <# 各 Agent 的默认全局 Skills 根目录；custom 返回空串表示必须显式给出目录。 #>
    param([Parameter(Mandatory = $true)][string]$AgentTarget)

    $userProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)

    switch ($AgentTarget) {
        "codex" {
            if ($env:CODEX_HOME) { return (Join-Path $env:CODEX_HOME "skills") }
            return (Join-Path (Join-Path $userProfile ".codex") "skills")
        }
        { $_ -in @("claude", "claude-code") } {
            if ($env:CLAUDE_HOME) { return (Join-Path $env:CLAUDE_HOME "skills") }
            return (Join-Path (Join-Path $userProfile ".claude") "skills")
        }
        "cursor" { return (Join-Path (Join-Path $userProfile ".cursor") "skills") }
        "gemini-cli" { return (Join-Path (Join-Path $userProfile ".gemini") "skills") }
        "github-copilot" { return (Join-Path (Join-Path $userProfile ".copilot") "skills") }
        "windsurf" { return (Join-Path (Join-Path $userProfile ".codeium\windsurf") "skills") }
        "opencode" { return (Join-Path (Join-Path (Get-ConfigHome) "opencode") "skills") }
        "openclaw" { return (Join-Path (Join-Path $userProfile ".openclaw") "skills") }
        "agents" { return (Join-Path (Join-Path $userProfile ".agents") "skills") }
        "universal" { return (Join-Path (Join-Path (Get-ConfigHome) "agents") "skills") }
        "antigravity" { return (Join-Path (Join-Path $userProfile ".gemini\antigravity") "skills") }
        "augment" { return (Join-Path (Join-Path $userProfile ".augment") "skills") }
        "qwen-code" { return (Join-Path (Join-Path $userProfile ".qwen") "skills") }
        "trae" { return (Join-Path (Join-Path $userProfile ".trae") "skills") }
        "roo" { return (Join-Path (Join-Path $userProfile ".roo") "skills") }
        "crush" { return (Join-Path (Join-Path (Get-ConfigHome) "crush") "skills") }
        "goose" { return (Join-Path (Join-Path (Get-ConfigHome) "goose") "skills") }
        "droid" { return (Join-Path (Join-Path $userProfile ".factory") "skills") }
        "continue" { return (Join-Path (Join-Path $userProfile ".continue") "skills") }
        "openhands" { return (Join-Path (Join-Path $userProfile ".openhands") "skills") }
        "custom" { return "" }
        default { throw "不支持的 Target：$AgentTarget" }
    }
}

function Show-TargetList {
    <# 打印全部预设及其解析后的目录，方便用户核对再安装。 #>
    $names = @(
        "codex", "claude", "claude-code", "cursor", "gemini-cli", "github-copilot",
        "windsurf", "opencode", "openclaw", "agents", "universal", "antigravity",
        "augment", "qwen-code", "trae", "roo", "crush", "goose", "droid",
        "continue", "openhands", "custom")

    Write-Status ("{0,-16} {1}" -f "预设", "全局 Skills 根目录")
    foreach ($name in $names) {
        $root = Get-PresetRoot -AgentTarget $name
        if ([string]::IsNullOrEmpty($root)) {
            Write-Status ("{0,-16} {1}" -f $name, "（必须配合 -Destination）")
        }
        else {
            Write-Status ("{0,-16} {1}" -f $name, (Expand-InstallPath $root))
        }
    }
    Write-Status ""
    Write-Status "项目级安装请改用 -Destination，例如 -Destination .\.claude\skills。"
}

function Get-SkillsRoot {
    <# 按 Agent 预设选择 Skills 根目录；自定义模式必须显式给出目录。 #>
    param(
        [Parameter(Mandatory = $true)][string]$AgentTarget,
        [string]$CustomDestination
    )

    if (-not [string]::IsNullOrWhiteSpace($CustomDestination)) {
        return Expand-InstallPath $CustomDestination
    }

    $root = Get-PresetRoot -AgentTarget $AgentTarget
    if ([string]::IsNullOrEmpty($root)) {
        throw "Target 为 custom 时必须提供 -Destination。"
    }
    return Expand-InstallPath $root
}

function Test-IsReparsePoint {
    <# 判断路径是否为符号链接或目录联接。 #>
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    $item = Get-Item -LiteralPath $Path -Force
    return (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Get-LinkTargetPath {
    <# 读取链接指向的路径；PowerShell 5.1 可能返回数组，这里统一成字符串。 #>
    param([Parameter(Mandatory = $true)][string]$Path)

    $item = Get-Item -LiteralPath $Path -Force
    $value = $item.Target
    if ($null -eq $value) {
        return ""
    }
    if ($value -is [array]) {
        if ($value.Count -eq 0) {
            return ""
        }
        return [string]$value[0]
    }
    return [string]$value
}

function Get-PayloadFileList {
    <# 列出目录下全部普通文件的相对路径，按序数排序以匹配 Bash 版的 LC_ALL=C sort。 #>
    param([Parameter(Mandatory = $true)][string]$Root)

    $rootFull = [IO.Path]::GetFullPath($Root)
    if (-not $rootFull.EndsWith([string][IO.Path]::DirectorySeparatorChar)) {
        $rootFull = $rootFull + [IO.Path]::DirectorySeparatorChar
    }

    $collected = New-Object 'System.Collections.Generic.List[string]'
    foreach ($file in (Get-ChildItem -LiteralPath $Root -Recurse -File -Force)) {
        $collected.Add($file.FullName.Substring($rootFull.Length).Replace("\", "/"))
    }
    $collected.Sort([System.StringComparer]::Ordinal)
    return $collected.ToArray()
}

function Get-DigestList {
    <# 生成 "相对路径 sha256" 数组；清单以空格分隔，因此强制校验文件名字符集。 #>
    param([Parameter(Mandatory = $true)][string]$Root)

    foreach ($entry in (Get-ChildItem -LiteralPath $Root -Recurse -Force)) {
        if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Skill 载荷中存在链接，清单无法保证可复现：$($entry.FullName)"
        }
    }

    $lines = New-Object 'System.Collections.Generic.List[string]'
    foreach ($rel in @(Get-PayloadFileList -Root $Root)) {
        if ($rel -notmatch '^[A-Za-z0-9._/-]+$') {
            throw "文件名含清单不支持的字符（仅允许字母、数字、点、下划线、连字符和斜杠）：$rel"
        }
        $full = Join-Path $Root ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
        $hash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
        $lines.Add("$rel $hash")
    }
    return $lines.ToArray()
}

function Convert-ToJsonString {
    <# 只需转义反斜杠和双引号：其余字段都是路径、版本号或十六进制摘要。 #>
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value)

    return $Value.Replace("\", "\\").Replace('"', '\"')
}

function Write-InstallManifest {
    <# 手写 JSON 而不用 ConvertTo-Json：必须与 Bash 版逐行同构，
       这样 install.sh --verify 也能解析本脚本写出的清单。 #>
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Mode,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$DigestList,
        [Parameter(Mandatory = $true)][string]$SourceDirectory,
        [Parameter(Mandatory = $true)][string]$TargetDirectory,
        [Parameter(Mandatory = $true)][string]$SkillVersion,
        [AllowEmptyString()][string]$SourceCommit = ""
    )

    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append("{`n")
    [void]$builder.Append("  `"schema`": $ManifestSchema,`n")
    [void]$builder.Append("  `"skill`": `"$(Convert-ToJsonString $SkillName)`",`n")
    [void]$builder.Append("  `"version`": `"$(Convert-ToJsonString $SkillVersion)`",`n")
    [void]$builder.Append("  `"install_mode`": `"$(Convert-ToJsonString $Mode)`",`n")
    [void]$builder.Append("  `"installed_at`": `"$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))`",`n")
    [void]$builder.Append("  `"installer`": `"scripts/install.ps1`",`n")
    [void]$builder.Append("  `"source_dir`": `"$(Convert-ToJsonString $SourceDirectory)`",`n")
    if ([string]::IsNullOrEmpty($SourceCommit)) {
        [void]$builder.Append("  `"source_commit`": null,`n")
    }
    else {
        [void]$builder.Append("  `"source_commit`": `"$(Convert-ToJsonString $SourceCommit)`",`n")
    }
    [void]$builder.Append("  `"target_path`": `"$(Convert-ToJsonString $TargetDirectory)`",`n")
    [void]$builder.Append("  `"file_count`": $($DigestList.Count),`n")
    [void]$builder.Append("  `"files`": [`n")
    for ($i = 0; $i -lt $DigestList.Count; $i++) {
        $parts = $DigestList[$i].Split(" ")
        $comma = ","
        if ($i -eq ($DigestList.Count - 1)) {
            $comma = ""
        }
        [void]$builder.Append("    { `"path`": `"$($parts[0])`", `"sha256`": `"$($parts[1])`" }$comma`n")
    }
    [void]$builder.Append("  ]`n")
    [void]$builder.Append("}`n")

    $temporary = "$Path.tmp"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($temporary, $builder.ToString(), $utf8NoBom)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Read-InstallManifest {
    <# 读取清单并返回 PSCustomObject；缺字段时给出明确错误而不是抛 StrictMode 异常。 #>
    param([Parameter(Mandatory = $true)][string]$Path)

    $manifest = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($field in @("install_mode", "version", "source_dir", "files")) {
        if (-not ($manifest.PSObject.Properties.Name -contains $field)) {
            throw "安装清单缺少字段 $field，无法使用：$Path"
        }
    }
    return $manifest
}

function Copy-SkillToStage {
    <# 先完整复制到临时目录，避免半完成的 Skill 被 Agent 发现。 #>
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Stage
    )

    New-Item -ItemType Directory -Path $Stage -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Stage -Recurse -Force
    }

    if (-not (Test-Path -LiteralPath (Join-Path $Stage "SKILL.md") -PathType Leaf)) {
        throw "暂存副本缺少 SKILL.md，安装已停止。"
    }
}

function Get-UnmanagedFileList {
    <# 列出目标目录里不在清单内的文件，用于卸载前的 Inspect Before Delete。 #>
    param(
        [Parameter(Mandatory = $true)][string]$TargetDirectory,
        [Parameter(Mandatory = $true)]$Manifest
    )

    $known = @{}
    foreach ($entry in $Manifest.files) {
        $known[$entry.path] = $true
    }

    $unmanaged = New-Object 'System.Collections.Generic.List[string]'
    foreach ($rel in @(Get-PayloadFileList -Root $TargetDirectory)) {
        if (-not $known.ContainsKey($rel)) {
            $unmanaged.Add($rel)
        }
    }
    return $unmanaged.ToArray()
}

# --- 公共上下文 -------------------------------------------------------------

$actionCount = 0
foreach ($switchState in @($Verify.IsPresent, $Uninstall.IsPresent, $ListTarget.IsPresent)) {
    if ($switchState) {
        $actionCount++
    }
}
if ($actionCount -gt 1) {
    throw "-Verify、-Uninstall 和 -ListTarget 互斥，一次只能指定一个。"
}
if ($script:UsePurge -and -not $Uninstall.IsPresent) {
    throw "-Purge 只能与 -Uninstall 一起使用。"
}

if ($ListTarget.IsPresent) {
    Show-TargetList
    return
}

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$sourcePath = Join-Path (Join-Path $repoRoot "skills") $SkillName
if (-not (Test-Path -LiteralPath (Join-Path $sourcePath "SKILL.md") -PathType Leaf)) {
    throw "找不到 Skill 源目录：$sourcePath"
}

$skillVersion = "unknown"
$versionFile = Join-Path $repoRoot "VERSION"
if (Test-Path -LiteralPath $versionFile -PathType Leaf) {
    $rawVersion = (Get-Content -LiteralPath $versionFile -Raw).Trim()
    if (-not [string]::IsNullOrWhiteSpace($rawVersion)) {
        $skillVersion = $rawVersion
    }
}

$sourceCommit = ""
if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitOutput = & git -C $repoRoot rev-parse HEAD 2>$null
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($gitOutput)) {
        $sourceCommit = $gitOutput.Trim()
    }
}

$skillsRoot = Get-SkillsRoot -AgentTarget $Target -CustomDestination $Destination
$targetPath = Join-Path $skillsRoot $SkillName
$manifestPath = Join-Path $skillsRoot $ManifestName

if (-not [string]::IsNullOrWhiteSpace($BackupDir)) {
    $backupRoot = Expand-InstallPath $BackupDir
}
else {
    $backupRoot = Join-Path $skillsRoot $BackupDirName
}

# --- 校验 -------------------------------------------------------------------

function Invoke-SkillVerify {
    if (-not (Test-Path -LiteralPath $targetPath)) {
        throw "未检测到安装：$targetPath"
    }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "缺少安装清单 $manifestPath，无法校验；请重新运行安装以生成清单。"
    }

    $manifest = Read-InstallManifest -Path $manifestPath
    Write-Status "清单版本：$($manifest.version)"
    Write-Status "安装方式：$($manifest.install_mode)"

    if ($manifest.install_mode -eq "link") {
        if (-not (Test-IsReparsePoint -Path $targetPath)) {
            throw "清单记录为链接安装，但 $targetPath 不是链接。"
        }
        $actual = Get-LinkTargetPath -Path $targetPath
        if ($actual.TrimEnd("\", "/") -ne ([string]$manifest.source_dir).TrimEnd("\", "/")) {
            throw "链接指向 $actual，与清单记录的 $($manifest.source_dir) 不一致。"
        }
        Write-Status "链接指向：$actual"
        Write-Status "校验通过：链接安装的内容随仓库变化，故跳过逐文件摘要比对。"
        return
    }

    if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
        throw "清单记录为复制安装，但 $targetPath 不是目录。"
    }

    $missing = 0
    $modified = 0
    $checked = 0
    foreach ($entry in $manifest.files) {
        $checked++
        $full = Join-Path $targetPath ($entry.path -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            Write-Warning "[缺失] $($entry.path)"
            $missing++
            continue
        }
        $actualHash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $entry.sha256) {
            Write-Warning "[被修改] $($entry.path)"
            $modified++
        }
    }

    if ($checked -eq 0) {
        throw "清单没有记录任何文件，内容不可信。"
    }

    $extra = @(Get-UnmanagedFileList -TargetDirectory $targetPath -Manifest $manifest)
    foreach ($rel in $extra) {
        Write-Warning "[清单外文件] $rel"
    }

    if ($missing -gt 0 -or $modified -gt 0 -or $extra.Count -gt 0) {
        throw "校验失败：$checked 个受管文件中缺失 $missing、被修改 $modified，另有 $($extra.Count) 个清单外文件。"
    }

    Write-Status "校验通过：$checked 个文件的 sha256 与清单完全一致，且无清单外文件。"
}

# --- 卸载 -------------------------------------------------------------------

function Invoke-SkillUninstall {
    $targetExists = Test-Path -LiteralPath $targetPath
    $manifestExists = Test-Path -LiteralPath $manifestPath -PathType Leaf

    if (-not $targetExists -and -not $manifestExists) {
        Write-Status "未检测到安装，无需卸载：$targetPath"
        return
    }

    $isLink = $false
    if ($targetExists) {
        $isLink = Test-IsReparsePoint -Path $targetPath
    }

    if ($isLink) {
        Write-Status "将移除链接：$targetPath"
    }
    elseif ($targetExists -and (Test-Path -LiteralPath $targetPath -PathType Container)) {
        if (-not $manifestExists) {
            if (-not $script:UseForce) {
                throw "缺少安装清单 $manifestPath，无法确认目录归属；确认要删除 $targetPath 请添加 -Force。"
            }
            Write-Warning "缺少清单，按 -Force 直接删除 $targetPath。"
        }
        else {
            $manifest = Read-InstallManifest -Path $manifestPath
            $unmanaged = @(Get-UnmanagedFileList -TargetDirectory $targetPath -Manifest $manifest)
            if ($unmanaged.Count -gt 0) {
                foreach ($rel in $unmanaged) {
                    Write-Warning "清单外文件（可能是本地修改）：$rel"
                }
                if (-not $script:UseForce) {
                    throw "存在清单外文件，已停止；确认连同这些文件一起删除请添加 -Force。"
                }
                Write-Warning "按 -Force 连同上述清单外文件一起删除。"
            }
        }
        Write-Status "将移除目录：$targetPath"
    }
    elseif ($targetExists) {
        throw "$targetPath 既不是目录也不是链接，出于安全考虑不做删除。"
    }

    if ($manifestExists) {
        Write-Status "将移除清单：$manifestPath"
    }
    $backupExists = Test-Path -LiteralPath $backupRoot -PathType Container
    if ($backupExists) {
        if ($script:UsePurge) {
            Write-Status "将移除备份目录：$backupRoot"
        }
        else {
            Write-Status "保留备份目录（加 -Purge 可一并删除）：$backupRoot"
        }
    }

    if ($script:IsDryRun) {
        Write-Status "-DryRun：以上操作均未执行。"
        return
    }

    if ($targetExists) {
        if ($isLink) {
            # 链接必须用 .NET 删除：Remove-Item -Recurse 在 5.1 上会跟随联接删掉源目录内容。
            [IO.Directory]::Delete($targetPath)
        }
        else {
            Remove-Item -LiteralPath $targetPath -Recurse -Force
        }
    }
    if ($manifestExists) {
        Remove-Item -LiteralPath $manifestPath -Force
    }
    if ($script:UsePurge -and $backupExists) {
        Remove-Item -LiteralPath $backupRoot -Recurse -Force
    }

    Write-Status "卸载完成：$targetPath"
}

# --- 安装 -------------------------------------------------------------------

function Test-TargetMatchesSource {
    <# 已安装内容与源目录逐字节一致时返回 $true，让重复的 -Force 安装成为幂等空操作。 #>
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$SourceDigest)

    if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
        return $false
    }
    if (Test-IsReparsePoint -Path $targetPath) {
        return $false
    }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        return $false
    }

    try {
        $manifest = Read-InstallManifest -Path $manifestPath
    }
    catch {
        return $false
    }

    if ($manifest.install_mode -ne "copy" -or $manifest.version -ne $skillVersion) {
        return $false
    }

    try {
        $installed = @(Get-DigestList -Root $targetPath)
    }
    catch {
        return $false
    }

    if ($installed.Count -ne $SourceDigest.Count) {
        return $false
    }
    for ($i = 0; $i -lt $installed.Count; $i++) {
        if ($installed[$i] -ne $SourceDigest[$i]) {
            return $false
        }
    }
    return $true
}

function New-SkillLink {
    <# 优先建符号链接；无开发者模式/管理员权限时回落到目录联接。 #>
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Low")]
    param(
        [Parameter(Mandatory = $true)][string]$LinkPath,
        [Parameter(Mandatory = $true)][string]$SourceDirectory
    )

    if (-not $PSCmdlet.ShouldProcess($LinkPath, "创建指向 $SourceDirectory 的链接")) {
        return
    }

    try {
        New-Item -ItemType SymbolicLink -Path $LinkPath -Value $SourceDirectory -ErrorAction Stop | Out-Null
    }
    catch {
        Write-Warning "创建符号链接失败（$($_.Exception.Message)），改用目录联接。"
        New-Item -ItemType Junction -Path $LinkPath -Value $SourceDirectory -ErrorAction Stop | Out-Null
    }
}

function Invoke-SkillInstall {
    $sourceDigest = @(Get-DigestList -Root $sourcePath)
    if ($sourceDigest.Count -eq 0) {
        throw "源目录没有可安装的文件：$sourcePath"
    }

    $targetExists = Test-Path -LiteralPath $targetPath
    if ($targetExists -and -not $script:UseForce) {
        throw "目标已存在：$targetPath。未做任何覆盖；确认更新时请显式添加 -Force（会先备份），或用 -Verify 检查当前副本。"
    }

    if ($targetExists -and -not $script:UseLink -and (Test-TargetMatchesSource -SourceDigest $sourceDigest)) {
        Write-Status "已安装版本 $skillVersion，且 $($sourceDigest.Count) 个文件的 sha256 全部一致，无需变更：$targetPath"
        return
    }

    if ($script:UseLink) {
        Write-Status "计划：在 $targetPath 创建指向 $sourcePath 的链接（开发模式）"
    }
    else {
        Write-Status "计划：把 $($sourceDigest.Count) 个文件（版本 $skillVersion）安装到 $targetPath"
    }
    if ($targetExists) {
        Write-Status "计划：先把现有副本备份到 $backupRoot"
    }
    Write-Status "计划：写出安装清单 $manifestPath"

    if ($script:IsDryRun) {
        Write-Status "-DryRun：以上操作均未执行，磁盘未被写入。"
        return
    }

    New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
    $stagePath = Join-Path $skillsRoot (".{0}.install-{1}" -f $SkillName, [Guid]::NewGuid().ToString("N"))
    $backupPath = $null
    $installed = $false

    try {
        if (-not $script:UseLink) {
            Write-Status "正在验证并暂存 Skill：$sourcePath"
            Copy-SkillToStage -Source $sourcePath -Stage $stagePath
            $stagedDigest = @(Get-DigestList -Root $stagePath)
            if (($stagedDigest -join "`n") -ne ($sourceDigest -join "`n")) {
                throw "暂存副本与源目录的摘要不一致，安装已停止。"
            }
        }

        if ($targetExists) {
            New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
            $backupPath = Join-Path $backupRoot (Get-Date -Format "yyyyMMdd-HHmmssfff")
            Move-Item -LiteralPath $targetPath -Destination $backupPath
            Write-Status "旧版本已备份到：$backupPath"
        }

        if ($script:UseLink) {
            New-SkillLink -LinkPath $targetPath -SourceDirectory $sourcePath -Confirm:$false
            Write-InstallManifest -Path $manifestPath -Mode "link" -DigestList $sourceDigest `
                -SourceDirectory $sourcePath -TargetDirectory $targetPath `
                -SkillVersion $skillVersion -SourceCommit $sourceCommit
        }
        else {
            Move-Item -LiteralPath $stagePath -Destination $targetPath
            Write-InstallManifest -Path $manifestPath -Mode "copy" -DigestList $sourceDigest `
                -SourceDirectory $sourcePath -TargetDirectory $targetPath `
                -SkillVersion $skillVersion -SourceCommit $sourceCommit
        }
        $installed = $true
    }
    catch {
        if ($backupPath -and -not (Test-Path -LiteralPath $targetPath) -and (Test-Path -LiteralPath $backupPath)) {
            Move-Item -LiteralPath $backupPath -Destination $targetPath
            Write-Warning "安装失败，已恢复原版本：$targetPath"
        }
        throw
    }
    finally {
        if (-not $installed -and (Test-Path -LiteralPath $stagePath)) {
            Remove-Item -LiteralPath $stagePath -Recurse -Force
        }
    }

    Write-Status "安装完成：$targetPath"
    Write-Status "安装清单：$manifestPath（可用 -Verify 复核，-Uninstall 卸载）"
    Write-Status "请重启或刷新 Agent 的 Skills 列表后使用 $SkillName。"
}

if ($Verify.IsPresent) {
    Invoke-SkillVerify
}
elseif ($Uninstall.IsPresent) {
    Invoke-SkillUninstall
}
else {
    Invoke-SkillInstall
}

# 显式成功退出：脚本内部调用过 git，$LASTEXITCODE 可能残留它的值。
# 不写这一行，同进程 `& ./install.ps1` 的调用方就无法只凭退出码判断成败。
exit 0
