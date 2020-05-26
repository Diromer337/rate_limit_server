import redis
from flask import Flask
from flask import abort
from flask import make_response
from flask import render_template
from flask import request

from user import User

app = Flask(__name__)

log_history = redis.Redis(host='redis', port=6379)


@app.errorhandler(429)
def error(e):
    resp = make_response(render_template('429.html'), 429)
    resp.headers['Retry-After'] = str(e.description)
    return resp


@app.route('/reset')
def reset():
    user = User(request, log_history)
    user.limit_reset()
    return 'reseted'


@app.route('/')
def start():
    user = User(request, log_history)
    if user.not_banned():
        return 'OK'
    else:
        abort(429, description=user.get_ban_time())


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=1337)
