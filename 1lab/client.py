import socket
import json

def send_request(request, host='localhost', port=5555):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(json.dumps(request).encode('utf-8'))

        response = b''
        while True:
            data = sock.recv(65536)
            if not data:
                break
            response += data

        print(response.decode('utf-8'))

if __name__ == "__main__":
    while True:
        print("\n1. Добавить программу")
        print("2. Получить вывод программы")
        print("3. Остановить программу")
        print("4. Возобновить программу")
        print("5. Установить интервал запуска программ")
        print("6. Выход")

        choice = input("Выберите действие (1-6): ")

        if choice == '1':
            program = input("Введите название программы: ")
            send_request({'action': 'add', 'program': program})

        elif choice == '2':
            program = input("Введите название программы: ")
            send_request({'action': 'get_output', 'program': program})

        elif choice == '3':
            program = input("Введите название программы для остановки: ")
            send_request({'action': 'stop', 'program': program})

        elif choice == '4':
            program = input("Введите название программы для возобновления: ")
            send_request({'action': 'resume', 'program': program})

        elif choice == '5':
            interval = input("Введите новый интервал запуска программ (в секундах): ")
            send_request({'action': 'set_interval', 'interval': interval})

        elif choice == '6':
            print("Выход из программы.")
            break

        else:
            print("Некорректный выбор.")
