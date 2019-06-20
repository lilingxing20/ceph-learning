#!/bin/bash
#
# cd ceph/src/
# MON=3 OSD=10 ./vstart.sh mon osd -d -n
# ./add_osd.sh 11 15
#
start_osd_id=$1
end_osd_id=$2

set -e

if [ -z "$CEPH_BUILD_ROOT" ]; then
    [ -z "$CEPH_BIN" ] && CEPH_BIN=.
    [ -z "$CEPH_LIB" ] && CEPH_LIB=.libs
    [ -z $EC_PATH ] && EC_PATH=$CEPH_LIB
    [ -z $OBJCLASS_PATH ] && OBJCLASS_PATH=$CEPH_LIB
else
    [ -z $CEPH_BIN ] && CEPH_BIN=$CEPH_BUILD_ROOT/bin
    [ -z $CEPH_LIB ] && CEPH_LIB=$CEPH_BUILD_ROOT/lib
    [ -z $EC_PATH ] && EC_PATH=$CEPH_LIB/erasure-code
    [ -z $OBJCLASS_PATH ] && OBJCLASS_PATH=$CEPH_LIB/rados-classes
fi

export PYTHONPATH=./pybind
export LD_LIBRARY_PATH=$CEPH_LIB
export DYLD_LIBRARY_PATH=$LD_LIBRARY_PATH


run() {
    type=$1
    shift
    eval "valg=\$valgrind_$type"
    [ -z "$valg" ] && valg="$valgrind"

    if [ -n "$valg" ]; then
	echo "valgrind --tool=$valg $* -f &"
	valgrind --tool=$valg $* -f &
	sleep 1
    else
	if [ "$nodaemon" -eq 0 ]; then
	    echo "$*"
	    $*
	else
	    echo "ceph-run $* -f &"
	    ./ceph-run $* -f &
	fi
    fi
}



[ -z "$CEPH_DIR" ] && CEPH_DIR="$PWD"
[ -z "$CEPH_DEV_DIR" ] && CEPH_DEV_DIR="$CEPH_DIR/dev"
# sudo if btrfs
test -d $CEPH_DEV_DIR/osd0/. && test -e $CEPH_DEV_DIR/sudo && SUDO="sudo"
HOSTNAME=`hostname -s`
[ -z "$CEPH_DIR" ] && CEPH_DIR="$PWD"
[ -z "$CEPH_DEV_DIR" ] && CEPH_DEV_DIR="$CEPH_DIR/dev"

overwrite_conf=1
conf_fn="$CEPH_DIR/ceph.conf"
keyring_fn="$CEPH_DIR/keyring"

ARGS="-c $conf_fn"

cephx=0
new=1
[ "$cephx" -eq 1 ] && [ "$new" -eq 1 ] && test -e $keyring_fn && rm $keyring_fn
if [ "$cephx" -eq 1 ]; then
    CEPH_ADM="$CEPH_BIN/ceph -c $conf_fn -k $keyring_fn"
else
    CEPH_ADM="$CEPH_BIN/ceph -c $conf_fn"
fi


# add osd
for osd in `seq ${start_osd_id} ${end_osd_id}`
do
    if [ "$new" -eq 1 ]; then
        if [ $overwrite_conf -eq 1 ]; then
    	    cat <<EOF >> $conf_fn
[osd.$osd]
        host = $HOSTNAME
EOF
    	    rm -rf $CEPH_DEV_DIR/osd$osd || true
    	    for f in $CEPH_DEV_DIR/osd$osd/* ; do btrfs sub delete $f || true ; done || true
    	    mkdir -p $CEPH_DEV_DIR/osd$osd
        fi
    
        uuid=`uuidgen`
        echo "add osd$osd $uuid"
        $SUDO $CEPH_ADM osd create $uuid
        $SUDO $CEPH_ADM osd crush add osd.$osd 1.0 host=$HOSTNAME root=default
        $SUDO $CEPH_BIN/ceph-osd -i $osd $ARGS --mkfs --mkkey --osd-uuid $uuid
    
        key_fn=$CEPH_DEV_DIR/osd$osd/keyring
        echo adding osd$osd key to auth repository
        $SUDO $CEPH_ADM -i $key_fn auth add osd.$osd osd "allow *" mon "allow profile osd"
    fi
    echo start osd$osd
    run 'osd' $SUDO $CEPH_BIN/ceph-osd -i $osd $ARGS $COSD_ARGS
done


