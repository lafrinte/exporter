#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from web import create_app
from web.lib.utils import shadow_password


@pytest.yield_fixture
def app():
    app = create_app()
    yield app


@pytest.fixture
def test_cli(loop, app, test_client):
    return loop.run_until_complete(test_client(app))


async def test_redis(test_cli):
    url = 'redis://:123@172.21.3.163'
    resp = await test_cli.get('/metrics/redis?url={}'.format(url))
    data = await resp.json()

    if resp.status == 200:
        assert shadow_password(url) in data.get('instance')


async def test_mysql(test_cli):
    url = 'mysql://teledb:teledb11!!@172.18.232.142:8801'
    resp = await test_cli.get('/metrics/mysql?url={}'.format(url))
    data = await resp.json()

    if resp.status == 200:
        assert shadow_password(url) in data.get('instance')
