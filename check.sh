#!/bin/bash

LOG=repocheck-`date +%F-%T`.log

echo "Logging to $LOG"

REPOS=$@
if [ -z "$REPOS" ]
then
   REPOS="oneiric precise oneiric-shadow precise-shadow"
fi

for R in $REPOS
do
   echo "Update $R"
   reprepro -V -b $R update
done

for R in $REPOS
do
   DISTRO=${R%-shadow}
   echo "Check $R distro $DISTRO"
   ./rc2.py --path $R --distro $DISTRO | tee -a $LOG
done
