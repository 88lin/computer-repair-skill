# Windows 工具映射

默认使用 PowerShell。先确认当前宿主运行的是 Windows PowerShell 5.1 还是 PowerShell 7；优先调用带 `-LiteralPath`、`-ErrorAction Stop` 和结构化对象输出的 cmdlet。

占位符 `<HOST>`、`<DOMAIN>`、`<URL>`、`<PID>`、`<SERVICE>`、`<PRINTER>`、`<APP>` 和 `<PATH>` 必须替换成已验证的字面值。不要把尖括号原样交给 Shell。

## 网络

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `win_network_info` | `Get-NetIPConfiguration`、`Get-NetRoute`、`Get-DnsClientServerAddress` | 只读 |
| `win_ping` | `ping.exe -n <COUNT> <HOST>` | 只读 |
| `win_dns_check` | `Resolve-DnsName -Name '<DOMAIN>' -ErrorAction Stop` | 只读 |
| `win_http_check` | `Invoke-WebRequest -Uri '<URL>' -Method Head -MaximumRedirection 5 -TimeoutSec 15 -UseBasicParsing` | 只读联网 |
| `win_flush_dns` | `ipconfig.exe /flushdns` | 可逆变更，先确认 |

网络快照：

```powershell
Get-NetIPConfiguration |
  Select-Object InterfaceAlias, InterfaceDescription, NetProfile, IPv4Address, IPv4DefaultGateway, DNSServer

Get-NetRoute -DestinationPrefix '0.0.0.0/0' |
  Sort-Object RouteMetric |
  Select-Object -First 5 InterfaceAlias, NextHop, RouteMetric, State

Get-DnsClientServerAddress -AddressFamily IPv4 |
  Select-Object InterfaceAlias, ServerAddresses
```

HTTP 检查需要记录状态码、最终 URL 和耗时。目标不支持 `HEAD` 时改用 `GET`，限制响应体读取范围。

## 打印机

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `win_printer_list` | `Get-Printer` | 只读 |
| `win_print_queue` | `Get-PrintJob -PrinterName '<PRINTER>'` | 只读 |
| `win_cancel_print_jobs` | `Get-PrintJob -PrinterName '<PRINTER>' \| Remove-PrintJob` | 高影响，先列出作业并确认 |
| `win_restart_spooler` | `Restart-Service -Name Spooler` | 会中断打印，先确认 |

```powershell
Get-Printer |
  Select-Object Name, DriverName, PortName, PrinterStatus, Shared

Get-PrintJob -PrinterName '<PRINTER>' |
  Select-Object ID, DocumentName, UserName, JobStatus, Size, SubmittedTime
```

## 性能与存储

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `win_system_info` | 查询 `Win32_OperatingSystem`、`Win32_ComputerSystem`、`Win32_Processor` | 只读 |
| `win_process_list` | `Get-Process`，分别按 CPU 和工作集排序 | 只读 |
| `win_disk_usage` | 优先查询 `Win32_LogicalDisk`；`Storage` 模块可用时补充 `Get-Volume` | 只读 |
| `win_kill_process` | `Stop-Process -Id <PID>` | 高影响，确认 PID 和用途 |
| `win_clear_caches` | 先测量并枚举具体缓存目录，再删除明确条目 | 高影响，读取安全策略 |

```powershell
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor
[pscustomobject]@{
  Caption = $os.Caption
  Version = $os.Version
  Build = $os.BuildNumber
  LastBoot = $os.LastBootUpTime
  MemoryGB = [math]::Round($computer.TotalPhysicalMemory / 1GB, 2)
  CPU = ($cpu.Name -join '; ')
}

Get-Process |
  Sort-Object WorkingSet64 -Descending |
  Select-Object -First 15 Id, ProcessName, CPU,
    @{n='WorkingSetMB';e={[math]::Round($_.WorkingSet64 / 1MB, 1)}}

Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' |
  Select-Object DeviceID, VolumeName, FileSystem,
    @{n='SizeGB';e={[math]::Round($_.Size / 1GB, 1)}},
    @{n='FreeGB';e={[math]::Round($_.FreeSpace / 1GB, 1)}}
```

需要卷健康、BitLocker 或分区细节时再尝试 `Get-Volume`。若 `Storage` 模块加载失败，继续使用 CIM 结果并明确缺少的字段。

CPU 字段通常是进程累计 CPU 时间，不等同于瞬时百分比。需要瞬时负载时使用性能计数器并标注采样窗口。

## 应用与日志

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `win_app_list` | 读取 HKLM/HKCU 的 Uninstall 注册表项 | 只读 |
| `win_app_logs` | `Get-WinEvent` 查询 Application 日志 | 只读 |
| `win_app_data_ls` | 对 `%APPDATA%`、`%LOCALAPPDATA%` 的具体应用目录使用 `Get-ChildItem` | 只读 |
| `win_clear_app_cache` | 检查并关闭应用后清理具体缓存子目录 | 高影响，读取安全策略 |
| `win_move_file` | `Move-Item -LiteralPath '<SOURCE>' -Destination '<DESTINATION>'` | 状态变更，先确认并检查目标冲突 |

```powershell
$uninstallRoots = @(
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
Get-ItemProperty $uninstallRoots -ErrorAction SilentlyContinue |
  Where-Object DisplayName |
  Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
  Sort-Object DisplayName

Get-WinEvent -FilterHashtable @{
  LogName = 'Application'
  StartTime = (Get-Date).AddHours(-2)
} -ErrorAction Stop |
  Select-Object -First 100 TimeCreated, LevelDisplayName, ProviderName, Id, Message
```

日志量大时先按时间、Provider、事件级别和事件 ID 缩小范围。

## 应用生命周期

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `win_package_inventory` | `winget list --source winget`、`Get-AppxPackage`、卸载注册表项，分别保留来源和包 ID | 只读 |
| `win_package_metadata` | `winget show --id '<ID>' --exact` 或官方源页面；对安装器补充签名和 SHA-256 | 只读联网 |
| `win_file_signature` | `Get-AuthenticodeSignature -LiteralPath '<PATH>'` | 只读 |
| `win_persistence_snapshot` | 组合 `Win32_Service`、`Win32_StartupCommand`、`Get-ScheduledTask` 和已确认的注册表项 | 只读 |
| `win_package_install` | 对已确认的精确 ID 使用 `winget install --id '<ID>' --exact` 或用户选定的 Chocolatey 包；保留来源与版本 | 高影响，先确认 |
| `win_package_uninstall` | 对已确认的精确 ID 使用 `winget uninstall --id '<ID>' --exact`、原生卸载器或 `Remove-AppxPackage -Package '<FULL_NAME>'` | 高影响，先确认 |

不要把 `winget`、Chocolatey、Appx 和注册表卸载项的显示名称直接拼接进
Shell。先列出精确 ID、发布者、版本、来源和卸载字符串，再通过结构化参数
执行。若 `winget` 不存在，报告缺失并让用户选择官方安装路径；不要自动下载
未知 App Installer、远程脚本或未签名二进制。

## 存储、策略与恢复

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `win_path_inventory` | 对已确认的字面路径使用 `Get-ChildItem -LiteralPath`，限制深度并跳过 reparse point | 只读但可能较慢 |
| `win_file_hash` | 对明确文件使用 `Get-FileHash -Algorithm SHA256` | 只读 |
| `win_recycle_path` | 使用宿主的回收站能力或 `Microsoft.VisualBasic.FileIO.FileSystem`，只传入已确认的字面路径 | 高影响，先确认 |
| `win_registry_snapshot` | `reg.exe export '<KEY>' '<BACKUP_FILE>' /y`，备份文件放在已确认的隔离目录 | 可逆变更，先确认目标 |
| `win_scheduled_task_list` | `Get-ScheduledTask`，按 TaskPath、TaskName、State 和 Actions 输出 | 只读 |
| `win_policy_list` | 读取明确的 `HKLM/HKCU:\Software\Policies` 子项和浏览器策略页 | 只读 |
| `win_recovery_image_scan` | 对写保护的磁盘镜像调用宿主的取证/恢复工具，报告输出到独立目标卷 | 只读；源盘禁止写入 |
| `win_volume_inventory` | `Get-Disk`、`Get-Partition`、`Get-Volume`，必要时补充 `Win32_LogicalDisk` | 只读 |
| `win_bitlocker_status` | `Get-BitLockerVolume`；家庭版或命令不可用时记录缺失并使用设置界面核对 | 只读 |

目录清单只报告路径、类型、大小、时间、扩展名比例和计数。不要为了解释未知目录而读取文件正文；如需外部模型分析，只发送去标识化元数据和最多 20 条相对路径样本。

## 系统诊断与服务

| Playbook 工具 | 推荐实现 | 风险 |
|---|---|---|
| `win_system_summary` | 组合系统、磁盘、网络和启动时间查询 | 只读 |
| `win_read_file` | `Get-Content -LiteralPath '<PATH>'`，先检查大小 | 只读 |
| `win_read_log` | `Get-WinEvent` 或对明确文本日志使用 `Get-Content -Tail` | 只读 |
| `shell_run` | 使用宿主终端执行 PowerShell 或 `cmd.exe` 命令 | 按具体输入分类 |
| `win_startup_programs` | 查询 `Win32_StartupCommand` 和常见 Run 注册表项 | 只读 |
| `win_service_list` | `Get-Service`，需要时补充 `Win32_Service` | 只读 |
| `win_restart_service` | `Restart-Service -Name '<SERVICE>'` | 会中断依赖，先确认 |
| `win_pnp_device_list` | `Get-PnpDevice` 与 `Get-PnpDeviceProperty -KeyName 'DEVPKEY_Device_HardwareIds'` | 只读 |
| `win_driver_inventory` | `Get-CimInstance Win32_PnPSignedDriver`，按设备实例筛选 | 只读 |

```powershell
Get-CimInstance Win32_StartupCommand |
  Select-Object Name, Command, Location, User

Get-CimInstance Win32_Service |
  Select-Object Name, DisplayName, State, StartMode, StartName, PathName
```

读取文件前使用 `Get-Item -LiteralPath '<PATH>'` 获取类型和大小。二进制、超大文件或凭据文件只读取诊断所需的元数据。

## 管理员权限

- 先用普通权限完成诊断。
- 需要管理员权限时展示单条准确命令、原因、影响和回滚。
- 使用宿主的提升机制或由用户在管理员终端执行，不打开长期高权限会话。
- 重启 Windows Update、BITS、打印和网络服务前记录原始状态。
- 不用 `Remove-Item`、`rmdir` 或扩展名通配符替代 `win_recycle_path`；不对 `C:\`、用户根目录、浏览器 profile 或应用数据根目录做递归删除。
