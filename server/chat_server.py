# chat_server.py
import socket
import threading
import json
# import bcrypt
import time
from database import Database

# DB 인스턴스 생성
db = Database()
clients = {} # {socket 객체: "유저ID"} 형태로 관리

def socket_send(csock, target, value):
    """메시지 전송하는 부분"""
    json_data = json.dumps({"target": target, "value": value})
    csock.send(json_data.encode('utf-8'))

def socket_recv(csock):
    recv_raw = csock.recv(4096).decode('utf-8')
    recv_dict = json.loads(recv_raw)
    return recv_dict

def login(csock):
    """로그인 DB 검증 및 결과 반환 (아이디 리턴하면 성공, 0 리턴하면 실패, 1 리턴하면 이미 접속 중)"""
    try:
        recv = socket_recv(csock)
        id = recv['value']['id'].strip()
        password = recv['value']['password'].strip()

        if db.authenticate_user(id, password):

            # 중복 접속 체크
            if id in clients.values():
                socket_send(csock, "REQUEST", "login_conflict")
                answer = socket_recv(csock)

                if answer['value'] == 'y':
                    target_sock = None
                    for con_sock, con_id in list(clients.items()):
                        if con_id == id:
                            target_sock = con_sock
                            break

                    if target_sock:
                        try:
                            socket_send(target_sock, "SYSTEM", "duplicate_login")
                            target_sock.close()
                        except:
                            pass
                        # 딕셔너리 안전하게 삭제
                        clients.pop(target_sock, None)

                else:
                    socket_send(csock, "SYSTEM", "disconnect")
                    return 0

            socket_send(csock, "SYSTEM", "login_success")
            clients[csock] = id
            
            return id
        else:
            socket_send(csock, "SYSTEM", "login_fail")
            return 0

    except Exception as e:
        print(f"Exception - {e}")
        return 0

def broadcast(msg, room_id, exclude_sock=None):
    """모든 클라이언트에게 메시지를 전송하는 함수"""
    member_ids = {row[0] for row in db.get_room_members(room_id)}
    for client_sock in list(clients.keys()):
        if client_sock == exclude_sock:
            continue
        if clients[client_sock] in member_ids:
            try:
                payload = msg if isinstance(msg, str) else json.dumps(msg)
                client_sock.send(payload.encode('utf-8'))
            except:
                pass

def handle_room_selection(csock, user_id):
    """방 선택"""
    room_list = db.get_user_rooms(user_id)
    processed_rooms = [
        {'room_id': r[0], 'room_name': r[1]}
        for r in room_list
    ]
    socket_send(csock, "room_list", processed_rooms)
    return socket_recv(csock)['value']

def handle_chat_room(csock, user_ip, user_id, room_id):
    """채팅"""
    try:
        while True:
            msg = socket_recv(csock)
            if not msg['value']: break
            if msg['value'] == "back": return
            if msg['target'] != f"room_{room_id}": break

            # DB에 메시지 기록
            db.save_message(room_id, user_id, user_ip, msg['value'])

            # 다른 사람들에게 브로드캐스트
            json_msg = {
                'target': f"room_{room_id}",
                'value': {
                    "user": user_id,
                    "time": time.time(),
                    "msg": msg['value']
                }
            }
            broadcast(json_msg, room_id)
    except Exception as e:
        print(f"Exception - {e}")
        pass

def send_chat_history(client_socket, room_id):
    """DB에서 이전 채팅 기록을 불러와 클라이언트에게 전송"""
    history = db.get_recent_messages(room_id, limit=20)
    if history:
        client_socket.send("\n--- 지난 대화 내역 ---\n".encode('utf-8'))
        for sender, content, timestamp in history:
            client_socket.send(f"[{timestamp}] {sender}: {content}\n".encode('utf-8'))
        client_socket.send("-------------------------------\n\n".encode('utf-8'))

def handle_client(client_socket, addr):
    print(f"[연결 시도] {addr} 에서 접속을 시도합니다.")

    client_ip = addr[0]
    client_request = None

    try:
        # DB를 통해 인증 확인
        user_id = login(client_socket)

        if user_id == 0:
            # 로그인 실패 실제 소켓 닫기
            print(f"{addr} - 로그인 실패: 연결을 종료합니다.")
            client_socket.close()
            return
            
        # 로그인 성공
        print(f"{addr} - {user_id} 로그인 성공")
        client_request = socket_recv(client_socket)['value']
        print(f"-----{client_request}")
        
        while True:
            """방 선택 -> 채팅방"""
            if client_request == "room_select":
                client_request = handle_room_selection(client_socket, user_id)
            elif client_request == None:
                break
            else:
                # send_chat_history()
                broadcast(
                    {'target': "CHAT_SYSTEM", 'value': f"{user_id}님이 입장했습니다."},
                    client_request,
                    exclude_sock=client_socket
                )
                handle_chat_room(client_socket, client_ip, user_id, client_request)
                client_request = "room_select"

    except Exception as e:
        print(f"Exception - {e}")
        pass

    finally:
        # 클라이언트가 종료했거나 오류로 끊긴 경우
        if client_socket in clients:
            username = clients.pop(client_socket)
            # broadcast(f"\n[알림] {username}님이 퇴장하셨습니다.", None)
            if client_request and client_request != "room_select":
                broadcast(
                    {'target': "CHAT_SYSTEM", 'value': f"{username}님이 퇴장하셨습니다."},
                    client_request
                )
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