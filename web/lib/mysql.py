#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sanic.log import logger
from asyncio import gather, ensure_future

from .utils import shadow_password

from aiomysql import Connection
from aiomysql import OperationalError
from aiomysql.cursors import DeserializationCursor, DictCursor
from urllib.parse import urlparse

from typing import Dict, List


class AsyncMysql(Connection):

    def __init__(self, *args, **kwargs):
        super(AsyncMysql, self).__init__(*args, **kwargs)
        self.default_cursors = (DeserializationCursor, DictCursor)
        self.strict_url = 'mysql://{}:{}'.format(self.host, self.port)
        self.connect_cursor = None

    async def __aenter__(self):
        msg = 'An {} Error raised when connect to {}'

        try:
            await self._connect()
            self.connect_cursor = await self.cursor(*self.default_cursors)
        except OperationalError:
            logger.error(msg.format('OperationalError', self.strict_url))
            return None
        except:
            logger.error(msg.format("UnExpected", self.strict_url))
            return None
        return self

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

    async def get_master_url(self, slave_info: Dict[str, str or int or float]) -> str:
        host, port = slave_info.get('Master_Host'), slave_info.get('Master_Port')
        return 'mysql://{}:{}@{}:{}'.format(self.user, self._password, host, port)

    async def get_status(self) -> Dict[str, str or int or float]:
        await self.connect_cursor.execute('show global status')
        data = await self.connect_cursor.fetchall()
        return {x['Variable_name']:x['Value'] for x in data} if data else dict()

    async def get_variables(self) -> Dict[str, str or int]:
        await self.connect_cursor.execute('show variables')
        data = await self.connect_cursor.fetchall()
        return {x['Variable_name']:x['Value'] for x in data} if data else dict()

    async def get_slave_status(self) -> Dict[str, str or int]:
        await self.connect_cursor.execute('show slave status')
        data = await self.connect_cursor.fetchall()
        return data[0] if data else dict()

    async def get_master_status(self) -> Dict[str, str or int]:
        await self.connect_cursor.execute('show master status')
        data = await self.connect_cursor.fetchall()
        return data[0] if data else dict()

    async def get_sql_output(self, sql: str) -> List[Dict[str, str or int]]:
        await self.connect_cursor.execute(sql)
        data = await self.connect_cursor.fetchall()
        return data if data else list()


class MysqlInfo(object):

    def __init__(self, urls):
        self.urls = set(urls)

        # if a node has slave info, we will parse the slave info to get master url, and then save the master
        # and slave info into self.datastore['cluster']. if the master url is not in self.urls. we put it into
        # self.datastore['other_urls'], collection action will collect it after all self.urls finished.
        self.datastore = dict(cluster=list(), other_urls=set())

    async def collection(self, url: str) -> Dict[str, Dict]:
        shadow_url, status, variables = shadow_password(url), dict(), dict()

        logger.info("Start collection for {}".format(shadow_url))
        async with AsyncMysql.from_url(url) as session:
            if session:
                status = await session.get_status()
                variables = await session.get_variables()
                slave_status = await session.get_slave_status()

                if slave_status:
                    master_url = await session.get_master_url(slave_status)
                    if master_url not in self.urls:
                        logger.info("Detect new cluster node {}".format(shadow_password(master_url)))
                        self.datastore['other_urls'].add(master_url)
                        self.datastore['cluster'].append(dict(arch=dict(master=shadow_password(master_url),
                                                                        slave=shadow_url),
                                                              state=slave_status))
        return shadow_url, dict(status, **variables)

    async def get_all_datas(self) -> Dict[str, Dict]:
        results = await gather(*[ensure_future(self.collection(url)) for url in self.urls])

        if self.datastore['other_urls']:
            other_results = await gather(*[ensure_future(self.collection(url)) for url in self.datastore['other_urls']])
            results.extend(other_results)
        return dict(instance={x[0]:x[1] for x in results},
                    cluster=self.datastore['cluster'])
