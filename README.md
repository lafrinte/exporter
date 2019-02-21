## deploy

* command

```
python3 -m sanic app.app --host=HOST --port=PORT --worker=WORKER_NUM
```

* log

only enable stream log

## request

### redis

* data source

instance data is from command `redis info`.

cluster state data is from command `cluster info`

cluster archtechive is from command `cluster nodes`

* request redis data

if request from terminal, use `pretty=True` will enable indent to json data

```
➜  json-exportor git:(master) ✗ curl http://127.0.0.1:8000/metrics/redis\?pretty\=True\&url\=redis://:123@172.21.3.163\&url\=redis://localhost
```

* request monitor statue

```
➜  json-exportor git:(master) ✗ curl http://127.0.0.1:8000/api/state
{"state":"running"}%
```

### mysql

* data source

instance data is from command `show global status` and `show variables`

cluster state is from command `show slave status` if current node has a valid output

cluster archtechive is from command `show slave status`, getting master host and port from the output

* request mysql data

```
➜  json-exportor git:(master) ✗ curl http://127.0.0.1:8000/metrics/mysql\?pretty\=True\&url\=mysql://root:123@127.0.0.1:3306
```

## response

* redis format

```
{
   "instance": {
      url1: data1,
      url2: data2,
      ...
   },
   "cluster": [
      {
          "arch": {arch_data},
          "state": {state_data}
      }
   ]   
}
```

```
{
    "instance":{
        "redis:\/\/localhost":{
            "redis_version":"5.0.3",
            "redis_git_sha1":0,
            "redis_git_dirty":0,
            ...
        },
        "redis:\/\/172.21.3.163":{
            "redis_version":"3.2.8",
            "redis_git_sha1":0,
            "redis_git_dirty":0,
            ...
        },
        "redis:\/\/172.21.3.165:6380":{
            "redis_version":"3.2.8",
            "redis_git_sha1":0,
            "redis_git_dirty":0,
            ...
        },
        "redis:\/\/172.21.3.165:6379":{
            "redis_version":"3.2.8",
            "redis_git_sha1":0,
            "redis_git_dirty":0,
            ...
        },
        "redis:\/\/172.21.3.164:6380": null,
        "redis:\/\/172.21.3.164:6379":{
            "redis_version":"3.2.8",
            "redis_git_sha1":0,
            "redis_git_dirty":0,
            ...
        },
        "redis:\/\/172.21.3.163:6379":{
            "redis_version":"3.2.8",
            "redis_git_sha1":0,
            "redis_git_dirty":0,
            ...
        },
        "redis:\/\/172.21.3.163:6380":{
            "redis_version":"3.2.8",
            "redis_git_sha1":0,
            ...
        }
    },
    "cluster":[
        {
            "arch":[
                {
                    "id":"3ef2858610c95a8ed3ab91af288c0bb1ed9cffab",
                    "url":"redis:\/\/172.21.3.163:6379",
                    "flags":"master",
                    "master":null,
                    "link-state":"connected",
                    "slots":[
                        "0-5461"
                    ],
                    "migrations":[

                    ]
                },
                {
                    "id":"035d0c5712b5dbeca42b93661884fd943ef7904b",
                    "url":"redis:\/\/172.21.3.165:6380",
                    "flags":"master",
                    "master":null,
                    "link-state":"connected",
                    "slots":[
                        "5462-10923"
                    ],
                    "migrations":[

                    ]
                },
                {
                    "id":"8c428f6b2662de28b1d8d9cb37c0df531c64e08d",
                    "url":"redis:\/\/172.21.3.163:6380",
                    "flags":"slave",
                    "master":"6fe50d517066244b7320cbd268f8516f2561be52",
                    "link-state":"connected",
                    "slots":[

                    ],
                    "migrations":[

                    ]
                },
                {
                    "id":"03845f0a46c52bb59fc7349d8ad807e6b38ced3f",
                    "url":"redis:\/\/172.21.3.164:6380",
                    "flags":"slave",
                    "master":"3ef2858610c95a8ed3ab91af288c0bb1ed9cffab",
                    "link-state":"disconnected",
                    "slots":[

                    ],
                    "migrations":[

                    ]
                },
                {
                    "id":"6fe50d517066244b7320cbd268f8516f2561be52",
                    "url":"redis:\/\/172.21.3.165:6379",
                    "flags":"master",
                    "master":null,
                    "link-state":"connected",
                    "slots":[
                        "10924-16383"
                    ],
                    "migrations":[

                    ]
                },
                {
                    "id":"0bd76723b0e42695ab5821966ec9ffc0bd763376",
                    "url":"redis:\/\/172.21.3.164:6379",
                    "flags":"slave",
                    "master":"035d0c5712b5dbeca42b93661884fd943ef7904b",
                    "link-state":"connected",
                    "slots":[

                    ],
                    "migrations":[

                    ]
                }
            ],
            "state":{
                "cluster_state":"ok",
                "cluster_slots_assigned":"16384",
                "cluster_slots_ok":"16384",
                "cluster_slots_pfail":"0",
                "cluster_slots_fail":"0",
                "cluster_known_nodes":"6",
                "cluster_size":"3",
                "cluster_current_epoch":"6",
                "cluster_my_epoch":"1",
                "cluster_stats_messages_sent":"39455331",
                "cluster_stats_messages_received":"6629953"
            }
        }
    ]
}%
```

* mysql format

```
{
   "instance": {
      url1: data1,
      url2: data2,
       ...
   },
   "cluster": [
      {
          "arch": {
            "master": master_url,
            "slave": slave_url
            },
          "state": {state_data}
      }
   ]   
}
```

```
{
    "instance": {
        "mysql:\/\/172.18.232.142:8801":{
            "Aborted_clients":"29517",
            "Aborted_connects":"0",
            ...
        },
        "mysql:\/\/127.0.0.1:3306":{
            "Aborted_clients":"6",
            "Aborted_connects":"0",
            ...
        },
        "mysql:\/\/172.18.232.144:8801":{
            "Aborted_clients":"27035",
            "Aborted_connects":"5",
            ...
        }
    },
    "cluster":[
        {
            "arch":{
                "master":"mysql:\/\/172.18.232.144:8801",
                "slave":"mysql:\/\/172.18.232.142:8801"
            },
            "state":{
                "Slave_IO_State":"Waiting for master to send event",
                "Master_Host":"172.18.232.144",
                "Master_User":"sla",
                "Master_Port":8801,
                "Connect_Retry":2,
                "Master_Log_File":"mysql-bin.000002",
                "Read_Master_Log_Pos":96550794,
                "Relay_Log_File":"relay-bin.000005",
                "Relay_Log_Pos":48219118,
                "Relay_Master_Log_File":"mysql-bin.000002",
                "Slave_IO_Running":"Yes",
                "Slave_SQL_Running":"Yes",
                ...
            }
        }
    ]
}
```

## test case

```
➜  json-exportor git:(master) ✗ py.test -q test_restful.py
```
