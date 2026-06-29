#!/bin/bash
export PATH="/opt/homebrew/bin:$PATH"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
nvm use 18 2>/dev/null || true
ROOT="$(cd "$(dirname "$0")" && pwd)"

# 检查前端依赖
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "安装前端依赖..."
  cd "$ROOT/frontend" && npm install
fi

# 启动后端
cd "$ROOT/backend"
python3 app.py &
BACKEND_PID=$!
echo "后端已启动 PID=$BACKEND_PID (port 5001)"

# 启动前端
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "前端已启动 PID=$FRONTEND_PID (port 5173)"

echo "按 Ctrl+C 停止全部服务"
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
