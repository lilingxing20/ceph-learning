#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# step1: 从ceph集群导出osdmap,pg_dump.txt
# ceph osd getmap -o ceph_osdmap
# ceph pg dump > ceph_pgdump.txt
#
# step2: 新建或修改crushmap
# ceph osd getcrushmap -o ceph_crushmap
# crushtool -d ceph_crushmap -o ceph_crushmap.txt
# vim ceph_crushmap.txt
# crushtool -c ceph_crushmap.txt -o ceph_crushmap_u1
#
# step3: 若没有新加osd，跳过；否则，需要调整下osdmap中的max_osd属性
# 注：此osdmaptool命令经过修改源码重编译
# osdmaptool --resize_max_osd 929 ceph_osdmap --mark-up-in
#
# step4: 对比修改crushmap前后pgs map变化情况，计算数据迁移量
# python compare_crush_change.py --osdmap-file ceph_osdmap --pgdump_file ceph_pgdump.txt --crushmap-file ceph_crushmap_u1
# # osdmaptool --test-map-pgs-dump ceph_osdmap
# # cp ceph_osdmap ceph_osdmap_2019-06-27-16-35-13
# # osdmaptool --import-crush ceph_crushmap_u1 ceph_osdmap_2019-06-27-16-35-13
# # osdmaptool --test-map-pgs-dump ceph_osdmap_2019-06-27-16-35-13
# POOL                 REMAPPED OSDs        BYTES REBALANCE      OBJECTS REBALANCE   
# vms-ssd              0                    0                    0                   
# volumes-sas          20580                21017348781910       5020453             
# volumes-ssd          0                    0                    0                   
# images               5156                 467021956326         403127              
# backups              5099                 133823466820         31916               
# vms-sas              10294                7771412843148        1893108
#


import ast
import json
import os
import subprocess
import argparse
import sys
import time


FNULL = open(os.devnull, 'w')


def get_pg_info(pg_dump_info):
    pg_data = {}
    pg_objects = {}
    # args = ['sudo', 'ceph', 'pg', 'dump']
    args = ['cat', pg_dump_info]
    pgmap = subprocess.check_output(args, stderr=FNULL).split('\n')

    for line in pgmap:
        if line[0].isdigit():
            pg_id = line.split('\t')[0]
            pg_bytes = line.split('\t')[6]
            pg_obj = line.split('\t')[1]
            pg_data[pg_id] = pg_bytes
            pg_objects[pg_id] = pg_obj
        elif line.startswith('pool'):
            break

    return pg_data, pg_objects


# assume the osdmap test output is the same lenght and order...
# if add support for PG increase that's gonna break.
def diff_output(original_map_pgs_dump, new_map_pgs_dump, pools, original_pg_dump_file):
    """
    """
    results = {}

    pg_data, pg_objects = get_pg_info(original_pg_dump_file)

    for i in range(len(original_map_pgs_dump)):
        orig_i = original_map_pgs_dump[i]
        new_i = new_map_pgs_dump[i]

        if orig_i[0].isdigit():
            pg_id = orig_i.split('\t')[0]
            pool_id = pg_id[0]
            pool_name = pools[pool_id]['pool_name']

            if not pool_name in results:
                results[pool_name] = {}
                results[pool_name]['osd_remap_counter'] = 0
                results[pool_name]['osd_bytes_movement'] = 0
                results[pool_name]['osd_objects_movement'] = 0

            original_mappings = ast.literal_eval(orig_i.split('\t')[1])
            new_mappings = ast.literal_eval(new_i.split('\t')[1])
            intersection = list(set(original_mappings).intersection(set(new_mappings)))

            osd_movement_for_this_pg = int(pools[pool_id]['pool_size']) - len(intersection)
            osd_data_movement_for_this_pg = int(osd_movement_for_this_pg) * int(pg_data[pg_id])
            osd_object_movement_for_this_pg = int(osd_movement_for_this_pg) * int(pg_objects[pg_id])

            results[pool_name]['osd_remap_counter'] += osd_movement_for_this_pg
            results[pool_name]['osd_bytes_movement'] += int(osd_data_movement_for_this_pg)
            results[pool_name]['osd_objects_movement'] += int(osd_object_movement_for_this_pg)

        elif orig_i.startswith('#osd'):
            break

    return results


def osdmaptool_test_map_pgs_dump(osdmap_file):
    args = ['osdmaptool', '--test-map-pgs-dump', osdmap_file]
    print(' '.join(args))
    pgs_dump_info = subprocess.check_output(args, stderr=FNULL).split('\n')
    return pgs_dump_info


def import_crushmap(osdmap_file, crushmap_file):
    args = ['osdmaptool', '--import-crush', crushmap_file, osdmap_file]
    print(' '.join(args))
    subprocess.call(args, stdout=FNULL, stderr=subprocess.STDOUT)


def copy_file(original_file, new_file):
    args = ['cp', original_file, new_file]
    print(' '.join(args))
    subprocess.call(args, stdout=FNULL, stderr=subprocess.STDOUT)


def get_pools_info(osdmap_file):
    pools = {}
    args = ['osdmaptool', '--print', osdmap_file]
    osdmap_out = subprocess.check_output(args, stderr=FNULL).split('\n')
    for line in osdmap_out:
        if line.startswith('pool'):
            pool_id = line.split()[1]
            pool_size = line.split()[5]
            pool_name = line.split()[2].replace("'","")
            pools[pool_id] = {}
            pools[pool_id]['pool_size'] = pool_size
            pools[pool_id]['pool_name'] = pool_name
        elif line.startswith('max_osd'):
            break

    return pools


def test_map_pgs_dump(original_osdmap_file, original_pg_dump_file, new_crushmap_file):
    """
    模拟ceph集群crushmap调整，对比前后pg map信息，计算数据迁移量
    """
    # original map pgs dump
    original_map_pgs_dump = osdmaptool_test_map_pgs_dump(original_osdmap_file)

    # use new crushmap build new osdmap
    time_str = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    new_osdmap_file = "%s_%s" % (original_osdmap_file, time_str)
    copy_file(original_osdmap_file, new_osdmap_file)
    import_crushmap(new_osdmap_file, new_crushmap_file)

    # new pgs dump
    new_map_pgs_dump = osdmaptool_test_map_pgs_dump(new_osdmap_file)

    # delete new osdmap file
    #os.remove(new_osdmap_file)

    # get pools info
    pools = get_pools_info(original_osdmap_file)

    # diff pgs dump info
    results = diff_output(original_map_pgs_dump, new_map_pgs_dump, pools, original_pg_dump_file)

    return results


def dump_plain_output(results):
    """
    输出结果
    """
    sys.stdout.write("%-20s %-20s %-20s %-20s\n" % ("POOL", "REMAPPED OSDs", "BYTES REBALANCE", "OBJECTS REBALANCE"))

    for pool in results:
        sys.stdout.write("%-20s %-20s %-20s %-20s\n" % (pool,
                                                        results[pool]['osd_remap_counter'],
                                                        results[pool]['osd_bytes_movement'],
                                                        results[pool]['osd_objects_movement']
                                                        )
                        )


def parse_args():
    parser = argparse.ArgumentParser(description='Ceph CRUSH change data movement calculator.')

    parser.add_argument(
        '--osdmap-file',
        help="Where to save the original osdmap. Temp one will be <location>.new. Default: /tmp/osdmap",
        default="/tmp/osdmap",
        dest="osdmap_file"
        )
    parser.add_argument(
        '--crushmap-file',
        help="CRUSHmap to run the movement test against.",
        required=True,
        dest="new_crushmap"
        )
    parser.add_argument(
        '--pgdump-file',
        help="Ceph pg dump results.",
        required=True,
        dest="pgdump_file"
        )

    parser.add_argument(
        '--format',
        help="Output format. Default: plain",
        choices=['json', 'plain'],
        dest="format",
        default="plain"
        )

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    """
    计算ceph集群crushmap改变后，计算数据迁移量
    """
    ctx = parse_args()

    results = test_map_pgs_dump(ctx.osdmap_file, ctx.pgdump_file, ctx.new_crushmap)

    FNULL.close()

    if ctx.format == 'json':
        print json.dumps(results)
    elif ctx.format == 'plain':
        dump_plain_output(results)

