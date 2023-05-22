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
