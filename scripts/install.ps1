[CmdletBinding()]
param(
    [ValidateSet("codex", "claude", "agents", "custom")]
    [string]$Target = "codex",

    [string]$Destination,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SkillName = "computer-repair-skill"

function Expand-InstallPath {
    <# 将环境变量、用户目录和相对路径转换为可审计的绝对路径。 #>
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

function Get-SkillsRoot {
    <# 按 Agent 预设选择 Skills 根目录；自定义模式必须显式给出目录。 #>
    param(
        [Parameter(Mandatory = $true)][string]$AgentTarget,
        [string]$CustomDestination
    )

    if (-not [string]::IsNullOrWhiteSpace($CustomDestination)) {
        return Expand-InstallPath $CustomDestination
    }

    $userProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
    switch ($AgentTarget) {
        "codex" {
            $agentHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $userProfile ".codex" }
        }
        "claude" {
            $agentHome = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $userProfile ".claude" }
        }
        "agents" {
            $agentHome = Join-Path $userProfile ".agents"
        }
        "custom" {
            throw "Target 为 custom 时必须提供 -Destination。"
        }
        default {
            throw "不支持的 Target：$AgentTarget"
        }
    }

    return Expand-InstallPath (Join-Path $agentHome "skills")
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

$sourcePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\skills\$SkillName"))
if (-not (Test-Path -LiteralPath (Join-Path $sourcePath "SKILL.md") -PathType Leaf)) {
    throw "找不到 Skill 源目录：$sourcePath"
}

$skillsRoot = Get-SkillsRoot -AgentTarget $Target -CustomDestination $Destination
$targetPath = Join-Path $skillsRoot $SkillName
$targetExists = Test-Path -LiteralPath $targetPath

if ($targetExists -and -not $Force) {
    throw "目标已存在：$targetPath。未做任何覆盖；确认更新时请显式添加 -Force。"
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
$stagePath = Join-Path $skillsRoot (".{0}.install-{1}" -f $SkillName, [Guid]::NewGuid().ToString("N"))
$backupPath = $null
$installed = $false

try {
    Write-Host "正在验证并暂存 Skill：$sourcePath"
    Copy-SkillToStage -Source $sourcePath -Stage $stagePath

    if ($targetExists) {
        $backupRoot = Join-Path (Split-Path $skillsRoot -Parent) "external\$SkillName\backups"
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        $backupPath = Join-Path $backupRoot (Get-Date -Format "yyyyMMdd-HHmmssfff")
        Move-Item -LiteralPath $targetPath -Destination $backupPath
        Write-Host "旧版本已备份到：$backupPath"
    }

    Move-Item -LiteralPath $stagePath -Destination $targetPath
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

Write-Host "安装完成：$targetPath"
Write-Host "请重启或刷新 Agent 的 Skills 列表后使用 $SkillName。"
