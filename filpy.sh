#!/bin/bash

# $1: .fil name
# $2: output key
# $3: node/element id file

THIS=$(readlink -f $0)
EXE=${THIS%.*}
FILD=$(dirname $1)
FILN=$(basename ${1%.*})
KEY=$2
ID=$(basename $3)

pushd $FILD

if [ -f $FILN.fil ]; then

abaqus $EXE<<EOS && python $EXE.py
$FILN
$KEY
$ID
EOS

else

  echo 'Error: '$FILN'.fil not found'

fi
popd
