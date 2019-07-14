#!/bin/bash

# $1: .fil name
# $2: output key
# $3: nset/elset name

THIS=$(readlink -f $0)
EXE=${THIS%.*}
FILD=$(dirname $1)
FILN=$(basename ${1%.*})
KEY=$2
SET=$3

pushd $FILD

python3 $EXE.py $FILN.fil $KEY $SET

popd
