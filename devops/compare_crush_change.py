#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# step1: 从ceph集群导出osdmap, pg_dump.txt
# ceph osd getmap -o ceph_osdmap.bin
# ceph pg dump > ceph_pgdump.txt
#
# step2: 新建或修改crushmap
# ceph osd getcrushmap -o ceph_crushmap
# crushtool -d ceph_crushmap -o ceph_crushmap.txt
# vim ceph_crushmap.txt
# crushtool -c ceph_crushmap.txt -o ceph_crushmap_update1
#
# step4: 查看osdmap信息
# crushtool ceph_osdmap.bin --print
# | osdmaptool: osdmap file 'ceph_osdmap.bin'
# | epoch 6078
# | fsid 0d8a6a0f-c187-44db-8115-75818a960fa9
# | created 2017-08-24 11:10:54.748383
# | modified 0.000000
# | flags 
# | 
# | pool 0 'rbd' replicated size 2 min_size 1 crush_ruleset 0 object_hash rjenkins pg_num 64 pgp_num 64 last_change 1 flags hashpspool stripe_width 0
# | pool 1 'volumes' replicated size 2 min_size 1 crush_ruleset 0 object_hash rjenkins pg_num 128 pgp_num 128 last_change 6058 flags hashpspool stripe_width 0
# |     removed_snaps [1~4,6~3,a~6]
# | pool 2 'images' replicated size 2 min_size 1 crush_ruleset 0 object_hash rjenkins pg_num 128 pgp_num 128 last_change 6057 flags hashpspool stripe_width 0
# |     removed_snaps [1~2,5~1,7~9,14~2,17~7,25~5,2b~1,2f~2,32~6,3d~2,42~11,54~8,60~2,66~2,6b~2,6e~7,76~8,80~2,83~1,85~9,90~6,9b~2,9f~1,a1~1,a9~3,ae~1,b4~2]
# | pool 3 'vms' replicated size 2 min_size 1 crush_ruleset 0 object_hash rjenkins pg_num 128 pgp_num 128 last_change 6062 flags hashpspool stripe_width 0
# |     removed_snaps [1~1a3]
# | pool 5 'backups' replicated size 2 min_size 1 crush_ruleset 0 object_hash rjenkins pg_num 256 pgp_num 256 last_change 4806 flags hashpspool stripe_width 0
# | 
# | max_osd 20
# | osd.0 up   in  weight 1 up_from 6040 up_thru 6048 down_at 6038 last_clean_interval [5938,6039) 192.168.100.14:6811/25750 192.168.200.14:6802/1025750 192.168.200.14:6803/1025750 192.168.100.14:6806/1025750 exists,up f0cafdd7-bdd1-441b-b124-cf1d66c4b421
# | ......
#
# step4: 对比修改crushmap前后pgs map变化情况，计算数据迁移量
# 注：此osdmaptool命令经过修改源码重编译
# python compare_crush_change.py --osdmap-file ceph_osdmap.bin --pgdump-file ceph_pgdump.txt --crushmap-file ceph_crushmap_update1.bin --new-max-osd 21 --new-osd-weight 0.1
# | osdmaptool --test-map-pgs-dump ceph_osdmap.bin
# | cp ceph_osdmap.bin ceph_osdmap.bin_2019-07-24-17-14-44
# | osdmaptool --print ceph_osdmap.bin_2019-07-24-17-14-44
# | osdmaptool --resize_max_osd 21 ceph_osdmap.bin_2019-07-24-17-14-44
# | osdmaptool --import-crush ceph_crushmap_update1.bin ceph_osdmap.bin_2019-07-24-17-14-44
# | osdmaptool --test-map-pgs-dump ceph_osdmap.bin_2019-07-24-17-14-44
# | 
# | PG ID    ORIGINAL OSD SET   NEW OSD SET        PG MIGRATION        
# | 0.0      [6, 4]             [10, 11]           ['6-->10', '4-->11']
# | 1.6a     [10, 13]           [10, 6]            ['13-->6']          
# | 2.14     [15, 9]            [15, 2]            ['9-->2']           
# | 2.40     [15, 12]           [18, 0]            ['15-->18', '12-->0']
# | 2.7e     [17, 15]           [17, 12]           ['15-->12']         
# | 3.32     [17, 7]            [17, 0]            ['7-->0']           
# | 3.59     [19, 6]            [3, 7]             ['19-->3', '6-->7'] 
# | 3.66     [10, 6]            [11, 9]            ['10-->11', '6-->9']
# | 3.71     [19, 3]            [11, 13]           ['19-->11', '3-->13']
# | 5.2      [6, 8]             [9, 0]             ['6-->9', '8-->0']  
# | 5.e6     [7, 13]            [7, 6]             ['13-->6']          
# | 5.eb     [15, 10]           [15, 17]           ['10-->17']         
# | Total Remap PG num: 12
# | 
# | OSD_ID   IN_PGS_NUM   OUT_PGS_NUM  IN_PGS               OUT_PGS             
# | 0        3            0            ['2.40', '3.32', '5.2'] []                  
# | 2        1            0            ['2.14']             []                  
# | 3        1            1            ['3.59']             ['3.71']            
# | 4        0            1            []                   ['0.0']             
# | 6        2            4            ['1.6a', '5.e6']     ['0.0', '3.59', '3.66', '5.2']
# | 7        1            1            ['3.59']             ['3.32']            
# | 8        0            1            []                   ['5.2']             
# | 9        2            1            ['3.66', '5.2']      ['2.14']            
# | 10       1            2            ['0.0']              ['3.66', '5.eb']    
# | 11       3            0            ['0.0', '3.66', '3.71'] []                  
# | 12       1            1            ['2.7e']             ['2.40']            
# | 13       1            2            ['3.71']             ['1.6a', '5.e6']    
# | 15       0            2            []                   ['2.40', '2.7e']    
# | 17       1            0            ['5.eb']             []                  
# | 18       1            0            ['2.40']             []                  
# | 19       0            2            []                   ['3.59', '3.71']    
# | 
# | POOL                 REMAPPED OSDs        BYTES REBALANCE      OBJECTS REBALANCE   
# | images               4                    22194159704          16683               
# | backups              4                    0                    0                   
# | rbd                  2                    0                    0                   
# | vms                  7                    124242257989         30054               
# | volumes              1                    8316252160           1997                
# | 
# |  total_movement_objects: 48734               
# |       data_balance_hour: 0.409954573984      
# |        data_balance_sec: 24.597274439        
# |    total_movement_bytes: 154752669853        
# |     total_remap_counter: 18                  
# |         bandwidth(Mbps): 100
# 

import ast
import json
import os
import subprocess
import argparse
import sys
import time


FNULL = open(os.devnull, 'w')


def get_max_osd(osdmap_file):
    args = ['osdmaptool', '--print', osdmap_file]
    print(' '.join(args))
    osd_map_info = subprocess.check_output(args, stderr=FNULL).split('\n')
    max_osd = 0
    for line in osd_map_info:
        if line.startswith('max_osd'):
            max_osd = line.split()[1]
            break
    return max_osd


def resize_max_osd(osdmap_file, new_max_osd):
    # original max_osd num
    original_max_osd = get_max_osd(osdmap_file)

    if original_max_osd < new_max_osd:
        args = ['osdmaptool', '--resize_max_osd', new_max_osd, osdmap_file]
        print(' '.join(args))
        subprocess.call(args, stdout=FNULL, stderr=subprocess.STDOUT)
    else:
        print('original_max_osd: %s, new_max_osd: %s' % (original_max_osd, new_max_osd))


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


def get_map_pgs_dump_info(map_pgs_dump):
    pg_data = {}
    pg_objects = {}
    pg_location = {}
    for line in map_pgs_dump:
        if line[0].isdigit():
            pg_id = line.split('\t')[0]
            osd_set = line.split('\t')[1].strip('[]').split(',')
            pg_location[pg_id] = osd_set
        elif line.startswith('#osd'):
            break

    return pg_location


def calc_osd_in_out_pgs(original_map_pgs_dump, new_map_pgs_dump):
    original_pgdump = get_map_pgs_dump_info(original_map_pgs_dump)
    new_pgdump = get_map_pgs_dump_info(new_map_pgs_dump)
    osd_counter = {}
    for pg_id in new_pgdump:
        o_pg_loc = original_pgdump[pg_id]
        n_pg_loc = new_pgdump[pg_id]
        for a,b in zip(o_pg_loc, n_pg_loc):
            if a == b:
                continue
            if not osd_counter.get(a, None):
                osd_counter[a] = {'out': 1, 'out_pg': [pg_id], 'in': 0, 'in_pg': []}
            else:
                osd_counter[a]['out'] += 1
                osd_counter[a]['out_pg'].append(pg_id)
            if not osd_counter.get(b, None):
                osd_counter[b] = {'out': 0, 'out_pg': [], 'in': 1, 'in_pg': [pg_id]}
            else:
                osd_counter[b]['in'] += 1
                osd_counter[b]['in_pg'].append(pg_id)
    return osd_counter


def calc_pg_remap(o_pg_loc, n_pg_loc):
    pg_remaps = []
    for o,n in zip(o_pg_loc, n_pg_loc):
        if o == n:
            continue
        pg_remaps.append("%s-->%s" % (o, n))
    return pg_remaps


# assume the osdmap test output is the same lenght and order...
# if add support for PG increase that's gonna break.
def diff_output(original_map_pgs_dump, new_map_pgs_dump, pools, original_pg_dump_file):
    """
    """
    results = {}

    pg_data, pg_objects = get_pg_info(original_pg_dump_file)

    print("")
    _remap_pg_num = 0
    _columns_four = "{0:<8} {1:<18} {2:<18} {3:<20}"
    print _columns_four.format("PG ID", "ORIGINAL OSD SET", "NEW OSD SET", "PG MIGRATION")
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
            if len(intersection) != 2:
                _remap_pg_num += 1
                pg_remaps = calc_pg_remap(original_mappings, new_mappings)
                print _columns_four.format(pg_id, original_mappings, new_mappings, pg_remaps)

            osd_movement_for_this_pg = int(pools[pool_id]['pool_size']) - len(intersection)
            osd_data_movement_for_this_pg = int(osd_movement_for_this_pg) * int(pg_data[pg_id])
            osd_object_movement_for_this_pg = int(osd_movement_for_this_pg) * int(pg_objects[pg_id])

            results[pool_name]['osd_remap_counter'] += osd_movement_for_this_pg
            results[pool_name]['osd_bytes_movement'] += int(osd_data_movement_for_this_pg)
            results[pool_name]['osd_objects_movement'] += int(osd_object_movement_for_this_pg)

        elif orig_i.startswith('#osd'):
            break
    print("Total Remap PG num: %s" % _remap_pg_num)
    print("")

    return results


def osdmaptool_test_map_pgs_dump1(osdmap_file):
    args = ['osdmaptool', '--test-map-pgs-dump', osdmap_file]
    print(' '.join(args))
    pgs_dump_info = subprocess.check_output(args, stderr=FNULL).split('\n')
    return pgs_dump_info


def osdmaptool_test_map_pgs_dump2(osdmap_file, new_osd_start_idx, new_osd_weight):
    args = ['osdmaptool', '--test-map-pgs-dump', osdmap_file]
    if new_osd_start_idx != -1:
        args += ['--mark-up-in', new_osd_start_idx, '--new-osd-weight', new_osd_weight]
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


def test_map_pgs_dump(original_osdmap_file, original_pg_dump_file, new_crushmap_file, new_max_osd,
                      new_osd_start_idx, new_osd_weight):
    """
    模拟ceph集群crushmap调整，对比前后pg map信息，计算数据迁移量
    """
    # original map pgs dump
    original_map_pgs_dump = osdmaptool_test_map_pgs_dump1(original_osdmap_file)

    # use new crushmap build new osdmap
    time_str = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    new_osdmap_file = "%s_%s" % (original_osdmap_file, time_str)
    copy_file(original_osdmap_file, new_osdmap_file)
    # resize max osd num
    resize_max_osd(new_osdmap_file, new_max_osd)
    # import new curshmap
    import_crushmap(new_osdmap_file, new_crushmap_file)

    # new pgs dump
    new_map_pgs_dump = osdmaptool_test_map_pgs_dump2(new_osdmap_file, new_osd_start_idx,
            new_osd_weight)

    # delete new osdmap file
    #os.remove(new_osdmap_file)

    # get pools info
    pools = get_pools_info(original_osdmap_file)

    # diff pgs dump info
    results = diff_output(original_map_pgs_dump, new_map_pgs_dump, pools, original_pg_dump_file)

    # calc osd in/out pgs
    osd_counter = calc_osd_in_out_pgs(original_map_pgs_dump, new_map_pgs_dump)

    return results, osd_counter


def calc_data_balance_time(results, bandwidth):
    total_remap_counter = 0
    total_movement_bytes = 0
    total_movement_objects = 0
    for pool in results:
        total_remap_counter += results[pool]['osd_remap_counter']
        total_movement_bytes += results[pool]['osd_bytes_movement']
        total_movement_objects += results[pool]['osd_objects_movement']
    data_balance_sec = 1.0 * total_movement_bytes / (bandwidth * 1024 * 1024) / 60
    data_balance_hour = data_balance_sec / 60

    return {'total_remap_counter': total_remap_counter,
            'total_movement_objects': total_movement_objects,
            'total_movement_bytes': total_movement_bytes,
            'bandwidth(Mbps)': bandwidth,
            'data_balance_sec': data_balance_sec,
            'data_balance_hour': data_balance_hour}


def dump_plain_output(results, osd_counter, statistics):
    """
    输出结果
    """
    sys.stdout.write("%-8s %-12s %-12s %-20s %-20s\n" % ("OSD_ID", "IN_PGS_NUM", "OUT_PGS_NUM", "IN_PGS", "OUT_PGS"))
    for osd in sorted(osd_counter.keys()):
        sys.stdout.write("%-8s %-12s %-12s %-20s %-20s\n" % (osd, osd_counter[osd]['in'], \
            osd_counter[osd]['out'], osd_counter[osd]['in_pg'], osd_counter[osd]['out_pg']))
    sys.stdout.write("\n")

    sys.stdout.write("%-20s %-20s %-20s %-20s\n" % ("POOL", "REMAPPED OSDs", "BYTES REBALANCE", "OBJECTS REBALANCE"))
    for pool in results:
        sys.stdout.write("%-20s %-20s %-20s %-20s\n" % (pool,
                                                        results[pool]['osd_remap_counter'],
                                                        results[pool]['osd_bytes_movement'],
                                                        results[pool]['osd_objects_movement']
                                                        )
                        )
    sys.stdout.write("\n")

    for key in statistics:
        sys.stdout.write("%23s: %-20s\n" % (key, statistics[key]))
    sys.stdout.write("\n")


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
        '--new-max-osd',
        help="Ceph cluster new max osd num.",
        default=0,
        dest="new_max_osd"
        )
    parser.add_argument(
        '--new-osd-weight',
        help="Ceph cluster new osd weight.",
        default=1.0,
        dest="new_osd_weight"
        )
    parser.add_argument(
        '--new-osd-start-idx',
        help="Ceph cluster new osd start idx.",
        default=-1,
        dest="new_osd_start_idx"
        )
    parser.add_argument(
        '--bandwidth',
        help="Ceph cluster data migration bandwidth (Mbps).",
        default=100,
        type=int,
        dest="bandwidth"
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

    results, osd_counter = test_map_pgs_dump(ctx.osdmap_file, ctx.pgdump_file, ctx.new_crushmap,
            ctx.new_max_osd, ctx.new_osd_start_idx, ctx.new_osd_weight)
    statistics = calc_data_balance_time(results, ctx.bandwidth)

    FNULL.close()

    if ctx.format == 'json':
        print json.dumps(results)
        print json.dumps(osd_counter)
        print json.dumps(statistics)
    elif ctx.format == 'plain':
        dump_plain_output(results, osd_counter, statistics)

