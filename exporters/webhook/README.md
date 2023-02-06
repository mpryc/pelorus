# Webhook Exporter

A simple Webhook exporter written using FastAPI and pydantic that exposes metrics to the prometheus endpoint.

Currently only some of the commit time data is received, no SSL/salt to secure the data. It's PoC.

```shell
$ cd exporters/webhook
$ export LOG_LEVEL=debug
$ uvicorn app:app
```

To sent some data you can use simple curl:

```shell
curl -X POST http://localhost:8000/pelorus/webhook -d @./testdata/pelorus_committime.json -H "Content-Type: application/json" -H "User-Agent: Pelorus-Webhook/test" -H "X-Pelorus-Event: committime"
```

To check if the metric was received, open web page:
http://localhost:8000/metrics
