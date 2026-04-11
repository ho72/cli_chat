# chat_server.py
import socket
import threading
from database import Database

# DB 인스턴스 생성
db = Database()
clients = {} # {socket 객체: "유저ID"} 형태로 관리

def broadcast(msg, exclude_sock=None):
    """모든 클라이언트에게 메시지를 전송하는 함수"""
    for client_sock in list(clients.keys()):
        if client_sock != exclude_sock:
            try:
                client_sock.send(msg.encode('utf-8'))
            except:
                pass

def send_chat_history(client_socket, room_id):
    """DB에서 이전 채팅 기록을 불러와 클라이언트에게 전송"""
    history = db.get_recent_messages(room_id, limit=20)
    if history:
        client_socket.send("\n--- 지난 대화 내역 ---\n".encode('utf-8'))
        for sender, content, time in history:
            client_socket.send(f"[{time}] {sender}: {content}\n".encode('utf-8'))
        client_socket.send("-------------------------------\n\n".encode('utf-8'))

def handle_client(client_socket, addr):
    print(f"[연결 시도] {addr} 에서 접속을 시도합니다.")

    client_ip = addr[0]

    # 임시로 모든 유저를 1번 방에 배정
    current_room_id = 1

    try:
        # 로그인 인증 단계
        # 클라이언트에게 ID 요청
        client_socket.send("ID: ".encode('utf-8'))
        username = client_socket.recv(1024).decode('utf-8').strip()

        # 클라이언트에게 비밀번호 요청
        client_socket.send("PW: ".encode('utf-8'))
        password = client_socket.recv(1024).decode('utf-8').strip()

        # DB를 통해 인증 확인
        if db.authenticate_user(username, password):

            # 중복 접속 체크
            if username in clients.values():
                #client_socket.send("이미 접속 중인 아이디입니다! 연결을 종료합니다.\n".encode('utf-8'))
                #client_socket.close()
                # return
                client_socket.send("이미 접속 중인 아이디입니다! 다른 세션을 종료하고 접속하시겠습니까? (y/n): ".encode('utf-8'))
                answer = client_socket.recv(1024).decode('utf-8').strip().lower()

                if answer == 'y':
                    target_sock = None
                    for sock, user_id in list(clients.items()):
                        if user_id == username:
                            target_sock = sock
                            break

                    if target_sock:
                        try:
                            target_sock.send("quit".encode('utf-8'))
                            target_sock.close()
                        except:
                            pass
                        # 딕셔너리에서 안전하게 삭제
                        clients.pop(target_sock, None)
                    
                    # 새로 들어온 사람에게 성공 메시지 전송
                    client_socket.send(f"\n {username}님의 기존 연결을 성공적으로 종료했습니다.\n".encode('utf-8'))
                else:
                    client_socket.send("연결을 종료합니다.".encode('utf-8'))
                    return
                

            client_socket.send("인증 성공! 채팅을 시작합니다.\n".encode('utf-8'))
            clients[client_socket] = username

            # 입장 시 과거 채팅 기록 전송
            send_chat_history(client_socket, current_room_id)

            broadcast(f"\n[알림] {username}님이 입장하셨습니다.", client_socket)

        else:
            client_socket.send("인증 실패! 연결 종료\n".encode('utf-8'))
            client_socket.close()
            return

        # 채팅 메시지 송수신 단계
        while True:
            msg = client_socket.recv(1024).decode('utf-8')
            if not msg: break

            # DB에 메시지 기록
            db.save_message(current_room_id, username, client_ip, msg)

            # 다른 사람들에게 브로드캐스트
            formatted_msg = f"\r\033[96m[{username}]\033[0m: {msg}"
            broadcast(formatted_msg, client_socket)

    except Exception as e:
        print(f"Exception - {e}")
        pass

    finally:
        # 클라이언트가 종료했거나 오류로 끊긴 경우
        if client_socket in clients:
            username = clients.pop(client_socket)
            broadcast(f"\n[알림] {username}님이 퇴장하셨습니다.", None)
        client_socket.close()
        print(f"[끊김] {addr} 연결 종료.")

# 메인 서버 실행 로직
if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 5000)) # GCP에서 연 방화벽 포트
    server.listen(2)
    print("[서버 시작] 클라이언트 기다리는 중...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()