# CoTalk Backend

`Concord`队软工项目`CoTalk`的后端仓库

## API文档

参见 [API Overview | CoTalk API Docs (jason-fu-git.github.io)](https://jason-fu-git.github.io/CoTalkReference/api-docs.html)

## WebSocket部署
启动docker引擎并打开一个终端，运行

    docker run -it --rm --name redis -p 6379:6379 redis

> 替代方案
> 
> 1. 在 Linux 系统上运行 `sudo apt install redis-server`，下载 `redis-server`
> 2. 新建 `tumx` 虚拟终端，例如执行命令 ` tmux new -s redis`
> 3. 在新建的终端里运行`redis-server`，执行命令 `redis-server --port 6379 --bind 127.0.0.1`
> 4. 按`ctrl+B`,再按`D`键，退出虚拟终端

同时另外打开一个终端，运行

    python manage.py runserver

此时可以通过localhost:8000访问网页。