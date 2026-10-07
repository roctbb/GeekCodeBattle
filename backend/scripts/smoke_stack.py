"""Run only against a disposable Compose stack with a local checker stub.

GCB_SMOKE_JWT_SECRET must match that stack. No real GeekClass/GeekPaste calls.
Requires requests, pyjwt, python-socketio and websocket-client.
"""
import argparse
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import requests
import socketio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://localhost:18090')
    parser.add_argument('--checker-port', type=int, default=18084)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    secret = os.environ['GCB_SMOKE_JWT_SECRET']
    sockets = []
    prefix = uuid.uuid4().hex[:8]

    class Checker(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'queued', 'job_id': payload['callback_id']}).encode())

        def log_message(self, *args):
            pass

    checker = ThreadingHTTPServer(('127.0.0.1', args.checker_port), Checker)
    threading.Thread(target=checker.serve_forever, daemon=True).start()

    def call(session, method, path, body=None, status=200):
        response = session.request(method, base + '/api/v1' + path, json=body, timeout=20)
        assert response.status_code == status, (path, response.status_code, response.text[:500])
        return response.json()

    def login(name, role):
        client = requests.Session()
        token = jwt.encode({'id': f'{prefix}-{name}', 'name': name, 'role': role, 'iat': int(time.time())}, secret, algorithm='HS256')
        response = client.post(base + '/api/v1/auth/login/geekclass', headers={'Authorization': 'Bearer ' + token}, timeout=10)
        assert response.status_code == 200, response.text
        return client, response.json()

    try:
        teacher, _ = login('Учитель', 'teacher')
        a, ua = login('Маша', 'student')
        b, ub = login('Саша', 'student')
        outsider, _ = login('Наблюдатель', 'student')
        assert call(teacher, 'GET', '/health')['status'] == 'ok'
        task = call(teacher, 'POST', '/tasks', {
            'title': 'Сумма двух чисел', 'statement_md': '## Условие\nПрочитайте два целых числа **a** и **b** и выведите их сумму.\n\n### Формат ввода\nДва числа через пробел.\n\n### Формат вывода\nСумма чисел.',
            'difficulty': 'easy', 'check_type': 'tests',
            'config': {'tests': [{'input': '1 2', 'expected': '3'}]},
        }, 201)
        battle = call(teacher, 'POST', '/battles', {'title': 'Осенний код-баттл'}, 201)['id']
        call(teacher, 'POST', f'/battles/{battle}/tasks/{task["id"]}')
        invite = prefix.upper()
        call(teacher, 'PUT', f'/battles/{battle}/invite', {'code': invite})
        call(teacher, 'POST', f'/battles/{battle}/open-lobby')
        call(teacher, 'POST', f'/battles/{battle}/start')

        found = threading.Event()
        received = []
        sock = socketio.Client(http_session=a)
        sockets.append(sock)
        sock.on('match_found', lambda payload: (received.append(payload), found.set()))
        sock.connect(base, transports=['websocket'])
        for client in (a, b):
            call(client, 'POST', '/battles/join', {'code': invite})
        assert sock.call('subscribe', {'battle_id': battle})['status'] == 'subscribed'
        for client in (a, b):
            result = call(client, 'POST', f'/battles/{battle}/queue/ready')
            assert not result['created_rooms'], 'Expected delayed matchmaking in Celery'
        assert found.wait(15), 'Celery match_found did not reach the web Socket.IO client'
        room = received[-1]
        sock.call('subscribe', {'battle_id': battle, 'room_id': room['room_id'], 'match_id': room['match_id']})
        call(outsider, 'GET', f'/rooms/{room["room_id"]}', status=403)
        call(outsider, 'GET', '/tasks', status=403)
        other_socket = socketio.Client(http_session=outsider)
        sockets.append(other_socket)
        other_socket.connect(base, transports=['websocket'])
        assert other_socket.call('subscribe', {'match_id': room['match_id']})['error'] == 'Forbidden'
        verdicts = []
        arrived = threading.Event()
        sock.on('submission_verdict', lambda payload: (verdicts.append(payload), arrived.set()))
        submission = call(a, 'POST', f'/rooms/{room["room_id"]}/submit', {'language': 'python', 'source_code': 'print(3)'}, 202)
        token = jwt.encode({'service': 'geekpaste', 'iat': int(time.time())}, secret, algorithm='HS256')
        callback = {'callback_id': submission['submission_id'], 'job_id': submission['submission_id'], 'status': 'success', 'points': 1, 'max_points': 1}
        for _ in range(2):
            response = requests.post(base + '/api/v1/integrations/geekpaste/callback', json=callback, headers={'Authorization': 'Bearer ' + token}, timeout=10)
            assert response.status_code == 200, response.text
        assert arrived.wait(10)
        assert len(verdicts) == 1, verdicts
        call(b, 'POST', f'/rooms/{room["room_id"]}/surrender')
        result = call(a, 'GET', '/me/state')
        assert result['last_result']['result_type'] == 'win'
        assert result['last_result']['points'] == 140
        call(teacher, 'POST', f'/matches/{room["match_id"]}/rejudge', {
            'reason': 'Smoke test correction', 'new_results': [
                {'student_id': ua['id'], 'result_type': 'loss'}, {'student_id': ub['id'], 'result_type': 'win'},
            ],
        })
        assert call(b, 'GET', '/me/state')['last_result']['points'] == 100
        assert call(a, 'GET', '/me/state')['last_result']['points'] == 70
        call(teacher, 'POST', f'/battles/{battle}/stop')
        report = call(a, 'GET', f'/me/results/{battle}')
        assert report['students'][0]['tasks'][0]['submissions'][0]['source_code'] == 'print(3)'
        assert call(teacher, 'GET', f'/battles/{battle}/statistics')['summary']['participants'] == 2
        call(outsider, 'GET', f'/me/results/{battle}', status=403)
        call(teacher, 'POST', f'/battles/{battle}/finish')
        print('PASS: invite admission and private result history; PostgreSQL migrations, Nginx/WebSocket, Celery → Redis → browser events, access checks, checker callback deduplication, surrender and rejudge.')
        print(json.dumps({'battle_id': battle, 'room_id': room['room_id'], 'student_external_id': ua['external_id'], 'teacher_external_id': f'{prefix}-Учитель'}, ensure_ascii=False))
    finally:
        for sock in sockets:
            if sock.connected:
                sock.disconnect()
        checker.shutdown()
        checker.server_close()


if __name__ == '__main__':
    main()
