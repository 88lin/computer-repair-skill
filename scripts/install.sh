#!/usr/bin/env bash
# 把 computer-repair-skill 安装到某个 Agent 的 Skills 根目录。
#
# 设计约束：
#   * 默认绝不覆盖已存在的安装，必须显式 --force。
#   * 所有写入先落到同一文件系统的暂存目录，再用一次 mv 原子生效，失败自动回滚。
#   * 安装后写出清单（含每个文件的 sha256），使 --verify 与 --uninstall 可审计。
#   * 兼容 bash 3.2（macOS 自带版本）：不使用关联数组、mapfile、${var^^} 等新语法。
set -euo pipefail

skill_name="computer-repair-skill"
manifest_name=".computer-repair-skill-install.json"
backup_dir_name=".computer-repair-skill-backups"
manifest_schema=1

action="install"
target="codex"
destination=""
backup_dir=""
force=0
dry_run=0
link_mode=0
purge=0
quiet=0
sha256_tool=""

# 内置 Agent 预设。每一项的全局 Skills 目录都按官方 skills CLI 文档核对过。
presets="codex claude claude-code cursor gemini-cli github-copilot windsurf opencode openclaw \
agents universal antigravity augment qwen-code trae roo crush goose droid continue openhands custom"

usage() {
  cat <<'EOF'
用法: ./scripts/install.sh [操作] [选项]

操作（互斥，缺省为安装）:
      --verify           校验已安装副本与清单是否一致，只读，不做任何修改
      --uninstall        按清单移除已安装副本
      --list-targets     列出内置 Agent 预设及其解析后的 Skills 根目录
  -h, --help             显示帮助

选项:
      --target <preset>  Agent 预设，默认 codex；用 --list-targets 查看全部
      --destination <p>  覆盖预设的 Skills 根目录（target 为 custom 时必填）
      --backup-dir <p>   覆盖备份目录，默认 <skills 根目录>/.computer-repair-skill-backups
      --link             创建指向仓库的符号链接（开发模式），不复制文件
      --force            允许覆盖已存在的安装；覆盖前先备份
      --purge            仅配合 --uninstall：连备份目录一起删除
      --dry-run          只打印将要执行的操作，不写入任何文件
      --quiet            只输出警告与错误

示例:
  ./scripts/install.sh --target claude
  ./scripts/install.sh --target custom --destination ~/skills --force
  ./scripts/install.sh --verify --target claude
  ./scripts/install.sh --uninstall --target claude --purge
EOF
}

fail() {
  printf '错误：%s\n' "$1" >&2
  exit 1
}

warn() {
  printf '警告：%s\n' "$1" >&2
}

log() {
  if ((quiet == 0)); then
    printf '%s\n' "$1"
  fi
}

set_action() {
  if [[ "$action" != "install" ]]; then
    fail "操作 --$1 与 --$action 互斥，一次只能指定一个。"
  fi
  action="$1"
}

while (($# > 0)); do
  case "$1" in
    --target)
      (($# >= 2)) || fail "--target 缺少参数。"
      target="$2"
      shift 2
      ;;
    --destination)
      (($# >= 2)) || fail "--destination 缺少参数。"
      destination="$2"
      shift 2
      ;;
    --backup-dir)
      (($# >= 2)) || fail "--backup-dir 缺少参数。"
      backup_dir="$2"
      shift 2
      ;;
    --verify)
      set_action verify
      shift
      ;;
    --uninstall)
      set_action uninstall
      shift
      ;;
    --list-targets)
      set_action list-targets
      shift
      ;;
    --link)
      link_mode=1
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    --purge)
      purge=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --quiet)
      quiet=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      fail "未知参数：$1。用 --help 查看用法。"
      ;;
  esac
done

if ((purge == 1)) && [[ "$action" != "uninstall" ]]; then
  fail "--purge 只能与 --uninstall 一起使用。"
fi

# --- 路径工具 ---------------------------------------------------------------

# 展开用户传入的字面量波浪号路径。
# case 分支里的 ~ 必须加引号：不加引号时 shell 会先做波浪号展开，模式就变成 $HOME/*，
# 反而匹配不到用户输入的字面量 "~/..."。因此这里的 SC2088 是刻意为之。
# shellcheck disable=SC2088
expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${1#"~/"}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

# 纯字符串路径规范化：故意不调用 realpath，也不创建任何目录，
# 这样 --dry-run 才能真正做到零副作用。
normalize_path() (
  path="$1"
  case "$path" in
    /*) ;;
    *) path="$PWD/$path" ;;
  esac

  set -f
  IFS='/'
  # 这里需要按 / 分词，因此必须不加引号；set -f 已关闭通配符展开。
  # shellcheck disable=SC2086
  set -- $path

  out=""
  for segment in "$@"; do
    case "$segment" in
      '' | '.') continue ;;
      '..') out="${out%/*}" ;;
      *) out="$out/$segment" ;;
    esac
  done

  printf '%s\n' "${out:-/}"
)

config_home() {
  printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}"
}

# 各 Agent 的默认全局 Skills 根目录；custom 返回空串表示必须显式给出目录。
preset_root() {
  case "$1" in
    codex) printf '%s/skills\n' "${CODEX_HOME:-$HOME/.codex}" ;;
    claude | claude-code) printf '%s/skills\n' "${CLAUDE_HOME:-$HOME/.claude}" ;;
    cursor) printf '%s/.cursor/skills\n' "$HOME" ;;
    gemini-cli) printf '%s/.gemini/skills\n' "$HOME" ;;
    github-copilot) printf '%s/.copilot/skills\n' "$HOME" ;;
    windsurf) printf '%s/.codeium/windsurf/skills\n' "$HOME" ;;
    opencode) printf '%s/opencode/skills\n' "$(config_home)" ;;
    openclaw) printf '%s/.openclaw/skills\n' "$HOME" ;;
    agents) printf '%s/.agents/skills\n' "$HOME" ;;
    universal) printf '%s/agents/skills\n' "$(config_home)" ;;
    antigravity) printf '%s/.gemini/antigravity/skills\n' "$HOME" ;;
    augment) printf '%s/.augment/skills\n' "$HOME" ;;
    qwen-code) printf '%s/.qwen/skills\n' "$HOME" ;;
    trae) printf '%s/.trae/skills\n' "$HOME" ;;
    roo) printf '%s/.roo/skills\n' "$HOME" ;;
    crush) printf '%s/crush/skills\n' "$(config_home)" ;;
    goose) printf '%s/goose/skills\n' "$(config_home)" ;;
    droid) printf '%s/.factory/skills\n' "$HOME" ;;
    continue) printf '%s/.continue/skills\n' "$HOME" ;;
    openhands) printf '%s/.openhands/skills\n' "$HOME" ;;
    custom) printf '\n' ;;
    *) return 1 ;;
  esac
}

list_targets() {
  printf '%-16s %s\n' "预设" "全局 Skills 根目录"
  for name in $presets; do
    root="$(preset_root "$name")" || fail "内部错误：预设 $name 未定义。"
    if [[ -z "$root" ]]; then
      printf '%-16s %s\n' "$name" "（必须配合 --destination）"
    else
      printf '%-16s %s\n' "$name" "$(normalize_path "$(expand_user_path "$root")")"
    fi
  done
  printf '\n项目级安装请改用 --destination，例如 --destination ./.claude/skills。\n'
}

resolve_skills_root() {
  if [[ -n "$destination" ]]; then
    normalize_path "$(expand_user_path "$destination")"
    return
  fi

  root="$(preset_root "$target")" || fail "不支持的 target：${target}。用 --list-targets 查看全部预设。"
  [[ -n "$root" ]] || fail "target 为 custom 时必须提供 --destination。"
  normalize_path "$(expand_user_path "$root")"
}

# --- 摘要与清单 -------------------------------------------------------------

detect_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256_tool="sha256sum"
  elif command -v shasum >/dev/null 2>&1; then
    sha256_tool="shasum"
  elif command -v openssl >/dev/null 2>&1; then
    sha256_tool="openssl"
  else
    fail "找不到 sha256sum、shasum 或 openssl，无法生成校验清单。"
  fi
}

hash_file() {
  case "$sha256_tool" in
    sha256sum) sha256sum -- "$1" | awk '{ print $1 }' ;;
    shasum) shasum -a 256 -- "$1" | awk '{ print $1 }' ;;
    openssl) openssl dgst -sha256 -- "$1" | awk '{ print $NF }' ;;
    *) fail "内部错误：未初始化摘要工具。" ;;
  esac
}

# 列出目录下的全部普通文件（相对路径、LC_ALL=C 排序），保证清单可复现。
list_payload_files() {
  (
    CDPATH='' cd -- "$1" || exit 1
    find . -type f -print | sed 's|^\./||' | LC_ALL=C sort
  )
}

# 生成 "相对路径 sha256" 列表。清单以空格分隔，因此这里强制校验文件名字符集。
build_digest_list() {
  digest_root="$1"
  link_probe="$(find "$digest_root" -type l 2>/dev/null || true)"
  if [[ -n "$link_probe" ]]; then
    fail "Skill 载荷中存在符号链接，清单无法保证可复现：$digest_root"
  fi

  list_payload_files "$digest_root" | while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    case "$rel" in
      *[!A-Za-z0-9._/-]*)
        fail "文件名含清单不支持的字符（仅允许字母、数字、点、下划线、连字符和斜杠）：$rel"
        ;;
    esac
    printf '%s %s\n' "$rel" "$(hash_file "$digest_root/$rel")"
  done
}

json_string() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

manifest_scalar() {
  sed -n 's/^[[:space:]]*"'"$2"'": *"\([^"]*\)".*/\1/p' "$1" | head -n 1
}

# 清单里的文件条目固定一行一项，路径字符集在写入时已校验，因此可安全用 sed 解析。
manifest_digests() {
  sed -n 's/^[[:space:]]*{ *"path": *"\([^"]*\)", *"sha256": *"\([0-9a-f]*\)" *}.*/\1 \2/p' "$1"
}

manifest_paths_of() {
  manifest_digests "$1" | awk '{ print $1 }'
}

write_manifest() {
  target_manifest="$1"
  mode="$2"
  digest_list="$3"
  file_count="$4"
  tmp_manifest="$target_manifest.tmp.$$"

  {
    printf '{\n'
    printf '  "schema": %s,\n' "$manifest_schema"
    printf '  "skill": "%s",\n' "$(json_string "$skill_name")"
    printf '  "version": "%s",\n' "$(json_string "$skill_version")"
    printf '  "install_mode": "%s",\n' "$(json_string "$mode")"
    printf '  "installed_at": "%s",\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf '  "installer": "scripts/install.sh",\n'
    printf '  "source_dir": "%s",\n' "$(json_string "$source_dir")"
    if [[ -n "$source_commit" ]]; then
      printf '  "source_commit": "%s",\n' "$(json_string "$source_commit")"
    else
      printf '  "source_commit": null,\n'
    fi
    printf '  "target_path": "%s",\n' "$(json_string "$target_path")"
    printf '  "file_count": %s,\n' "$file_count"
    printf '  "files": [\n'
    if ((file_count > 0)); then
      printf '%s\n' "$digest_list" | awk '
        { entries[NR] = sprintf("    { \"path\": \"%s\", \"sha256\": \"%s\" }", $1, $2) }
        END {
          for (i = 1; i <= NR; i++) {
            printf "%s%s\n", entries[i], (i < NR ? "," : "")
          }
        }'
    fi
    printf '  ]\n'
    printf '}\n'
  } >"$tmp_manifest"

  mv -- "$tmp_manifest" "$target_manifest"
}

# --- 公共上下文 -------------------------------------------------------------

script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)"
repo_root="$(CDPATH='' cd -- "$script_dir/.." && pwd -P)"
source_dir="$repo_root/skills/$skill_name"

if [[ "$action" == "list-targets" ]]; then
  list_targets
  exit 0
fi

[[ -f "$source_dir/SKILL.md" ]] || fail "找不到 Skill 源目录：$source_dir"

skill_version="unknown"
if [[ -f "$repo_root/VERSION" ]]; then
  skill_version="$(tr -d ' \t\r\n' <"$repo_root/VERSION")"
  [[ -n "$skill_version" ]] || skill_version="unknown"
fi

source_commit=""
if command -v git >/dev/null 2>&1; then
  source_commit="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || printf '')"
fi

skills_root="$(resolve_skills_root)"
target_path="$skills_root/$skill_name"
manifest_path="$skills_root/$manifest_name"

if [[ -n "$backup_dir" ]]; then
  backup_root="$(normalize_path "$(expand_user_path "$backup_dir")")"
else
  backup_root="$skills_root/$backup_dir_name"
fi

detect_sha256

# --- 校验 -------------------------------------------------------------------

run_verify() {
  if [[ ! -e "$target_path" && ! -L "$target_path" ]]; then
    fail "未检测到安装：$target_path"
  fi
  [[ -f "$manifest_path" ]] || fail "缺少安装清单 ${manifest_path}，无法校验；请重新运行安装以生成清单。"

  recorded_mode="$(manifest_scalar "$manifest_path" install_mode)"
  recorded_version="$(manifest_scalar "$manifest_path" version)"
  recorded_source="$(manifest_scalar "$manifest_path" source_dir)"

  log "清单版本：${recorded_version:-未记录}"
  log "安装方式：${recorded_mode:-未记录}"

  if [[ "$recorded_mode" == "link" ]]; then
    [[ -L "$target_path" ]] || fail "清单记录为链接安装，但 $target_path 不是符号链接。"
    actual_link="$(readlink "$target_path")"
    if [[ "$actual_link" != "$recorded_source" ]]; then
      fail "符号链接指向 ${actual_link}，与清单记录的 $recorded_source 不一致。"
    fi
    log "链接指向：$actual_link"
    log "校验通过：链接安装的内容随仓库变化，故跳过逐文件摘要比对。"
    return 0
  fi

  [[ -d "$target_path" ]] || fail "清单记录为复制安装，但 $target_path 不是目录。"

  missing=0
  modified=0
  checked=0
  while read -r rel expected; do
    [[ -n "$rel" ]] || continue
    checked=$((checked + 1))
    if [[ ! -f "$target_path/$rel" ]]; then
      printf '  [缺失] %s\n' "$rel" >&2
      missing=$((missing + 1))
      continue
    fi
    if [[ "$(hash_file "$target_path/$rel")" != "$expected" ]]; then
      printf '  [被修改] %s\n' "$rel" >&2
      modified=$((modified + 1))
    fi
  done <<EOF
$(manifest_digests "$manifest_path")
EOF

  ((checked > 0)) || fail "清单没有记录任何文件，内容不可信。"

  extra=0
  known_paths="$(manifest_paths_of "$manifest_path")"
  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    if ! printf '%s\n' "$known_paths" | grep -Fxq -- "$rel"; then
      printf '  [清单外文件] %s\n' "$rel" >&2
      extra=$((extra + 1))
    fi
  done <<EOF
$(list_payload_files "$target_path")
EOF

  if ((missing > 0 || modified > 0 || extra > 0)); then
    fail "校验失败：$checked 个受管文件中缺失 ${missing}、被修改 ${modified}，另有 $extra 个清单外文件。"
  fi

  log "校验通过：$checked 个文件的 sha256 与清单完全一致，且无清单外文件。"
}

# --- 卸载 -------------------------------------------------------------------

list_unmanaged_files() {
  known_paths="$(manifest_paths_of "$manifest_path")"
  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    if ! printf '%s\n' "$known_paths" | grep -Fxq -- "$rel"; then
      printf '  %s\n' "$rel"
    fi
  done <<EOF
$(list_payload_files "$target_path")
EOF
}

run_uninstall() {
  if [[ ! -e "$target_path" && ! -L "$target_path" && ! -f "$manifest_path" ]]; then
    log "未检测到安装，无需卸载：$target_path"
    return 0
  fi

  if [[ -L "$target_path" ]]; then
    log "将移除符号链接：$target_path"
  elif [[ -d "$target_path" ]]; then
    if [[ ! -f "$manifest_path" ]]; then
      ((force == 1)) || fail "缺少安装清单 ${manifest_path}，无法确认目录归属；确认要删除 $target_path 请添加 --force。"
      warn "缺少清单，按 --force 直接删除 ${target_path}。"
    else
      unmanaged="$(list_unmanaged_files)"
      if [[ -n "$unmanaged" ]]; then
        printf '以下文件不在安装清单中（可能是本地修改）：\n%s\n' "$unmanaged" >&2
        ((force == 1)) || fail "存在清单外文件，已停止；确认连同这些文件一起删除请添加 --force。"
        warn "按 --force 连同上述清单外文件一起删除。"
      fi
    fi
    log "将移除目录：$target_path"
  elif [[ -e "$target_path" ]]; then
    fail "$target_path 既不是目录也不是符号链接，出于安全考虑不做删除。"
  fi

  if [[ -f "$manifest_path" ]]; then
    log "将移除清单：$manifest_path"
  fi
  if [[ -d "$backup_root" ]]; then
    if ((purge == 1)); then
      log "将移除备份目录：$backup_root"
    else
      log "保留备份目录（加 --purge 可一并删除）：$backup_root"
    fi
  fi

  if ((dry_run == 1)); then
    log "--dry-run：以上操作均未执行。"
    return 0
  fi

  if [[ -L "$target_path" ]]; then
    rm -f -- "$target_path"
  elif [[ -d "$target_path" ]]; then
    rm -rf -- "$target_path"
  fi
  if [[ -f "$manifest_path" ]]; then
    rm -f -- "$manifest_path"
  fi
  if ((purge == 1)) && [[ -d "$backup_root" ]]; then
    rm -rf -- "$backup_root"
  fi

  log "卸载完成：$target_path"
}

# --- 安装 -------------------------------------------------------------------

stage_path=""
backup_path=""
source_digests=""

# 异常退出时只清理本次创建的临时目录，并在需要时恢复原版本。
on_exit() {
  status=$?
  trap - EXIT

  if [[ -n "$stage_path" && -d "$stage_path" ]]; then
    rm -rf -- "$stage_path"
  fi

  if ((status != 0)) && [[ -n "$backup_path" && ! -e "$target_path" && -e "$backup_path" ]]; then
    mv -- "$backup_path" "$target_path"
    printf '安装失败，已恢复原版本：%s\n' "$target_path" >&2
  fi

  exit "$status"
}

# 已安装内容与源目录逐字节一致时返回 0，让重复的 --force 安装成为幂等空操作。
target_matches_source() {
  [[ -d "$target_path" && ! -L "$target_path" ]] || return 1
  [[ -f "$manifest_path" ]] || return 1
  [[ "$(manifest_scalar "$manifest_path" install_mode)" == "copy" ]] || return 1
  [[ "$(manifest_scalar "$manifest_path" version)" == "$skill_version" ]] || return 1

  installed_digests="$(build_digest_list "$target_path" 2>/dev/null || true)"
  [[ -n "$installed_digests" && "$installed_digests" == "$source_digests" ]]
}

run_install() {
  source_digests="$(build_digest_list "$source_dir")"
  source_count="$(printf '%s\n' "$source_digests" | grep -c . || true)"
  ((source_count > 0)) || fail "源目录没有可安装的文件：$source_dir"

  target_exists=0
  if [[ -e "$target_path" || -L "$target_path" ]]; then
    target_exists=1
  fi

  if ((target_exists == 1)) && ((force == 0)); then
    fail "目标已存在：${target_path}。未做任何覆盖；确认更新时请显式添加 --force（会先备份），或用 --verify 检查当前副本。"
  fi

  if ((target_exists == 1)) && ((link_mode == 0)) && target_matches_source; then
    log "已安装版本 ${skill_version}，且 $source_count 个文件的 sha256 全部一致，无需变更：$target_path"
    return 0
  fi

  if ((link_mode == 1)); then
    log "计划：在 $target_path 创建指向 $source_dir 的符号链接（开发模式）"
  else
    log "计划：把 $source_count 个文件（版本 ${skill_version}）安装到 $target_path"
  fi
  if ((target_exists == 1)); then
    log "计划：先把现有副本备份到 $backup_root"
  fi
  log "计划：写出安装清单 $manifest_path"

  if ((dry_run == 1)); then
    log "--dry-run：以上操作均未执行，磁盘未被写入。"
    return 0
  fi

  mkdir -p -- "$skills_root"
  trap on_exit EXIT

  if ((link_mode == 0)); then
    stage_path="$(mktemp -d "$skills_root/.$skill_name.install.XXXXXX")"
    log "正在验证并暂存 Skill：$source_dir"
    cp -R -- "$source_dir"/. "$stage_path"/
    [[ -f "$stage_path/SKILL.md" ]] || fail "暂存副本缺少 SKILL.md，安装已停止。"
    staged_digests="$(build_digest_list "$stage_path")"
    [[ "$staged_digests" == "$source_digests" ]] || fail "暂存副本与源目录的摘要不一致，安装已停止。"
  fi

  if ((target_exists == 1)); then
    mkdir -p -- "$backup_root"
    backup_path="$backup_root/$(date '+%Y%m%d-%H%M%S')-$$"
    mv -- "$target_path" "$backup_path"
    log "旧版本已备份到：$backup_path"
  fi

  if ((link_mode == 1)); then
    ln -s -- "$source_dir" "$target_path"
    write_manifest "$manifest_path" "link" "$source_digests" "$source_count"
  else
    mv -- "$stage_path" "$target_path"
    stage_path=""
    write_manifest "$manifest_path" "copy" "$source_digests" "$source_count"
  fi

  trap - EXIT

  log "安装完成：$target_path"
  log "安装清单：${manifest_path}（可用 --verify 复核，--uninstall 卸载）"
  log "请重启或刷新 Agent 的 Skills 列表后使用 ${skill_name}。"
}

case "$action" in
  install) run_install ;;
  verify) run_verify ;;
  uninstall) run_uninstall ;;
  *) fail "内部错误：未处理的操作 $action" ;;
esac
