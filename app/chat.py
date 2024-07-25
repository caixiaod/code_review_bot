# -*- coding: utf-8 -*-
from os import abort

from flask import Blueprint, request, jsonify

from utils.LogHandler import log


chat = Blueprint('chat', __name__)


@chat.route('/api')
def question():
    return 'hello world'

