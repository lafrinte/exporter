#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sanic.log import logger
from asyncio import gather, ensure_future

from .utils import shadow_password

from aiomysql import Connection
from aiomysql import OperationalError
from aiomysql.cursors import DeserializationCursor, DictCursor
from urllib.parse import urlparse


class AsyncMysql(Connection):

    def __init__(self, *args, **kwargs):
        super(AsyncMysql, self).__init__(*args, **kwargs)
        self.default_cursors = (DeserializationCursor, DictCursor)

    @classmethod
    def from_url(cls, url, **kwargs):
        url, url_options = urlparse(url), dict()
        url_options = dict(db=url.path.replace('/', '') if url.path else None,
                           user=url.username,
                           port=url.port if url.port else 3306,
                           host=url.hostname if url.hostname else 'localhost',
                           password=url.password,
                           connect_timeout=5)
        url_options.update(kwargs)
        return cls(**url_options)

    async def get_master_url(self, slave_info=None):
        if not slave_info:
            slave_info = await self.get_slave_status()
        host = slave_info.get('Master_Host')
        port = slave_info.get('Master_Port')
        return 'mysql://{}:{}@{}:{}'.format(self.user, self._password, host, port)

    async def _get_cursor(self):
        msg = "A {} raised when handle a session to {}"
        strict_url = 'mysql://{}:{}'.format(self.host, self.port)

        if self.closed:
            try:
                await self._connect()
            except OperationalError:
                logger.error(msg.format('OperationalError', strict_url))
                return None
            except:
                logger.error(msg.format("UnExpected", strict_url))
                return None
        return await self.cursor(*self.default_cursors)

    async def get_status(self):
        cursor = await self._get_cursor()
        if not cursor:
            return dict()

        await cursor.execute('show global status')
        data = await cursor.fetchall()
        return {x['Variable_name']:x['Value'] for x in data}

    async def get_variables(self):
        cursor = await self._get_cursor()
        if not cursor:
            return dict()

        await cursor.execute('show variables')
        data = await cursor.fetchall()
        return {x['Variable_name']:x['Value'] for x in data}

    async def get_slave_status(self):
        cursor = await self._get_cursor()
        if not cursor:
            return dict()

        await cursor.execute('show slave status')
        data = await cursor.fetchall()
        return data[0] if data else data

    async def get_master_status(self):
        cursor = await self._get_cursor()
        if not cursor:
            return dict()

        await cursor.execute('show master status')
        return await cursor.fetchall()

    async def get_sql_output(self, sql, key=None):
        cursor = await self._get_cursor()
        if not cursor:
            return dict()

        await cursor.execute(sql)
        data = await cursor.fetchall()
        return {key: data} if key else data


class MysqlInfo(object):

    def __init__(self, urls):
        self.urls = set(urls)

        # if a node has slave info, we will parse the slave info to get master url, and then save the master
        # and slave info into self.datastore['cluster']. if the master url is not in self.urls. we put it into
        # self.datastore['other_urls'], collection action will collect it after all self.urls finished.
        self.datastore = dict(cluster=list(), other_urls=set())

    async def collection(self, url, cluster=True):
        shadow_url = shadow_password(url)

        logger.info("Start collection for {}".format(shadow_url))
        session = AsyncMysql.from_url(url)
        status = await session.get_status()
        variables = await session.get_variables()
        master_status = await session.get_master_status()
        slave_status = await session.get_slave_status()

        if slave_status:
            master_url = await session.get_master_url(slave_status)
            if master_url not in self.urls:
                logger.info("Detect new cluster node {}".format(shadow_password(master_url)))
                self.datastore['other_urls'].add(master_url)
                self.datastore['cluster'].append(dict(arch=dict(master=shadow_password(master_url),
                                                                slave=shadow_url),
                                                      state=slave_status))
        return {shadow_url: dict(status, **variables)}

    async def get_all_datas(self):
        results = await gather(*[ensure_future(self.collection(url)) for url in self.urls])

        if self.datastore['other_urls']:
            other_results = await gather(*[ensure_future(self.collection(url)) for url in self.datastore['other_urls']])
            results.extend(other_results)
        return dict(instance=[x for x in results],
                    cluster=self.datastore['cluster'])
