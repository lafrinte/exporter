#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools

def parse_cluster_nodes(func):

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
