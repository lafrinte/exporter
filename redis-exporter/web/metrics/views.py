#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import metrics
from sanic import response
from web.redis import RedisInfo
from web.public import GlobalVars


@metrics.route('/redis')
async def state(request):
    is_pretty = request.args.get('pretty') if 'pretty' in request.args else False
    obj = RedisInfo(request.args['url'])
    all = await obj.get_all_datas()
    return response.json(all, indent=4 if is_pretty else 0)
