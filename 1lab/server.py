import os
import socket
import threading
import subprocess
import json
import time
import shutil
import logging
import signal
import sys
from datetime import datetime

DATA_FILE = 'programs_data.json'
OUTPUT_DIR = 'programs_output'
INTERVAL = 10
program_threads = {}

logging.basicConfig(
    level=logging.INFO,
    filename='server_client.log',
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'
)

def is_program_safe(program):
    cmd = program.split()[0]
    return shutil.which(cmd) is not None

def load_programs():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"interval": INTERVAL, "programs": {}}

def save_programs(programs_data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(programs_data, f)

def run_program(program_name, stop_event, interval):
    folder = os.path.join(OUTPUT_DIR, program_name)
    os.makedirs(folder, exist_ok=True)
    while not stop_event.is_set():
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = os.path.join(folder, f'run_{timestamp}.txt')

        result = subprocess.run(program_name, capture_output=True, shell=True)
        stdout = result.stdout.decode('cp866', errors='ignore')
        stderr = result.stderr.decode('cp866', errors='ignore')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(stdout)
            f.write(stderr)

        for _ in range(interval):
            if stop_event.is_set():
                break
            time.sleep(1)

def start_programs(programs_data):
    for prog, info in programs_data['programs'].items():
        if info['active']:
            stop_event = threading.Event()
            thread = threading.Thread(target=run_program, args=(prog, stop_event, programs_data['interval']), daemon=True)
            program_threads[prog] = {'thread': thread, 'event': stop_event}
            thread.start()

def handle_client(conn, addr, programs_data):
    try:
        data = conn.recv(4096).decode('utf-8')
        request = json.loads(data)
        action = request.get('action')
        program = request.get('program')

        response = "Неизвестная команда."

        if action == 'add':
            if not is_program_safe(program):
                response = f"Ошибка: Программа '{program}' не найдена или недоступна."
                logging.warning(response)
            elif program not in programs_data['programs']:
                programs_data['programs'][program] = {'active': True}
                save_programs(programs_data)
                stop_event = threading.Event()
                thread = threading.Thread(target=run_program, args=(program, stop_event, programs_data['interval']), daemon=True)
                program_threads[program] = {'thread': thread, 'event': stop_event}
                thread.start()
                response = f"Программа {program} добавлена и запущена."
                logging.info(response)
            else:
                response = f"Программа {program} уже существует."
                logging.info(response)

        elif action == 'stop':
            if program in program_threads:
                program_threads[program]['event'].set()
                programs_data['programs'][program]['active'] = False
                save_programs(programs_data)
                response = f"Программа {program} остановлена."
                logging.info(response)
            else:
                response = f"Программа {program} не найдена."
                logging.warning(response)

        elif action == 'resume':
            if program in programs_data['programs'] and not programs_data['programs'][program]['active']:
                stop_event = threading.Event()
                thread = threading.Thread(target=run_program, args=(program, stop_event, programs_data['interval']), daemon=True)
                program_threads[program] = {'thread': thread, 'event': stop_event}
                thread.start()
                programs_data['programs'][program]['active'] = True
                save_programs(programs_data)
                response = f"Программа {program} возобновлена."
                logging.info(response)
            else:
                response = f"Программа {program} уже выполняется или не найдена."
                logging.warning(response)

        elif action == 'set_interval':
            try:
                new_interval = int(request.get('interval', INTERVAL))
                programs_data['interval'] = new_interval
                save_programs(programs_data)
                response = f"Интервал установлен на {new_interval} секунд."
                logging.info(response)
            except ValueError:
                response = "Ошибка: Неверно указан интервал."
                logging.error(response)

        elif action == 'get_output':
            folder = os.path.join(OUTPUT_DIR, program)
            if os.path.exists(folder):
                outputs = sorted(os.listdir(folder))
                combined_output = ''
                for file in outputs:
                    with open(os.path.join(folder, file), 'r', encoding='utf-8') as f:
                        combined_output += f"\n==== {file} ====\n{f.read()}\n"
                response = combined_output
                logging.info(f"Выведены результаты для {program}")
            else:
                response = f"Вывод для {program} не найден."
                logging.warning(response)

        conn.sendall(response.encode('utf-8'))

    except Exception as e:
        conn.sendall(f"Ошибка сервера: {e}".encode('utf-8'))
        logging.error(f"Ошибка: {e}")
    finally:
        conn.close()

def graceful_shutdown(signum, frame):
    logging.info("Получен сигнал завершения. Останавливаем программы и сохраняем состояние.")
    for prog, thread_info in program_threads.items():
        thread_info['event'].set()
        logging.info(f"Остановлена программа: {prog}")
    save_programs(programs_data)
    sys.exit(0)

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    programs_data = load_programs()
    start_programs(programs_data)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(('localhost', 5555))
        server.listen()
        logging.info("Сервер запущен на localhost:5555")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr, programs_data)).start()
