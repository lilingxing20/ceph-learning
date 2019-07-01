#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# ceph/src/osd/osd_types.cc
#
# [root@node244 ~]# python calc_pg_split.py --old-pg-num=8 --new-pg-num=24
# parent_pg: 0.0, children_pg: 0.8
# parent_pg: 0.0, children_pg: 0.10
# parent_pg: 0.1, children_pg: 0.9
# parent_pg: 0.1, children_pg: 0.11
# parent_pg: 0.2, children_pg: 0.a
# parent_pg: 0.2, children_pg: 0.12
# parent_pg: 0.3, children_pg: 0.b
# parent_pg: 0.3, children_pg: 0.13
# parent_pg: 0.4, children_pg: 0.c
# parent_pg: 0.4, children_pg: 0.14
# parent_pg: 0.5, children_pg: 0.d
# parent_pg: 0.5, children_pg: 0.15
# parent_pg: 0.6, children_pg: 0.e
# parent_pg: 0.6, children_pg: 0.16
# parent_pg: 0.7, children_pg: 0.f
# parent_pg: 0.7, children_pg: 0.17
# 
# Ceph Storage Pool: 0
#   Split pg number: 8
#   New  pg  number: 16
#

import os
import sys
import argparse


POOL_ID = 0


def calc_bits_of(t):
    b = 0
    while (t > 0):
        t = t >> 1
        b += 1
    return b


def ceph_stable_mod(x, b, bmask):
    if ((x & bmask) < b):
        return x & bmask
    else:
        return x & (bmask >> 1)


def is_split(pool_id, old_pg_num, new_pg_num, m_seed):

    if (new_pg_num <= old_pg_num):
        return None

    old_bits = calc_bits_of(old_pg_num)
    old_mask = (1 << old_bits) - 1
    n = 1
    children_pg = []
    while True:
        next_bit = (n << (old_bits-1))
        s = next_bit | m_seed
        if (s < old_pg_num or s == m_seed):
            continue
        if (s >= new_pg_num):
            break;
        if ceph_stable_mod(s, old_pg_num, old_mask) == m_seed:
            print("parent_pg: %d.%x, children_pg: %d.%x" % (POOL_ID, m_seed, POOL_ID, s))
            children_pg.append("%s.%x" % (POOL_ID, s))
        n += 1
    return children_pg


def calc_pg_split(pool_id, old_pg_num, new_pg_num):

    _pg_split_list = []
    _pg_create_list = []
    for i in xrange(old_pg_num):
        _children_pg = is_split(pool_id, old_pg_num, new_pg_num, i)
        if _children_pg:
            _pg_create_list += _children_pg
            _pg_split_list.append("%d.%x" % (pool_id, i))

    print("\nCeph Storage Pool: %d" % pool_id)
    print("  Split pg number: %d" % len(_pg_split_list))
    print("  New  pg  number: %d\n" % len(_pg_create_list))


def parse_args():
    parser = argparse.ArgumentParser(description='Ceph storage pool pg num increased, calculate pg split number.')

    parser.add_argument(
        '--pool-id',
        help="Ceph storage pool id.",
        # required=True,
        type=int,
        default=0,
        dest="pool_id"
        )
    parser.add_argument(
        '--old-pg-num',
        help="Ceph storage pool old pg number.",
        required=True,
        type=int,
        default=16,
        dest="old_pg_num"
        )
    parser.add_argument(
        '--new-pg-num',
        help="Ceph storage pool new pg number.",
        required=True,
        type=int,
        default=32,
        dest="new_pg_num"
        )

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    """
    计算ceph集群存储池pg数调大后，被分裂的pg数，新增的pg数
    """
    ctx = parse_args()

    calc_pg_split(ctx.pool_id, ctx.old_pg_num, ctx.new_pg_num)

