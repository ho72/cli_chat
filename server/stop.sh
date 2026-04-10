#!/bin/bash

echo "채팅 서버 종료 시도 중..."

# 실행 중인 프로세스가 있는지 확인
if pgrep -f "python3 chat_server.py" > /dev/null
then
    # 켜져 있다면 종료
    pkill -f "python3 chat_server.py"
    echo "서버가 정상적으로 종료되었습니다."
else
    # 켜져 있지 않다면 알림
    echo "현재 실행 중인 채팅 서버가 없습니다."
fi