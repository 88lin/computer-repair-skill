# PositionalBinding = $false：所有参数一律具名。
# 否则 `-ListSection json` 这类手滑会把多余的位置参数静默吞掉，
# 而 scripts/collect-health.sh 是明确报错的，两个脚本的行为必须一致。
[CmdletBinding(PositionalBinding = $false)]
param(
    [ValidateSet("json", "markdown")]
    [string]$Format = "json",

    [string]$OutputPath,

    [string[]]$Section,

    [switch]$ListSection,

    [ValidateRange(1, 600)]
    [int]$TimeoutSecond = 20,

    [switch]$NoIdentity,

    [switch]$Quiet
)

# 只读采集一台 Windows 机器的健康证据，输出结构化 JSON 或 Markdown。
#
# 安全边界（与 skills/computer-repair-skill/references/safety-policy.md 一致）：
#   * 只执行查询类命令：不安装、不卸载、不删除、不改注册表、不重启服务、不修改电源或安全策略。
#   * 不发起任何网络请求；需要联网才能回答的检查（例如待安装更新清单）会被显式标记为 skipped。
#   * 输出前逐行过滤，凡含 password / token / secret 等关键字的行整行替换为占位符。
#   * 除 -OutputPath 指定的文件外不写入任何路径。
#
# -NoIdentity 只保证报告头部不记录主机名与用户名；探针的原始输出（例如 w32tm /query /status）
# 仍可能包含主机信息，需要完全脱敏请在交付前人工复核。
#
# 与 scripts/collect-health.sh 的差异（刻意保留，已在 README 说明）：
#   * exit_code 语义：0 = 无错误；非 0 = 原生命令的退出码，或有 PowerShell 错误记录时记 1；
#     124 = 超过 -TimeoutSecond 未返回（沿用 GNU timeout 的约定）。
#   * 探针在同进程的独立 runspace 里执行，因此超时可以被真正打断，而不需要为每项检查开新进程。
#
# 这个脚本是可选的辅助工具。Skill 的核心仍然是 Markdown Playbook：
# 采集到的证据只是给 Agent 和维修工程师看的输入，任何变更动作仍由 Playbook 驱动。

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$CollectorName = "collect-health.ps1"
$OutputSchema = 1

$script:QuietOutput = $Quiet.IsPresent
$script:OutputFormat = $Format
$script:ProbeTimeout = $TimeoutSecond
$script:Buffer = New-Object System.Text.StringBuilder
$script:ProbeRunspace = $null
$script:ProbeIndex = 0
$script:ProbeCount = 0
$script:ProbeFailureCount = 0
$script:SkipCount = 0

# 小节顺序即输出顺序，与 scripts/collect-health.sh 的 section_catalog 一一对应。
$SectionCatalog = @(
    @{ Id = "overview"; Title = "系统与启动概览" }
    @{ Id = "hardware"; Title = "硬件与固件" }
    @{ Id = "storage"; Title = "存储与文件系统" }
    @{ Id = "memory"; Title = "内存与交换" }
    @{ Id = "process"; Title = "进程占用排行" }
    @{ Id = "network"; Title = "网络配置与监听" }
    @{ Id = "services"; Title = "服务与计划任务" }
    @{ Id = "updates"; Title = "系统更新状态（只读本地缓存）" }
    @{ Id = "security"; Title = "安全基线开关" }
    @{ Id = "logs"; Title = "近期错误日志与崩溃报告" }
    @{ Id = "power"; Title = "电源、电池与温度" }
)

$CredentialPattern = "password|passwd|secret|token|api[_-]?key|apikey|access[_-]?key|bearer|credential|private key|psk"

# Markdown 代码围栏。用 [char] 拼出来，避免在双引号字符串里数反引号转义。
$CodeFence = [string][char]0x60 + [string][char]0x60 + [string][char]0x60

function Write-Status {
    <# 进度与提示统一走标准错误：标准输出要保持是一份干净的 JSON 或 Markdown。 #>
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)

    if (-not $script:QuietOutput) {
        [Console]::Error.WriteLine($Message)
    }
}

function Show-SectionList {
    <# 列出可用小节；供 -ListSection 使用。 #>
    param([Parameter(Mandatory = $true)][object[]]$Catalog)

    [Console]::Out.WriteLine("可用小节（-Section 接受逗号分隔或数组形式的多个 id）：")
    foreach ($entry in $Catalog) {
        [Console]::Out.WriteLine(("  {0,-10} {1}" -f $entry.Id, $entry.Title))
    }
}

function Get-SectionTitle {
    param(
        [Parameter(Mandatory = $true)][object[]]$Catalog,
        [Parameter(Mandatory = $true)][string]$Id
    )

    foreach ($entry in $Catalog) {
        if ($entry.Id -eq $Id) {
            return $entry.Title
        }
    }
    return $Id
}

function Get-HostPlatform {
    <# 只用 .NET 判定平台：$IsWindows 在 Windows PowerShell 5.1 里并不存在。 #>
    param()

    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        return "windows"
    }
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Unix) {
        return "unix"
    }
    return "unknown"
}

function Protect-SensitiveText {
    <# 整行丢弃可能含凭据的输出。宁可少给一行证据，也不要把秘密写进报告。 #>
    param([AllowEmptyString()][string]$Text)

    if ([string]::IsNullOrEmpty($Text)) {
        return ""
    }

    $normalized = $Text.Replace("`r`n", "`n").Replace("`r", "`n")
    $kept = New-Object System.Collections.Generic.List[string]
    foreach ($line in $normalized.Split("`n")) {
        if ($line -imatch $CredentialPattern) {
            $kept.Add("[已按只读采集策略移除可能含凭据的一行]")
        }
        else {
            $kept.Add($line)
        }
    }
    return ($kept -join "`n").TrimEnd("`n")
}

function Convert-ToJsonText {
    <# 手写 JSON 字符串转义，保持与 Bash 版逐字节一致：
       控制字符里只保留制表与换行，其余直接丢弃（对应 Bash 版的 tr -d）。 #>
    param([AllowEmptyString()][string]$Value)

    if ([string]::IsNullOrEmpty($Value)) {
        return ""
    }

    $builder = New-Object System.Text.StringBuilder
    foreach ($character in $Value.ToCharArray()) {
        $code = [int]$character
        if ($character -eq '\') {
            [void]$builder.Append('\\')
        }
        elseif ($character -eq '"') {
            [void]$builder.Append('\"')
        }
        elseif ($character -eq "`n") {
            [void]$builder.Append('\n')
        }
        elseif ($character -eq "`t") {
            [void]$builder.Append('\t')
        }
        elseif ($code -lt 32) {
            continue
        }
        else {
            [void]$builder.Append($character)
        }
    }
    return $builder.ToString()
}

function Write-Buffer {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text)

    [void]$script:Buffer.Append($Text)
}

function Open-ProbeRunspace {
    <# 探针跑在独立 runspace 里：一是可以用 WaitOne 实现真正的超时打断，
       二是探针拿不到本脚本的变量，避免误引用。 #>
    param()

    $runspace = [RunspaceFactory]::CreateRunspace()
    $runspace.Open()
    return $runspace
}

function Invoke-ProbeCommand {
    <# 执行一条只读命令，返回 @{ Output = 文本; ExitCode = 整数 }。 #>
    param([Parameter(Mandatory = $true)][string]$Command)

    if ($null -eq $script:ProbeRunspace) {
        $script:ProbeRunspace = Open-ProbeRunspace
    }

    $shell = [PowerShell]::Create()
    $shell.Runspace = $script:ProbeRunspace

    # 探针里的错误不应该中断采集，所以显式把 ErrorActionPreference 降为 Continue；
    # 每次都把 LASTEXITCODE 归零，避免上一条原生命令的退出码串到下一项。
    $prelude = "`$ErrorActionPreference = 'Continue'" + "`n" + "`$global:LASTEXITCODE = 0" + "`n"
    $wrapped = $prelude + "& {" + "`n" + $Command + "`n" + "} | Out-String -Width 200"
    [void]$shell.AddScript($wrapped)

    $output = ""
    $exitCode = 0
    $handle = $shell.BeginInvoke()

    if (-not $handle.AsyncWaitHandle.WaitOne($script:ProbeTimeout * 1000)) {
        [void]$shell.Stop()
        $shell.Dispose()
        # 被打断的 runspace 状态不可信，直接换一个新的给后续探针用。
        $script:ProbeRunspace.Dispose()
        $script:ProbeRunspace = $null
        return @{ Output = "命令超过 $($script:ProbeTimeout) 秒未返回，已停止采集这一项。"; ExitCode = 124 }
    }

    try {
        $results = $shell.EndInvoke($handle)
        if ($null -ne $results) {
            $output = ($results -join "")
        }

        $errorText = ""
        if ($shell.Streams.Error.Count -gt 0) {
            $rendered = New-Object System.Collections.Generic.List[string]
            foreach ($record in $shell.Streams.Error) {
                $rendered.Add($record.ToString())
            }
            $errorText = ($rendered -join "`n")
        }

        $nativeExit = $script:ProbeRunspace.SessionStateProxy.GetVariable("LASTEXITCODE")
        if (($nativeExit -is [int]) -and ($nativeExit -ne 0)) {
            $exitCode = $nativeExit
        }
        elseif ($errorText.Length -gt 0) {
            $exitCode = 1
        }

        if ($errorText.Length -gt 0) {
            if ($output.Length -gt 0) {
                $output = $output.TrimEnd("`r", "`n") + "`n" + $errorText
            }
            else {
                $output = $errorText
            }
        }
    }
    catch {
        $output = $_.Exception.Message
        $exitCode = 1
    }
    finally {
        $shell.Dispose()
    }

    return @{ Output = $output; ExitCode = $exitCode }
}

function Write-ProbeRecord {
    <# 把一条探针结果写进缓冲区。JSON 布局与 Bash 版保持逐行同构。 #>
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [AllowEmptyString()][string]$Command = "",
        [AllowEmptyString()][string]$Output = "",
        [AllowNull()][object]$ExitCode = $null
    )

    $script:ProbeCount = $script:ProbeCount + 1
    if (($null -ne $ExitCode) -and ($ExitCode -ne 0)) {
        $script:ProbeFailureCount = $script:ProbeFailureCount + 1
    }

    $clean = Protect-SensitiveText $Output

    if ($script:OutputFormat -eq "json") {
        if ($script:ProbeIndex -gt 0) {
            Write-Buffer ",`n"
        }
        Write-Buffer "      {`n"
        Write-Buffer "        `"label`": `"$(Convert-ToJsonText $Label)`",`n"
        if ([string]::IsNullOrEmpty($Command)) {
            Write-Buffer "        `"command`": null,`n"
        }
        else {
            Write-Buffer "        `"command`": `"$(Convert-ToJsonText $Command)`",`n"
        }
        if ($null -eq $ExitCode) {
            Write-Buffer "        `"exit_code`": null,`n"
        }
        else {
            Write-Buffer "        `"exit_code`": $ExitCode,`n"
        }
        Write-Buffer "        `"output`": `"$(Convert-ToJsonText $clean)`"`n"
        Write-Buffer "      }"
    }
    else {
        Write-Buffer "### $Label`n`n"
        if (-not [string]::IsNullOrEmpty($Command)) {
            Write-Buffer ($CodeFence + "text`n")
            Write-Buffer "PS> $Command`n"
            Write-Buffer "$clean`n"
            Write-Buffer ($CodeFence + "`n`n")
            Write-Buffer "退出码：$ExitCode`n`n"
        }
        else {
            Write-Buffer "$clean`n`n"
        }
    }

    $script:ProbeIndex = $script:ProbeIndex + 1
}

function Write-SkipRecord {
    <# 记录一条被主动跳过的检查，并说明为什么不做。 #>
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Reason
    )

    $script:SkipCount = $script:SkipCount + 1
    Write-ProbeRecord -Label $Label -Command "" -Output "已跳过：$Reason" -ExitCode $null
}

function Invoke-Probe {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $result = Invoke-ProbeCommand -Command $Command
    Write-ProbeRecord -Label $Label -Command $Command -Output $result.Output -ExitCode $result.ExitCode
}

function Invoke-ProbeIfCommand {
    <# 命令不存在时记为 skipped，而不是把 "找不到 cmdlet" 当成机器故障。 #>
    param(
        [Parameter(Mandatory = $true)][string]$CommandName,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Command
    )

    if (Get-Command -Name $CommandName -ErrorAction SilentlyContinue) {
        Invoke-Probe -Label $Label -Command $Command
    }
    else {
        Write-SkipRecord -Label $Label -Reason "本机没有 $CommandName，无法采集这一项。"
    }
}

function Invoke-SectionProbe {
    <# 每个小节的只读探针清单。命令文本原样写进输出，方便工程师复核。 #>
    param([Parameter(Mandatory = $true)][string]$Id)

    switch ($Id) {
        "overview" {
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "操作系统版本与启动时间" `
                -Command "Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, InstallDate, LastBootUpTime | Format-List"
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "已连续运行时长" `
                -Command '$os = Get-CimInstance -ClassName Win32_OperatingSystem; ((Get-Date) - $os.LastBootUpTime).ToString("d\.hh\:mm\:ss")'
            Invoke-Probe -Label "PowerShell 版本" `
                -Command '$PSVersionTable.PSVersion.ToString(); "Edition: " + $PSVersionTable.PSEdition'
            Invoke-ProbeIfCommand -CommandName "Get-ExecutionPolicy" -Label "执行策略" `
                -Command "Get-ExecutionPolicy -List | Format-Table -AutoSize"
            Invoke-Probe -Label "当前时间（本地与 UTC）" `
                -Command '(Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz"); (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")'
            Invoke-ProbeIfCommand -CommandName "w32tm" -Label "时间同步状态" `
                -Command "w32tm /query /status"
        }
        "hardware" {
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "机型与制造商" `
                -Command "Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object Manufacturer, Model, SystemFamily, NumberOfProcessors, TotalPhysicalMemory | Format-List"
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "CPU 概览" `
                -Command "Get-CimInstance -ClassName Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | Format-List"
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "固件（BIOS/UEFI）版本" `
                -Command "Get-CimInstance -ClassName Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, ReleaseDate | Format-List"
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "内存条清单" `
                -Command "Get-CimInstance -ClassName Win32_PhysicalMemory | Select-Object BankLabel, DeviceLocator, Capacity, Speed, Manufacturer | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-PnpDevice" -Label "状态异常的设备（设备管理器黄色感叹号）" `
                -Command 'Get-PnpDevice | Where-Object { $_.Status -ne "OK" } | Select-Object Status, Class, FriendlyName, InstanceId | Format-Table -AutoSize'
        }
        "storage" {
            Invoke-ProbeIfCommand -CommandName "Get-Volume" -Label "卷与剩余空间" `
                -Command 'Get-Volume | Sort-Object DriveLetter | Select-Object DriveLetter, FileSystemLabel, FileSystem, HealthStatus, @{ Name = "SizeGB"; Expression = { [math]::Round($_.Size / 1GB, 1) } }, @{ Name = "FreeGB"; Expression = { [math]::Round($_.SizeRemaining / 1GB, 1) } } | Format-Table -AutoSize'
            Invoke-ProbeIfCommand -CommandName "Get-Disk" -Label "磁盘与分区风格" `
                -Command "Get-Disk | Select-Object Number, FriendlyName, BusType, PartitionStyle, HealthStatus, OperationalStatus | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-PhysicalDisk" -Label "物理磁盘健康状态" `
                -Command 'Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, HealthStatus, OperationalStatus, @{ Name = "SizeGB"; Expression = { [math]::Round($_.Size / 1GB, 1) } } | Format-Table -AutoSize'
            Invoke-ProbeIfCommand -CommandName "Get-StorageReliabilityCounter" -Label "SMART 可靠性计数（可能需要管理员）" `
                -Command 'Get-PhysicalDisk | ForEach-Object { $_ | Get-StorageReliabilityCounter } | Select-Object DeviceId, Temperature, Wear, PowerOnHours, ReadErrorsTotal, WriteErrorsTotal | Format-Table -AutoSize'
        }
        "memory" {
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "物理内存用量" `
                -Command '$os = Get-CimInstance -ClassName Win32_OperatingSystem; [pscustomobject]@{ TotalMB = [math]::Round($os.TotalVisibleMemorySize / 1KB, 0); FreeMB = [math]::Round($os.FreePhysicalMemory / 1KB, 0) } | Format-List'
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "页面文件用量" `
                -Command "Get-CimInstance -ClassName Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage | Format-List"
            Invoke-Probe -Label "内存占用前 10 的进程" `
                -Command 'Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Id, ProcessName, @{ Name = "WorkingSetMB"; Expression = { [math]::Round($_.WorkingSet64 / 1MB, 1) } } | Format-Table -AutoSize'
        }
        "process" {
            Invoke-Probe -Label "CPU 累计时间前 15 的进程" `
                -Command 'Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Id, ProcessName, CPU, @{ Name = "WorkingSetMB"; Expression = { [math]::Round($_.WorkingSet64 / 1MB, 1) } } | Format-Table -AutoSize'
            Invoke-Probe -Label "进程总数" `
                -Command '"进程总数：" + @(Get-Process).Count'
            Invoke-Probe -Label "句柄数前 5 的进程" `
                -Command "Get-Process | Sort-Object HandleCount -Descending | Select-Object -First 5 Id, ProcessName, HandleCount | Format-Table -AutoSize"
        }
        "network" {
            Invoke-ProbeIfCommand -CommandName "Get-NetIPConfiguration" -Label "IP 配置" `
                -Command "Get-NetIPConfiguration | Format-List InterfaceAlias, IPv4Address, IPv6Address, IPv4DefaultGateway, DNSServer"
            Invoke-ProbeIfCommand -CommandName "Get-NetAdapter" -Label "网卡状态" `
                -Command "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-DnsClientServerAddress" -Label "DNS 服务器" `
                -Command "Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, ServerAddresses | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-NetRoute" -Label "默认路由" `
                -Command 'Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object InterfaceAlias, NextHop, RouteMetric | Format-Table -AutoSize'
            Invoke-ProbeIfCommand -CommandName "Get-NetTCPConnection" -Label "监听端口（前 30）" `
                -Command "Get-NetTCPConnection -State Listen | Sort-Object LocalPort | Select-Object -First 30 LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-DnsClientCache" -Label "DNS 缓存条数" `
                -Command '"缓存条数：" + @(Get-DnsClientCache).Count'
        }
        "services" {
            Invoke-ProbeIfCommand -CommandName "Get-Service" -Label "设为自动但未运行的服务" `
                -Command 'Get-Service | Where-Object { $_.StartType -eq "Automatic" -and $_.Status -ne "Running" } | Select-Object Name, DisplayName, Status | Format-Table -AutoSize'
            Invoke-ProbeIfCommand -CommandName "Get-Service" -Label "修复相关关键服务的状态" `
                -Command "Get-Service -Name wuauserv, bits, cryptSvc, msiserver, Spooler, WSearch, fhsvc -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-ScheduledTask" -Label "非微软的就绪计划任务（前 20）" `
                -Command 'Get-ScheduledTask | Where-Object { $_.State -ne "Disabled" -and $_.TaskPath -notlike "\Microsoft\*" } | Select-Object -First 20 TaskPath, TaskName, State | Format-Table -AutoSize'
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "开机自启项" `
                -Command "Get-CimInstance -ClassName Win32_StartupCommand | Select-Object Name, Location, Command | Format-Table -AutoSize"
        }
        "updates" {
            Invoke-ProbeIfCommand -CommandName "Get-HotFix" -Label "最近安装的 5 个更新" `
                -Command "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID, Description, InstalledOn | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Test-Path" -Label "待重启标记（只读注册表）" `
                -Command '@("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending", "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired") | ForEach-Object { [pscustomobject]@{ Key = $_; Exists = (Test-Path -Path $_) } } | Format-Table -AutoSize'
            Invoke-ProbeIfCommand -CommandName "Get-ItemProperty" -Label "待重命名的文件操作数（PendingFileRenameOperations）" `
                -Command '$key = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager"; $value = (Get-ItemProperty -Path $key -Name PendingFileRenameOperations -ErrorAction SilentlyContinue); if ($null -eq $value) { "没有待重命名的文件操作" } else { "待处理条目数：" + @($value.PendingFileRenameOperations).Count }'
            Write-SkipRecord -Label "待安装更新清单" `
                -Reason "查询待安装更新需要联系 Windows Update 服务器，本脚本不发起网络请求；请在 playbook-windows-update-troubleshooting.md 里按步骤确认。"
        }
        "security" {
            Invoke-ProbeIfCommand -CommandName "Get-MpComputerStatus" -Label "Microsoft Defender 状态" `
                -Command "Get-MpComputerStatus | Select-Object AMServiceEnabled, AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureLastUpdated, QuickScanEndTime | Format-List"
            Invoke-ProbeIfCommand -CommandName "Get-NetFirewallProfile" -Label "防火墙三个配置档" `
                -Command "Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-BitLockerVolume" -Label "BitLocker 卷状态" `
                -Command "Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, ProtectionStatus, EncryptionPercentage | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Confirm-SecureBootUEFI" -Label "安全启动是否开启" `
                -Command "Confirm-SecureBootUEFI"
            Invoke-ProbeIfCommand -CommandName "Get-ItemProperty" -Label "UAC 相关策略（只读注册表）" `
                -Command 'Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" | Select-Object EnableLUA, ConsentPromptBehaviorAdmin, PromptOnSecureDesktop | Format-List'
            Invoke-ProbeIfCommand -CommandName "Get-ComputerRestorePoint" -Label "最近 5 个系统还原点" `
                -Command "Get-ComputerRestorePoint | Select-Object -Last 5 SequenceNumber, Description, CreationTime | Format-Table -AutoSize"
            Invoke-ProbeIfCommand -CommandName "Get-Tpm" -Label "TPM 状态（可能需要管理员）" `
                -Command "Get-Tpm | Select-Object TpmPresent, TpmReady, TpmEnabled, ManagedAuthLevel | Format-List"
        }
        "logs" {
            Invoke-ProbeIfCommand -CommandName "Get-WinEvent" -Label "近 24 小时 System 日志的严重与错误事件（前 20）" `
                -Command 'Get-WinEvent -FilterHashtable @{ LogName = "System"; Level = 1, 2; StartTime = (Get-Date).AddHours(-24) } -MaxEvents 20 -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, ProviderName, @{ Name = "FirstLine"; Expression = { ($_.Message -split "\r?\n")[0] } } | Format-Table -AutoSize -Wrap'
            Invoke-ProbeIfCommand -CommandName "Get-WinEvent" -Label "近 24 小时 Application 日志的错误事件（前 15）" `
                -Command 'Get-WinEvent -FilterHashtable @{ LogName = "Application"; Level = 1, 2; StartTime = (Get-Date).AddHours(-24) } -MaxEvents 15 -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, ProviderName, @{ Name = "FirstLine"; Expression = { ($_.Message -split "\r?\n")[0] } } | Format-Table -AutoSize -Wrap'
            Invoke-ProbeIfCommand -CommandName "Get-WinEvent" -Label "近 7 天异常关机与蓝屏事件（41 / 1001 / 6008）" `
                -Command 'Get-WinEvent -FilterHashtable @{ LogName = "System"; Id = 41, 1001, 6008; StartTime = (Get-Date).AddDays(-7) } -MaxEvents 10 -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, ProviderName | Format-Table -AutoSize'
            Invoke-Probe -Label "内存转储文件是否存在" `
                -Command '@("$env:SystemRoot\MEMORY.DMP", "$env:SystemRoot\Minidump") | ForEach-Object { [pscustomobject]@{ Path = $_; Exists = (Test-Path -LiteralPath $_) } } | Format-Table -AutoSize'
        }
        "power" {
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "电池状态" `
                -Command "Get-CimInstance -ClassName Win32_Battery | Select-Object Name, EstimatedChargeRemaining, BatteryStatus, DesignVoltage | Format-List"
            Invoke-ProbeIfCommand -CommandName "powercfg" -Label "支持的睡眠状态" `
                -Command "powercfg /a"
            Invoke-ProbeIfCommand -CommandName "powercfg" -Label "当前电源计划" `
                -Command "powercfg /getactivescheme"
            Invoke-ProbeIfCommand -CommandName "Get-CimInstance" -Label "温度传感器（多数机型不上报）" `
                -Command 'Get-CimInstance -Namespace "root/wmi" -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object InstanceName, @{ Name = "TempC"; Expression = { [math]::Round(($_.CurrentTemperature / 10) - 273.15, 1) } } | Format-Table -AutoSize'
        }
        default {
            Write-SkipRecord -Label $Id -Reason "该小节在 Windows 上没有定义探针。"
        }
    }
}

# --- 参数处理 ---------------------------------------------------------------

if ($ListSection.IsPresent) {
    Show-SectionList -Catalog $SectionCatalog
    exit 0
}

$knownIds = @()
foreach ($entry in $SectionCatalog) {
    $knownIds += $entry.Id
}

$wanted = @()
if ($PSBoundParameters.ContainsKey("Section") -and ($null -ne $Section)) {
    foreach ($raw in $Section) {
        foreach ($candidate in ($raw -split ",")) {
            $trimmed = $candidate.Trim()
            if ($trimmed.Length -eq 0) {
                continue
            }
            if ($knownIds -notcontains $trimmed) {
                # 刻意不用 throw：错误信息应该像 install.sh 的 fail() 一样只有一行，
                # 而不是甩给用户一整段 PowerShell 异常堆栈。
                [Console]::Error.WriteLine("错误：未知小节：$trimmed。用 -ListSection 查看全部。")
                exit 1
            }
            $wanted += $trimmed
        }
    }
}
if ($wanted.Count -eq 0) {
    $wanted = $knownIds
}

$platform = Get-HostPlatform
if ($platform -ne "windows") {
    Write-Status "提示：当前不是 Windows（检测到 $platform）。本脚本的探针面向 Windows，绝大多数检查会被记为 skipped；Linux 与 macOS 请改用 scripts/collect-health.sh。"
}

# --- 组装输出 ---------------------------------------------------------------

$generatedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$hostName = [Environment]::MachineName
$userName = [Environment]::UserName

if ($script:OutputFormat -eq "json") {
    Write-Buffer "{`n"
    Write-Buffer "  `"schema`": $OutputSchema,`n"
    Write-Buffer "  `"collector`": `"$(Convert-ToJsonText $CollectorName)`",`n"
    Write-Buffer "  `"generated_at`": `"$generatedAt`",`n"
    Write-Buffer "  `"platform`": `"$(Convert-ToJsonText $platform)`",`n"
    Write-Buffer "  `"read_only`": true,`n"
    Write-Buffer "  `"network_access`": false,`n"
    if ($NoIdentity.IsPresent) {
        Write-Buffer "  `"identity`": null,`n"
    }
    else {
        Write-Buffer "  `"identity`": { `"hostname`": `"$(Convert-ToJsonText $hostName)`", `"user`": `"$(Convert-ToJsonText $userName)`" },`n"
    }
    Write-Buffer "  `"sections`": [`n"
}
else {
    Write-Buffer "# 计算机健康证据采集（只读）`n`n"
    Write-Buffer "- 采集脚本：$CollectorName`n"
    Write-Buffer "- 采集时间（UTC）：$generatedAt`n"
    Write-Buffer "- 平台：$platform`n"
    if (-not $NoIdentity.IsPresent) {
        Write-Buffer "- 主机：$hostName（用户 $userName）`n"
    }
    Write-Buffer "- 全部命令均为只读查询，未发起网络请求。`n`n"
}

$sectionIndex = 0
foreach ($sectionId in $wanted) {
    $title = Get-SectionTitle -Catalog $SectionCatalog -Id $sectionId

    if ($script:OutputFormat -eq "json") {
        if ($sectionIndex -gt 0) {
            Write-Buffer ",`n"
        }
        Write-Buffer "    {`n"
        Write-Buffer "      `"id`": `"$(Convert-ToJsonText $sectionId)`",`n"
        Write-Buffer "      `"title`": `"$(Convert-ToJsonText $title)`",`n"
        Write-Buffer "      `"probes`": [`n"
    }
    else {
        Write-Buffer "## $title（$sectionId）`n`n"
    }

    $script:ProbeIndex = 0
    Invoke-SectionProbe -Id $sectionId

    if ($script:OutputFormat -eq "json") {
        Write-Buffer "`n      ]`n"
        Write-Buffer "    }"
    }
    $sectionIndex = $sectionIndex + 1
}

if ($script:OutputFormat -eq "json") {
    Write-Buffer "`n  ]`n"
    Write-Buffer "}`n"
}
else {
    Write-Buffer "---`n`n"
    Write-Buffer "共 $sectionIndex 个小节、$($script:ProbeCount) 项检查，其中 $($script:SkipCount) 项主动跳过、$($script:ProbeFailureCount) 项命令返回非零。`n"
}

if ($null -ne $script:ProbeRunspace) {
    $script:ProbeRunspace.Dispose()
    $script:ProbeRunspace = $null
}

$document = $script:Buffer.ToString()

if ([string]::IsNullOrEmpty($OutputPath)) {
    [Console]::Out.Write($document)
}
else {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $temporary = "$OutputPath.tmp"
    [IO.File]::WriteAllText($temporary, $document, $utf8NoBom)
    Move-Item -LiteralPath $temporary -Destination $OutputPath -Force
    Write-Status "已写入 $OutputPath（$sectionIndex 个小节，$($script:ProbeCount) 项检查，$($script:SkipCount) 项跳过，$($script:ProbeFailureCount) 项返回非零）"
}

exit 0
