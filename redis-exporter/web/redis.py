#!/usr/bin/env python
# -*- coding: utf-8 -*-


from sanic.log import logger

from web.public import GlobalVars
from web.decorator import parse_cluster_nodes

from aiocache import cached

from aredis import StrictRedis
from aredis import ResponseError, ConnectionError, TimeoutError


class AsyncRedis(StrictRedis):

    def __init__(self, *args, **kwargs):
        super(AsyncRedis, self).__init__(*args, **kwargs)
        self.connection_kwargs = self.connection_pool.connection_kwargs
        self.password = self.connection_kwargs['password']
        self.strict_url = 'redis://{}:{}'.format(self.connection_kwargs['host'], self.connection_kwargs['port'])

    async def is_instance_alive(self):
        msg = 'A {} raised when handle a session to {}'

        try:
            return await self.ping()
        except ConnectionError:
            logger.warning(msg.format('ConnectionError', self.strict_url))
            return False
        except TimeoutError:
            logger.warning(msg.format('TimeoutError', self.strict_url))
            return False
        except:
            logger.warning(msg.format('UnExpected', self.strict_url))
            return False

    async def is_cluster(self, instance_data=None):
        msg = 'A {} raised when handle a session to {}'

        if instance_data:
            return True if instance_data.get('redis_mode') == 'cluster' else False

        try:
            return True if await self.cluster_info() else False
        except ConnectionError:
            logger.warning(msg.format('ConnectionError', self.strict_url))
            return False
        except TimeoutError:
            logger.warning(msg.format('TimeoutError', self.strict_url))
            return False
        except ResponseError:
            logger.warning(msg.format('ResponseError', self.strict_url))
            return False
        except:
            logger.warning(msg.format('UnExpected', self.strict_url))
            return False

    @parse_cluster_nodes
    async def get_cluster_nodes_info(self):
        return await self.execute_command('cluster nodes')

    # return all url in the same cluster. if the login url requires password, the url returned will
    # add the password into url
    # url with no password: redis://localhost:port
    # url with password:    redis://:password@localhost:port
    async def get_cluster_nodes_set(self, nodes_info=None):
        info = await self.get_cluster_nodes_info() if not nodes_info else nodes_info
        source_nodes = (x for x in map(lambda x: x.get('url'), info))
        if self.password:
            source_nodes = (x for x in map(lambda x:''.join([x[:8], ':', self.password, '@', x[8:]]), source_nodes))
        return set(source_nodes)

    async def get_instance_info(self):
        is_alive = await self.is_instance_alive()
        return await self.info() if is_alive else None

    async def get_cluster_state_info(self):
        is_cluster = await self.is_cluster()
        return await self.cluster_info() if is_cluster else None


class RedisInfo(object):

    def __init__(self, urls):
        self.urls = urls
        self.instances_data = dict()
        self.clusters_data = dict()
        self.options = dict(decode_responses=True)

    def shadow_password(self, url):
        return ''.join([url[:8], url[url.index('@') + 1:]]) if '@' in url else url

    def _get_session(self, url):
        return GlobalVars.urls[url] if url in GlobalVars.urls else AsyncRedis.from_url(url, **self.options)

    async def _get_cluster_state_info(self, url):
        return await Cache.url[url].get_cluster_state_info()

    async def get_all_datas(self):
        cluster_nodes, instances_datas, cluster_datas = set(), list(), list()

        for url in self.urls:
            session = self._get_session(url)
            temp_in_data = await session.get_instance_info()

            if temp_in_data and temp_in_data['redis_mode'] == 'cluster' and url not in cluster_nodes:
                logger.info('Detect new cluster node {}, start to get cluster info'.format(self.shadow_password(url)))
                temp_clu_arch_data = await session.get_cluster_nodes_info()
                nodes = await session.get_cluster_nodes_set(temp_clu_arch_data)
                temp_clu_state_data = await session.get_cluster_state_info()

                # reflush cluster_nodes
                cluster_nodes = cluster_nodes | nodes

                # if other instances in same cluster but not in urls, add the other instances login url
                # at the end of urls.
                self.urls.extend(list(set(nodes) - {url}))
                cluster_datas.append(dict(state=temp_clu_state_data,
                                          architecture=temp_clu_arch_data))
            instances_datas.append({url: temp_in_data})
        return instances_datas, cluster_datas
