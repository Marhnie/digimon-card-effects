#!/bin/bash
D=/c/Users/Daewonmedia/ourai_data; cd $D
echo "RESUME $(date)" >> $D/evom_checkpoint.done
for i in 1 2 3 4 5; do nohup bash evom_goal.sh $i > /dev/null 2>&1 & done
nohup bash evom_goal_check.sh >> evom_goal_check.log 2>&1 &
nohup bash allround_loop.sh >> allround/loop.log 2>&1 &
wait
