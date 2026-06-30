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
python3 app.py > "$ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "后端已启动 PID=$BACKEND_PID (port 5002)，日志: $ROOT/backend.log"

# 启动前端
cd "$ROOT/frontend"
npm run dev > "$ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "前端已启动 PID=$FRONTEND_PID (port 5273)，日志: $ROOT/frontend.log"

echo "后端 PID=$BACKEND_PID，前端 PID=$FRONTEND_PID"
echo "$BACKEND_PID $FRONTEND_PID" > "$ROOT/pids"
echo "日志: $ROOT/backend.log / frontend.log"
echo "停止服务: kill \$(cat $ROOT/pids)"
