#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sanic.log import logger
from asyncio import gather, ensure_future

from web.public import GlobalVars
from web.decorator import parse_cluster_nodes

from aredis import StrictRedis
from aredis import ResponseError, ConnectionError, TimeoutError


class AsyncRedis(StrictRedis):

    def __init__(self, *args, **kwargs):
        super(AsyncRedis, self).__init__(*args, **kwargs)
        self.connection_kwargs = self.connection_pool.connection_kwargs
        self.password = self.connection_kwargs["password"]
        self.strict_url = "redis://{}:{}".format(self.connection_kwargs["host"], self.connection_kwargs["port"])

    async def is_instance_alive(self):
        msg = "A {} raised when handle a session to {}"

        try:
            return await self.ping()
        except ConnectionError:
            logger.error(msg.format("ConnectionError", self.strict_url))
            return False
        except TimeoutError:
            logger.error(msg.format("TimeoutError", self.strict_url))
            return False
        except:
            logger.error(msg.format("UnExpected", self.strict_url))
            return False

    async def is_cluster(self, instance_data=None):
        msg = "A {} raised when handle a session to {}"

        if instance_data:
            return True if instance_data.get("redis_mode") == "cluster" else False

        try:
            return True if await self.cluster_info() else False
        except ConnectionError:
            logger.error(msg.format("ConnectionError", self.strict_url))
            return False
        except TimeoutError:
            logger.error(msg.format("TimeoutError", self.strict_url))
            return False
        except ResponseError:
            logger.error(msg.format("ResponseError", self.strict_url))
            return False
        except:
            logger.error(msg.format("UnExpected", self.strict_url))
            return False

    @parse_cluster_nodes
    async def get_cluster_nodes_info(self):
        return await self.execute_command("cluster nodes")

    # return all url in the same cluster. if the login url requires password, the url returned will
    # add the password into url
    # url with no password: redis://localhost:port
    # url with password:    redis://:password@localhost:port
    async def get_cluster_nodes_set(self, nodes_info=None):
        info = await self.get_cluster_nodes_info() if not nodes_info else nodes_info
        source_nodes = (x for x in map(lambda x: x.get("url"), info))
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
        self.urls = set(urls)
        self.options = dict(decode_responses=True)
        self.datastore = dict(cluster_urls=set(),
                              other_urls=set())

    def shadow_password(self, url):
        return ''.join([url[:8], url[url.index('@') + 1:]]) if '@' in url else url

    def _get_session(self, url):
        return GlobalVars.urls[url] if url in GlobalVars.urls else AsyncRedis.from_url(url, **self.options)

    async def collection(self, url, cluster=True):
        data, shadow_url = dict(instance=dict(), cluster=dict()), self.shadow_password(url)

        logger.info("Start collection for {}".format(self.shadow_password(url)))

        session = self._get_session(url)
        data["instance"][shadow_url] = await session.get_instance_info()

        if cluster and data["instance"][shadow_url].get('redis_mode') == 'cluster' and url not in self.datastore["cluster_urls"]:
            logger.info("Detect new cluster node {}, start to get cluster info".format(shadow_url))
            data['cluster']['arch'] = await session.get_cluster_nodes_info()
            nodes = await session.get_cluster_nodes_set(data['cluster']['arch'])

            # reflush cluster_urls and other urls
            self.datastore["cluster_urls"] = self.datastore["cluster_urls"] | nodes
            self.datastore["other_urls"] = self.datastore["other_urls"] | nodes
            data['cluster']['state'] = await session.get_cluster_state_info()
        return data

    async def get_all_datas(self):
        results = await gather(*[ensure_future(self.collection(url)) for url in self.urls])
        undo_urls = self.datastore["other_urls"] - self.urls

        if undo_urls:
            undo_result = await gather(*[ensure_future(self.collection(url, False)) for url in undo_urls])
            results.extend(undo_result)

        return dict(instance=[x["instance"] for x in results if x.get("instance")],
                    cluster=[x["cluster"] for x in results if x.get("cluster")])
