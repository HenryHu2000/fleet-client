#!/bin/sh

cd /tmp/
wget http://worldtimeapi.org/api/timezone/Etc/GMT.txt
date @$(sed -nr 's/unixtime: ([0-9]+)/\1/p' GMT.txt)
