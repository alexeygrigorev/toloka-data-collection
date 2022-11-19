

If you run docker on WSL2, run this first (once)

```bash
wsl -d docker-desktop
sysctl -w vm.max_map_count=262144
exit
```

Start elastic:

```bash
docker run -it \
    -p 9200:9200 \
    -p 9300:9300 \
    -v es_toloka_data:/usr/share/elasticsearch/data \
    -e "discovery.type=single-node" \
    -e ELASTIC_PASSWORD="changeme" \
    docker.elastic.co/elasticsearch/elasticsearch:8.5.1
```

Credentials:

* user: elastic
* password: changeme