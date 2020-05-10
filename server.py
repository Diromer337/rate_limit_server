import redis
import time
from flask import Flask
from flask import request

app = Flask(__name__)
log_history = redis.Redis()


def get_client_ip():
    if request.headers.getlist('X-Forwarded-For'):
        ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        ip = request.remote_addr
    return ip


def get_subnet(ip: str) -> str:
    lst = ip.split('.')
    subnet = '.'.join(lst[0:-1])
    return subnet


def del_old_requests(subnet: str, request_time: int):
    if log_history.llen(subnet) != 0:
        low_time = request_time - 60
        requests = [int(x) for x in log_history.lrange(subnet, 0, -1) if int(x) >= low_time]
        log_history.delete(subnet)
        log_history.rpush(subnet, *requests)


def check_ban(subnet, request_time):
    if log_history.llen(subnet) != 0:
        status = log_history.lrange(subnet, 0, 0)[0]
        if status == b'ban':
            ban_time = int(log_history.lrange(subnet, 1, 1)[0])
            if request_time - ban_time > 120:
                log_history.delete(subnet)
                return False
            else:
                return True
    return False


def ip_not_banned(ip: str) -> bool:
    subnet = get_subnet(ip)
    request_time = int(time.time())
    if check_ban(subnet, request_time):
        return False
    del_old_requests(subnet, request_time)
    log_history.rpush(subnet, str(request_time))
    if log_history.llen(subnet) == 100:
        log_history.delete(subnet)
        log_history.rpush(subnet, 'ban', str(request_time))
    return True


@app.route('/')
def start():
    ip = get_client_ip()
    if ip_not_banned(ip):
        return 'OK'
    else:
        return 'too_many_requests', 429


if __name__ == '__main__':
    app.run('0.0.0.0', 1337)
