import configparser
import time

import redis
from flask import request


class User:
    def __init__(self, user_request: request, db: redis.Redis):
        self.user_request = user_request
        self.db = db
        self.max_req, self.ban_time = self.read_config()

    @staticmethod
    def read_config():
        config = configparser.ConfigParser()
        config.read('config.ini')
        max_req = config['DEFAULT']['max_req']
        ban_time = config['DEFAULT']['max_req']
        return max_req, ban_time

    def not_banned(self):
        subnet = self.get_subnet(self.user_request)
        request_time = int(time.time())
        if self._check_ban(subnet, request_time):
            return False
        self._del_old_requests(subnet, request_time)
        self.db.rpush(subnet, str(request_time))
        if self.db.llen(subnet) == 100:
            self.db.delete(subnet)
            self.db.rpush(subnet, 'ban', str(request_time))
        return True

    def _del_old_requests(self, subnet: str, request_time: int):
        if self.db.llen(subnet) != 0:
            low_time = request_time - 60
            requests = [int(x) for x in self.db.lrange(subnet, 0, -1) if int(x) >= low_time]
            self.db.delete(subnet)
            if len(requests) != 0:
                self.db.rpush(subnet, *requests)

    @staticmethod
    def get_subnet(user_request):
        if user_request.headers.getlist('X-Forwarded-For'):
            ip = user_request.headers.getlist('X-Forwarded-For')[0]
        else:
            ip = user_request.remote_addr
        lst = ip.split('.')
        subnet = '.'.join(lst[0:-1])
        return subnet

    def _check_ban(self, subnet: str, request_time: int) -> bool:
        if self.db.llen(subnet) != 0:
            status = self.db.lrange(subnet, 0, 0)[0]
            if status == b'ban':
                ban_time = int(self.db.lrange(subnet, 1, 1)[0])
                if request_time - ban_time > 120:
                    self.db.delete(subnet)
                    return False
                else:
                    return True
        return False
