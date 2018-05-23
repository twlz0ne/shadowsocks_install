# -*- coding: utf-8; mode: python -*-

# @author: gongqijian@gmail.com
# @date: 2017-01-18

from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm

execfile('.fabrc')

def fread(file_name):
    with open(file_name, 'r') as f:
        content = f.read()
    return content

cmd_init = '''\
dtime=$(date +"%%Y-%%m-%%d_%%H.%%M.%%S")
supervisord_conf=/etc/supervisord.conf
shadowsocks_conf=/etc/shadowsocks/config.json

# ----------------------------------------------------------------------
# shadowsocks
# ----------------------------------------------------------------------
[[ -z $(which ssserver) ]] && yum -y update && yum install -y python-pip && pip install shadowsocks
[[ -f $shadowsocks_conf ]] && cp $shadowsocks_conf{,-$dtime}
mkdir -p $(dirname $shadowsocks_conf)
cat<<EOF>$shadowsocks_conf
{
    "server":"0.0.0.0",
    "port_password":{
        "%(port_password)s"
    },
    "local_address":"127.0.0.1",
    "local_port":1080,
    "timeout":300,
    "method":"aes-256-cfb"
}
EOF

# ----------------------------------------------------------------------
# supervisor
# ----------------------------------------------------------------------
[[ -z $(which supervisorctl) ]] && yum install -y supervisor

[[ -f $supervisord_conf ]] && mv $supervisord_conf{,-$dtime}
echo_supervisord_conf > $supervisord_conf
cat<<EOF>>$supervisord_conf
[include]
files = /etc/supervisor/conf.d/*.conf
EOF

[[ -f /etc/rc.d/init.d/supervisord ]] || cat<<EOF>/etc/rc.d/init.d/supervisord
%(file_content)s
EOF

chmod +x /etc/rc.d/init.d/supervisord
chkconfig --add supervisord
chkconfig supervisord on
service supervisord start

mkdir -p /etc/supervisor/conf.d/
cat<<EOF>/etc/supervisor/conf.d/shadowsocks.conf
[program:shadowsocks]
command=ssserver -c /etc/shadowsocks/config.json
autostart=true
autorestart=true
user=nobody
EOF''' % {
    'port_password' : '",\n\t"'.join(map(lambda (_, port, secret): '":"'.join([port,secret]), users)),
    'file_content'  : fread('./etc/rc.d/init.d/supervisord')
}

cmd_iptab = '''\
iptab_save() {
    local suffix=$1
    local ostype=$(sed -n -e 's/^ID_LIKE=\\(.*\\)/\\1/p' /etc/os-release | xargs)
    case $ostype in
        debian      ) iptables-save > /etc/iptables/rules.v4$suffix;;
        rhel\ fedora) iptables-save > /etc/sysconfig/iptables$suffix;;
        *           ) echo "Unknow so type: '$ostype'"; exit 1;;
    esac
}

# 备份&清除旧规则
dtime=$(date +"%%Y-%%m-%%d_%%H.%%M.%%S")
iptab_save .$dtime

iptables -F
iptables -X
iptables -Z

# 基本端口
iptables -A INPUT -p tcp --dport 22 -j ACCEPT       # ssh
iptables -A INPUT -p tcp --dport 443 -j ACCEPT      # https

# shadowsocks 端口
iptables -A INPUT -p tcp --dport 1080 -j ACCEPT
%(ss_user_rules)s

# 扩展规则
%(extra_rules)s

# 允许已连接端口的后续数据包
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 禁止其他未允许的规则访问
iptables -A INPUT -j REJECT
iptables -A FORWARD -j REJECT

# 保存新规则
iptab_save''' % {
    'ss_user_rules': '\n'.join(map(lambda (_, port, __): 'iptables -A INPUT -p tcp --dport %s -j ACCEPT' % int(port), users)),
    'extra_rules': extra_rules
}

@task
def init():
    run(cmd_init)

@task
def iptab():
    run(cmd_iptab)

@task
def up():
    run('supervisorctl restart shadowsocks')