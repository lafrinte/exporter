#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aiocache import Cache
from aiocache.serializers import JsonSerializer


class GlobalVars(object):
    urls = dict()
    cache = Cache(serializer=JsonSerializer())
