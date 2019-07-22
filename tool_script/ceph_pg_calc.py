#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
Created Time: Mon 22 Jul 2019 11:29:19 AM CST
File Name   : ceph_pg_calc.py
Ceph pgcalc : https://ceph.com/pgcalc/
Version     : v1 init
[root@lixx pg_calc]# python ceph_pg_calc.py -s 3 -o 100 -t 100 -n cinder-backup -n cinder-volumes -n ephemeral-vms -n glance-images -p 25 -p 53 -p 15 -p 7
------------------------------------------------------------------------------------------------------------------
| Pool ID  | Pool Name            | size     | OSD num  | %Data    | Target PGs per OSD   | Suggested PG Count   |
------------------------------------------------------------------------------------------------------------------
| 0        | cinder-backup        | 3        | 100      | 25       | 100                  | 1024                 |
------------------------------------------------------------------------------------------------------------------
| 1        | cinder-volumes       | 3        | 100      | 53       | 100                  | 2048                 |
------------------------------------------------------------------------------------------------------------------
| 2        | ephemeral-vms        | 3        | 100      | 15       | 100                  | 512                  |
------------------------------------------------------------------------------------------------------------------
| 3        | glance-images        | 3        | 100      | 7        | 100                  | 256                  |
------------------------------------------------------------------------------------------------------------------
|                       Total Data Percentage: 100      |                               PG Total Count: 3840     |
------------------------------------------------------------------------------------------------------------------
'''

import argparse
import getpass
import math

def build_arg_parser():
    """
    Builds a standard argument parser with arguments for Ceph PGs calc:
    -n Name of the pool in question. Typical pool names are included below.
    -s Number of replicas the pool will have. Default value of 3 is pre-filled.
    -o Number of OSDs which this Pool will have PGs in. Typically, this is the entire Cluster OSD
       count, but could be less based on CRUSH rules. (e.g. Separate SSD and SATA disk sets).
    -t This value should be populated based on the following guidance:
       100 If the cluster OSD count is not expected to increase in the foreseeable future.
       200 If the cluster OSD count is expected to increase (up to double the size) in the foreseeable future.
    -p This value represents the approximate percentage of data which will be contained in this pool for that specific OSD set.
    """
    parser = argparse.ArgumentParser(
        description='Standard Arguments for Ceph PGs calc')

    parser.add_argument('-n', '--name',
                        default=[],
                        action='append',
                        help='Name of the pool in question. Typical pool names are included below.'
                        'Default is None.')

    parser.add_argument('-s', '--size',
                        # required=True,
                        type=int,
                        default=3,
                        action='store',
                        help='Number of replicas the pool will have. Default value of 3 is pre-filled.')

    parser.add_argument('-o', '--osd_num',
                        # required=True,
                        type=int,
                        default=100,
                        action='store',
                        help='Number of OSDs which this Pool will have PGs in. Typically, this'
                        'is the entire Cluster OSD count, but could be less based on CRUSH rules.'
                        '(e.g. Separate SSD and SATA disk sets). ')

    parser.add_argument('-t', '--target_pgs_per_osd',
                        # required=True,
                        type=int,
                        default=100,
                        action='store',
                        help='This value should be populated based on the following guidance:'
                        '100 If the cluster OSD count is not expected to increase in the foreseeable'
                        'future.'
                        '200 If the cluster OSD count is expected to increase (up to double the size)'
                        'in the foreseeable future.')

    parser.add_argument('-p', '--percentage',
                        default=[],
                        action='append',
                        help='This value represents the approximate percentage of data which will'
                        'be contained in this pool for that specific OSD set.')

    return parser


def prompt_for_percentage(args):
    """
    if no percentage is specified on the command line, prompt for it
    """
    if not args.percentage:
        args.percentage = getpass.getpass(
            prompt='Enter Data Percentage : ')
    return args


def get_args():
    """
    """
    parser = build_arg_parser()

    args = parser.parse_args()

    return prompt_for_percentage(args)


def pg_calc(target_pgs_per_osd, osd_num, percentage, size):
    """
    """
    pg_count = ( target_pgs_per_osd * osd_num * percentage ) / size / 100

    pg_count1 = osd_num / size
    if pg_count < pg_count1:
        pg_count = pg_count1
    else:
        x = int(math.log(pg_count, 2))
        pg_count_last = math.pow(2, x)
        pg_count_next = math.pow(2, x+1)
        if (pg_count - pg_count_last) < (pg_count_last - pg_count):
            pg_count = pg_count_last
        else:
            pg_count = pg_count_next

    return int(pg_count)


def print_line():
    print '-' * 114

def ceph_pool_pg_calc(ctx):
    percentage_all = sum([int(p) for p in ctx.percentage])
    if percentage_all <= 100:
        _columns_four = "| {0:<8} | {1:<20} | {2:<8} | {3:<8} | {4:<8} | {5:<20} | {6:<20} |"
        print_line()
        print _columns_four.format("Pool ID", "Pool Name", "size", "OSD num", "%Data", "Target PGs per OSD", "Suggested PG Count")
        print_line()
        pool_id = 0
        pg_total_count = 0
        total_percentage = 0
        for r in map(lambda n, p: (n, p), ctx.name, ctx.percentage):
            suggested_pg_count = pg_calc(ctx.target_pgs_per_osd, ctx.osd_num, int(r[1]), ctx.size)
            pg_total_count += suggested_pg_count
            total_percentage += int(r[1])
            print _columns_four.format(pool_id, r[0], ctx.size, ctx.osd_num, r[1],
                    ctx.target_pgs_per_osd, suggested_pg_count)
            print_line()
            pool_id += 1
        # tatal
        _columns_four2 = "| {0:>44} {1:<8} | {2:>45} {3:<8} |"
        print _columns_four2.format("Total Data Percentage:", total_percentage, "PG Total Count:", pg_total_count)
        print_line()
    else:
        print "\nThe data percentage is greater than 100 !\n"


if __name__ == '__main__':
    ctx = get_args()
    # print ctx

    ceph_pool_pg_calc(ctx)

# end
