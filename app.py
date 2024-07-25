# -*- coding: utf-8 -*-
"""
    Project startup file
"""

import os

from flask import Flask, jsonify, make_response, request

from app.chat import chat
from app.git import git
from utils.LogHandler import log

app = Flask(__name__)
app.config['debug'] = True

# Blueprint registration
app.register_blueprint(chat, url_prefix='/chat')
app.register_blueprint(git, url_prefix='/git')


@app.route('/actuator/health', methods=['GET', 'HEAD'])
def health():
    return jsonify({'online': True})


@app.errorhandler(400)
@app.errorhandler(404)
def handle_error(error):
    error_code = str(error.code)
    error_msg = 'Invalid request parameters' if error.code == 400 else 'Page not found'
    return make_response(jsonify({'code': error_code, 'msg': error_msg}), error.code)


if __name__ == '__main__':
    # os.environ['STABILITY_HOST'] = 'grpc.stability.ai:443'
    app.config['JSON_AS_ASCII'] = False
    log.info('Starting the app...')
    app.run(debug=True, host="0.0.0.0", use_reloader=False)
