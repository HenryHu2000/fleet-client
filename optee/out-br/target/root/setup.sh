#!/bin/sh

if ! ifconfig | grep -q "wlan0" ; then
  sed -i 's/ctrl_interface=[^\n]*//g' /etc/wpa_supplicant.conf
  sed -i 's/ssid=\"[^\n]*\"/ssid=\"ASK4 Wireless\"/g' /etc/wpa_supplicant.conf
  sed -i 's/psk=\"[^\n]*\"/key_mgmt=NONE/g' /etc/wpa_supplicant.conf
  wpa_supplicant -i wlan0 -c /etc/wpa_supplicant.conf -B
  udhcpc -i wlan0
fi

cd /tmp/
wget http://worldtimeapi.org/api/timezone/Etc/GMT.txt
date @$(sed -nr 's/unixtime: ([0-9]+)/\1/p' GMT.txt)
rm GMT.txt

python <<EOF
import os
import os.path
import ssl
import stat
import subprocess
import sys
import certifi
STAT_0o775 = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
             | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP
             | stat.S_IROTH |                stat.S_IXOTH )
openssl_dir, openssl_cafile = os.path.split(
    ssl.get_default_verify_paths().openssl_cafile)
# change working directory to the default SSL directory
os.chdir(openssl_dir)
relpath_to_certifi_cafile = os.path.relpath(certifi.where())
print(" -- removing any existing file or link")
try:
    os.remove(openssl_cafile)
except FileNotFoundError:
    pass
print(" -- creating symlink to certifi certificate bundle")
os.symlink(relpath_to_certifi_cafile, openssl_cafile)
print(" -- setting permissions")
os.chmod(openssl_cafile, STAT_0o775)
print(" -- update complete")
EOF

scp -o StrictHostKeyChecking=accept-new hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/resources/data.tar .
tar -xf data.tar -C /root/
rm data.tar
