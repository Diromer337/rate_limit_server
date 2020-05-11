import redis
from flask import Flask
from flask import abort
from flask import request
from user import User

app = Flask(__name__)
log_history = redis.Redis(host='redis', port=6379)


@app.route('/reset')
def reset():
    pass


@app.route('/')
def start():
    user = User(request, log_history)
    if user.not_banned():
        return 'OK'
    else:
        abort(429, 'You only allow 100 requests')


if __name__ == '__main__':
    app.run('0.0.0.0', 1337)
