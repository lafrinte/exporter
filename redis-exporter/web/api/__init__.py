#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sanic import Blueprint


api = Blueprint('api', url_prefix='/api')

from . import views
