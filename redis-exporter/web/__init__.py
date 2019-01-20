#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sanic import Sanic, Blueprint, response
from web.api import api


def create_app():
    app = Sanic(__name__)

    app.blueprint(api)
    app.blueprint(metrics)

    return app


app = create_app()
