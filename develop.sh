#!/bin/bash

export ENVIRONMENT=local

docker run -d -it --rm --name redis-dto-supplier-frontend redis 

docker run --rm -it \
    --env REDIS_HOST \
    --link redis-dto-supplier-frontend:redis \
    -p 5003:5003 \
    dto-supplier-frontend bash
docker stop redis-dto-supplier-frontend 