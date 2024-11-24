#!/bin/bash

if [[ $(ps aux|grep python| grep picframe| grep -v grep) ]]; then
   # echo "Picframe is already running"
   exit 0
fi

code_dir=/home/pi/code/picframe
cd ${code_dir}
source build/bin/activate
python picframe/start.py  /mnt/storage/picframe_data/config/configuration.yaml > ${HOME}/runPicframe.log
# echo "${0} started now $(date +%Y%m%d-%H%M%S)" > ${HOME}/picframe.log
