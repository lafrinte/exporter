#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import api
from sanic import response


@api.route('/')
async def state(request):
    return response.json(dict(state='running'))
