#!/bin/sh

while true
do
  date >> monitor.log
  TOP_RESULT="$(top -b -n 1)"
  echo "$TOP_RESULT" | grep "python" >> monitor.log
  echo "$TOP_RESULT" | grep "darknetp" >> monitor.log
  cat /sys/class/thermal/thermal_zone0/temp >> monitor.log
  sleep 5
done
