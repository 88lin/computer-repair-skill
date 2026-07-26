#!/usr/bin/env bash
set -euo pipefail

skill_name="noah-computer-care"
target="codex"
destination=""
force=0

# 输出命令帮助，说明目标目录是 Skills 根目录而不是最终 Skill 目录。
usage() {
  cat <<'EOF'
用法: ./scripts/install.sh [选项]

选项:
  --target <codex|claude|agents|custom>  Agent 预设，默认 codex
  --destination <path>                  覆盖预设的 Skills 根目录
  --force                               备份现有版本后更新
  -h, --help                            显示帮助
EOF
}

# 统一输出错误并返回非零状态。
fail() {
  printf '错误：%s\n' "$1" >&2
  exit 1
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
    --force)
      force=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "未知参数：$1"
      ;;
  esac
done

case "$target" in
  codex|claude|agents|custom) ;;
  *) fail "不支持的 target：$target" ;;
esac

# 展开常见的用户目录写法，避免在引号中把波浪号当成普通字符。
expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${1#~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

# 选择各 Agent 的默认 Skills 根目录，也允许显式目录覆盖预设。
resolve_skills_root() {
  if [[ -n "$destination" ]]; then
    expand_user_path "$destination"
    return
  fi

  case "$target" in
    codex) printf '%s/skills\n' "${CODEX_HOME:-$HOME/.codex}" ;;
    claude) printf '%s/skills\n' "${CLAUDE_HOME:-$HOME/.claude}" ;;
    agents) printf '%s/.agents/skills\n' "$HOME" ;;
    custom) fail "target 为 custom 时必须提供 --destination。" ;;
  esac
}

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
source_dir="$(CDPATH= cd -- "$script_dir/../skills/$skill_name" && pwd -P)"
[[ -f "$source_dir/SKILL.md" ]] || fail "找不到 Skill 源目录：$source_dir"

requested_root="$(resolve_skills_root)"
requested_root="$(expand_user_path "$requested_root")"
mkdir -p -- "$requested_root"
skills_root="$(CDPATH= cd -- "$requested_root" && pwd -P)"
target_path="$skills_root/$skill_name"

if [[ -e "$target_path" || -L "$target_path" ]]; then
  ((force == 1)) || fail "目标已存在：$target_path。未做任何覆盖；确认更新时请显式添加 --force。"
fi

stage_path="$(mktemp -d "$skills_root/.$skill_name.install.XXXXXX")"
backup_path=""
install_complete=0

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
trap on_exit EXIT

printf '正在验证并暂存 Skill：%s\n' "$source_dir"
cp -R -- "$source_dir"/. "$stage_path"/
[[ -f "$stage_path/SKILL.md" ]] || fail "暂存副本缺少 SKILL.md，安装已停止。"

if [[ -e "$target_path" || -L "$target_path" ]]; then
  backup_root="$(dirname -- "$skills_root")/external/$skill_name/backups"
  mkdir -p -- "$backup_root"
  backup_path="$backup_root/$(date '+%Y%m%d-%H%M%S')-$$"
  mv -- "$target_path" "$backup_path"
  printf '旧版本已备份到：%s\n' "$backup_path"
fi

mv -- "$stage_path" "$target_path"
stage_path=""
install_complete=1
trap - EXIT

printf '安装完成：%s\n' "$target_path"
printf '请重启或刷新 Agent 的 Skills 列表后使用 %s。\n' "$skill_name"
