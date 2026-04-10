#!/bin/bash

# 실행 중인 서버가 있다면 중복 실행 방지
if pgrep -f "python3 chat_server.py" > /dev/null
then
    echo "이미 채팅 서버 실행 중"
else
    echo "채팅 서버 시작"

    # $1은 스크립트 실행 시 입력한 첫 번째 옵션을 의미함.
    if [ "$1" == "--log" ] || [ "$1" == "-l" ]; then
        # 옵션이 있으면 로그를 server.log에 저장
        nohup python3 chat_server.py > server.log 2>&1 &
        echo "서버 시작 완료! [로그 기록 켬] (로그: tail -f server.log)"
    else
        # 옵션이 없거나 다르면 로그를 /dev/null에 버림 (기본값)
        nohup python3 chat_server.py > /dev/null 2>&1 &
        echo "서버 시작 완료! [로그 기록 끔] (로그를 보려면 --log 옵션을 주세요)"
    fi
fi