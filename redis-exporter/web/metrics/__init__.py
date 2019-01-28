#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sanic import Blueprint


metrics = Blueprint('metrics', url_prefix='/metrics')

from . import views
