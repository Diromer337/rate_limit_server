import configparser
import time
import ipaddress

import redis
from flask import request


class User:
    def __init__(self, user_request: request, db: redis.Redis):
        self.db = db
        self.max_req, self.ban_time, self.prefix_size = self._read_config()
        self.user_network = self._get_network(user_request)

    def get_ban_time(self):
        return self.ban_time

    @staticmethod
    def _read_config():
        config = configparser.ConfigParser()
        config.read('config.ini')
        max_req = int(config['DEFAULT']['max_req'])
        ban_time = int(config['DEFAULT']['ban_time'])
        prefix_size = config['DEFAULT']['prefix_size']
        return max_req, ban_time, prefix_size

    def _get_network(self, user_request: request):
        if user_request.headers.getlist('X-Forwarded-For'):
            ip = user_request.headers.getlist('X-Forwarded-For')[0]
        else:
            ip = user_request.remote_addr
        user_network = ipaddress.ip_interface(ip + '/' + self.prefix_size)
        return str(user_network.network)

    def not_banned(self):
        request_time = int(time.time())
        if self._check_ban(self.user_network, request_time):
            return False
        self._del_old_requests(self.user_network, request_time)
        self.db.rpush(self.user_network, str(request_time))
        if self.db.llen(self.user_network) == self.max_req:
            self.db.delete(self.user_network)
            self.db.rpush(self.user_network, 'ban', str(request_time))
        return True

    def _del_old_requests(self, subnet: str, request_time: int):
        if self.db.llen(subnet) != 0:
            low_time = request_time - 60
            requests = [int(x) for x in self.db.lrange(subnet, 0, -1) if int(x) >= low_time]
            self.db.delete(subnet)
            if len(requests) != 0:
                self.db.rpush(subnet, *requests)

    def limit_reset(self):
        self.db.delete(self.user_network)

    def _check_ban(self, subnet: str, request_time: int) -> bool:
        if self.db.llen(subnet) != 0:
            status = self.db.lrange(subnet, 0, 0)[0]
            if status == b'ban':
                ban_time = int(self.db.lrange(subnet, 1, 1)[0])
                if request_time - ban_time > self.ban_time:
                    self.db.delete(subnet)
                    return False
                else:
                    return True
        return False
