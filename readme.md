# CoTalk Backend

`Concord`队软工项目`CoTalk`的后端仓库

## API文档

参见 [API Overview | CoTalk API Docs (jason-fu-git.github.io)](https://jason-fu-git.github.io/CoTalkReference/api-docs.html)

## WebSocket部署
启动docker引擎并打开一个终端，运行

    docker run -it --rm --name redis -p 6379:6379 redis

同时另外打开一个终端，运行

    python manage.py runserver

此时可以通过localhost:8000访问网页。