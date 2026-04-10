# chat_client.py
import socket
import threading
import sys
import getpass  # 비밀번호 입력을 가려주는 기본 모듈

def receive(sock):
    while True:
        try:
            msg = sock.recv(1024).decode('utf-8')
            if not msg: break
            if msg == "quit": sock.close()
            # 상대방 메시지 출력 후 다시 내 입력 프롬프트 띄우기
            print(f"{msg}")
            print("\033[92m[나]\033[0m: ", end="", flush=True)
        except:
            print("\n[알림] 서버와 연결이 끊어졌습니다.")
            break

# GCP 인스턴스의 '외부 IP 주소' 입력
SERVER_IP = '34.10.148.139'
PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.connect((SERVER_IP, PORT))
except Exception as e:
    print(f"[오류] 서버에 연결할 수 없습니다: {e}")
    sys.exit()

# 로그인 인증 단계
# 서버가 보내는 "ID: " 프롬프트 수신
id_prompt = sock.recv(1024).decode('utf-8')
username = input(id_prompt)
sock.send(username.encode('utf-8'))

# 서버가 보내는 "PW: " 프롬프트 수신
pw_prompt = sock.recv(1024).decode('utf-8')
# getpass를 사용하면 키보드를 쳐도 화면에 글자가 안보임(리눅스 터미널 방식)
password = getpass.getpass(pw_prompt)
sock.send(password.encode('utf-8'))

# 인증 결과 수신
auth_result = sock.recv(1024).decode('utf-8')

if "이미 접속 중인 아이디입니다!" in auth_result:
    answer = input(auth_result)
    sock.send(answer.encode('utf-8'))

    # 서버의 최종 처리 결과 대기
    auth_result = sock.recv(1024).decode('utf-8')

print(auth_result)

# 채팅 단계
# 인증 성공 메시지를 받았을 때만 채팅 스레드 시작
if "인증 성공" in auth_result or "성공적으로 종료" in auth_result:
    threading.Thread(target=receive, args=(sock,), daemon=True).start()

    while True:
        msg = input("\033[92m[나]\033[0m: ")
        if msg.lower() == 'quit': break

        try:
            sock.send(msg.encode('utf-8'))
        except OSError:
            print("\n통신이 종료되어 메시지를 전송할 수 없습니다. 프로그램을 종료합니다.")
            break

sock.close()