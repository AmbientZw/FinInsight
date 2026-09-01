#!/usr/bin/env bash
# =============================================================================
# FinInsight 演示录屏脚本（macOS）
#
# 用 macOS 自带的 screencapture 录制演示视频，无需第三方依赖；
# 若装了 ffmpeg，可一键转 mp4 / gif（适合放 README 或提交）。
#
# 用法：
#   ./capture.sh                     # 默认：全屏录 120 秒，输出 demo_<时间戳>.mov
#   ./capture.sh -d 90               # 录 90 秒
#   ./capture.sh -c 10               # 开始前倒计时 10 秒（默认 3）
#   ./capture.sh -o demo.mov         # 指定输出文件
#   ./capture.sh -r "0,0,1280,720"   # 只录屏幕左上角 1280x720 区域
#   ./capture.sh -a                  # 同时录麦克风（口播配音）
#   ./capture.sh --no-clicks         # 不显示鼠标点击
#   ./capture.sh -m                  # 录完自动转 mp4（需 ffmpeg）
#   ./capture.sh --gif               # 录完自动转 gif（需 ffmpeg）
#
# 首次使用：macOS 会弹「屏幕录制」权限申请，请在 系统设置 → 隐私与安全性
# → 屏幕录制 中勾选你的终端，然后重跑本脚本。
# =============================================================================
set -euo pipefail

# ---------- 默认值 ----------
DURATION=120
COUNTDOWN=3
OUTPUT=""
REGION=""            # 空=全屏；否则为 "x,y,w,h"
WITH_AUDIO=0
SHOW_CLICKS=1
CONVERT_MP4=0
CONVERT_GIF=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR"

usage() {
  sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# ---------- 参数解析 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d) DURATION="$2"; shift 2 ;;
    -c) COUNTDOWN="$2"; shift 2 ;;
    -o) OUTPUT="$2"; shift 2 ;;
    -r) REGION="$2"; shift 2 ;;
    -a) WITH_AUDIO=1; shift ;;
    --no-clicks) SHOW_CLICKS=0; shift ;;
    -m) CONVERT_MP4=1; shift ;;
    --gif) CONVERT_GIF=1; shift ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1"; usage ;;
  esac
done

# ---------- 前置检查 ----------
command -v screencapture >/dev/null 2>&1 || {
  echo "❌ 需要 macOS 自带的 screencapture（本脚本仅支持 macOS）"; exit 1;
}

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="$OUTPUT_DIR/demo_$(date +%Y%m%d_%H%M%S).mov"
fi

# 服务检查（仅提醒，不阻断）
echo "── 前置检查 ──────────────────────────────"
if curl -sf -o /dev/null --max-time 3 http://localhost:5173 2>/dev/null; then
  echo "✅ 前端 http://localhost:5173 已运行"
else
  echo "⚠️  前端未运行，请先启动：cd frontend && npm run dev"
fi
if curl -sf -o /dev/null --max-time 3 http://localhost:8000/api/health 2>/dev/null; then
  echo "✅ 后端 http://localhost:8000 已运行"
else
  echo "⚠️  后端未运行，请先启动：cd backend && uvicorn app.main:app --reload"
fi

echo ""
echo "📹 录制参数："
echo "   时长    : ${DURATION} 秒"
echo "   区域    : ${REGION:-全屏}"
echo "   音频    : $([ "$WITH_AUDIO" = 1 ] && echo 麦克风 || echo 无)"
echo "   点击指示: $([ "$SHOW_CLICKS" = 1 ] && echo 显示 || echo 隐藏)"
echo "   输出    : $OUTPUT"

# ---------- 倒计时 ----------
echo ""
echo "倒计时 ${COUNTDOWN} 秒后开始录制，请切到浏览器窗口准备好演示流程……"
for ((i = COUNTDOWN; i >= 1; i--)); do echo "  $i ..."; sleep 1; done

# ---------- 录制 ----------
echo "🔴 录制中（${DURATION} 秒）……"

ARGS=(-v -V "$DURATION" -x)
[[ "$WITH_AUDIO" = 1 ]] && ARGS+=(-g)
[[ "$SHOW_CLICKS" = 1 ]] && ARGS+=(-k)
[[ -n "$REGION" ]] && ARGS+=(-R "$REGION")
ARGS+=("$OUTPUT")

screencapture "${ARGS[@]}"
echo "✅ 已保存: $OUTPUT"

# ---------- 转码（可选，需 ffmpeg） ----------
if [[ "$CONVERT_MP4" = 1 || "$CONVERT_GIF" = 1 ]]; then
  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "❌ 未安装 ffmpeg，无法转码。安装：brew install ffmpeg"
    exit 1
  fi
fi

if [[ "$CONVERT_MP4" = 1 ]]; then
  MP4="${OUTPUT%.mov}.mp4"
  echo "🎬 转 mp4 → $MP4"
  ffmpeg -y -loglevel error -i "$OUTPUT" -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$MP4"
  echo "✅ 已生成: $MP4"
fi

if [[ "$CONVERT_GIF" = 1 ]]; then
  GIF="${OUTPUT%.mov}.gif"
  echo "🖼️  转 gif → $GIF"
  ffmpeg -y -loglevel error -i "$OUTPUT" -vf "fps=15,scale=1280:-1:flags=lanczos" -loop 0 "$GIF"
  echo "✅ 已生成: $GIF"
fi

echo ""
echo "完成。录屏流程可参考 docs/demo/demo_script.md 的分镜脚本。"
