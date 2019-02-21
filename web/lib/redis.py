#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools

from sanic.log import logger
from asyncio import gather, ensure_future

from .utils import shadow_password

from aredis import StrictRedis
from aredis import ResponseError, ConnectionError, TimeoutError

from typing import Dict, List, Set


def parse_redis_cluster_nodes(func):

    def parse_slots(s):
        slots, migrations = [], []
        for r in s.split(' '):
            if '->-' in r:
                slot_id, dst_node_id = r[1:-1].split('->-', 1)
                migrations.append({
                    'slot': int(slot_id),
                    'node_id': dst_node_id,
                    'state': 'migrating'
                })
            elif '-<-' in r:
                slot_id, src_node_id = r[1:-1].split('-<-', 1)
                migrations.append({
                    'slot': int(slot_id),
                    'node_id': src_node_id,
                    'state': 'importing'
                })
            else:
                slots.append(r)
        return slots, migrations

    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        resp = await func(*args, **kwargs)
        nodes = []

        if isinstance(resp, str):
            resp = resp.splitlines()

        for line in resp:
            parts = line.split(' ', 8)
            self_id, addr, flags, master_id, ping_sent, \
                pong_recv, config_epoch, link_state = parts[:8]

            host, port = addr.rsplit(':', 1)

            node = {
                'id': self_id,
                'url': 'redis://{}:{}'.format(host, port.split('@')[0]),
                'flags': list(set(flags.split(',')) - {'myself', 'fail'})[0],
                'master': master_id if master_id != '-' else None,
                'link-state': link_state,
                'slots': [],
                'migrations': [],
            }

            if len(parts) >= 9:
                slots, migrations = parse_slots(parts[8])
                node['slots'], node['migrations'] = tuple(slots), migrations

            nodes.append(node)
        return nodes
    return wrapped


class AsyncRedis(StrictRedis):

    def __init__(self, *args, **kwargs):
        super(AsyncRedis, self).__init__(*args, **kwargs)
        self.connection_kwargs = self.connection_pool.connection_kwargs
        self.password = self.connection_kwargs["password"]
        self.strict_url = "redis://{}:{}".format(self.connection_kwargs["host"], self.connection_kwargs["port"])

    async def is_instance_alive(self) -> bool:
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

    async def is_cluster(self) -> bool:
        msg = "A {} raised when handle a session to {}"

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

    @parse_redis_cluster_nodes
    async def get_cluster_nodes_info(self) -> str:
        return await self.execute_command("cluster nodes")

    # return all url in the same cluster. if the login url requires password, the url returned will
    # add the password into url
    # url with no password: redis://localhost:port
    # url with password:    redis://:password@localhost:port
    async def get_cluster_nodes_set(self, nodes_info: List[Dict]) -> Set[str]:
        source_nodes = (x for x in map(lambda x: x.get("url"), nodes_info))
        if self.password:
            source_nodes = (x for x in map(lambda x:''.join([x[:8], ':', self.password, '@', x[8:]]), source_nodes))
        return set(source_nodes)

    async def get_instance_info(self) -> Dict[str, str or int or float]:
        is_alive = await self.is_instance_alive()
        return await self.info() if is_alive else dict()

    async def get_cluster_state_info(self) -> Dict[str, str or int or float]:
        is_cluster = await self.is_cluster()
        return await self.cluster_info() if is_cluster else dict()


class RedisInfo(object):

    def __init__(self, urls):
        self.urls = set(urls)
        self.options = dict(decode_responses=True)
        self.datastore = dict(cluster_urls=set(),
                              other_urls=set())

    async def collection(self, url: str) -> Dict[str, Dict]:
        instance, cluster, shadow_url = dict(), dict(), shadow_password(url)

        logger.info("Start collection for {}".format(shadow_url))
        session = AsyncRedis.from_url(url, **self.options)
        instance = await session.get_instance_info()

        if instance.get('redis_mode') == 'cluster' and url not in self.datastore["cluster_urls"]:
            logger.info("Detect new cluster node {}, start to get cluster info".format(shadow_url))
            cluster['arch'] = await session.get_cluster_nodes_info()
            nodes = await session.get_cluster_nodes_set(cluster['arch'])

            # reflush cluster_urls and other urls
            self.datastore["cluster_urls"] = self.datastore["cluster_urls"] | nodes
            self.datastore["other_urls"] = self.datastore["other_urls"] | nodes
            cluster['state'] = await session.get_cluster_state_info()
        return shadow_url, instance, cluster

    async def get_all_datas(self) -> Dict[str, Dict]:
        results = await gather(*[ensure_future(self.collection(url)) for url in self.urls])
        undo_urls = self.datastore["other_urls"] - self.urls

        if undo_urls:
            undo_result = await gather(*[ensure_future(self.collection(url)) for url in undo_urls])
            results.extend(undo_result)

        return dict(instance={x[0]:x[1] for x in results if x[1]},
                    cluster=[x[2] for x in results if x[2]])
