Shadowsocks 远程安装部署脚本，目前支持 CentOS。

## requirements

- python 2.7.x
- fabric

## configure

```
$ cp .fabrc.example .fabrc
$ vi .fabrc # 添加远程主机名，Shadowsocks 用户信息
```

## usage

```
$ fab init        # 初始化
$ fab up          # 启动
$ fab iptab       # iptables
```