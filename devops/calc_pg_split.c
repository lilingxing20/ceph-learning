/*
 * [root@node244 ~]# gcc -std=c99 calc_pg_split.c -o calc_pg_split
 * [root@node244 ~]# ./calc_pg_split 6 12 1
 * pool: 1, old pg num: 6, new pg num: 12
 * ---------------------------
 *  | parent_pg | children_pg |
 *  ---------------------------
 *  |       1.0 |        1.8 |
 *  |       1.1 |        1.9 |
 *  |       1.2 |        1.6 |
 *  |       1.2 |        1.a |
 *  |       1.3 |        1.7 |
 *  |       1.3 |        1.b |
 *  ---------------------------
 *  pool: 1, will be split pg number: 4, new create pg number: 6
 *
 */

#include <stdio.h>
#include <stdlib.h>

// need use -std=c99
#include <stdbool.h>
//#include <stdint.h>


// without c99 need following two lines
// #define true 1
// #define false 0


static int calc_bits_of(int t)
{
    int b = 0;
    while (t > 0) {
        t = t >> 1;
        ++b;
    }
    return b;
}


static inline int ceph_stable_mod(int x, int b, int bmask)
{
    if ((x & bmask) < b)
        return x & bmask;
    else
        return x & (bmask >> 1);
}


int is_split(unsigned int pool_id, unsigned int old_pg_num, unsigned int new_pg_num, int m_seed)
{
    if (m_seed >= old_pg_num)
        return false;
    if (new_pg_num <= old_pg_num)
        return false;

    int child_pg_num = 0;
    if (true) {
        int old_bits = calc_bits_of(old_pg_num);
        int old_mask = (1 << old_bits) - 1;
        for (int n=1; ; n++)
        {
            int next_bit = (n << (old_bits-1));
            unsigned int s = next_bit | m_seed;

            if (s < old_pg_num || s == m_seed)
                continue;
            if (s >= new_pg_num)
                break;
            if ((unsigned int)ceph_stable_mod(s, old_pg_num, old_mask) == m_seed)
            {
                child_pg_num ++;
                printf("| %7x.%x |\t%6x.%x |\n", pool_id, m_seed, pool_id, s);
            }
        }
    }
    return child_pg_num;
}


void calc_pg_split(unsigned int pool_id, unsigned int old_pg_num, unsigned int new_pg_num)
{
    int split_pg_num = 0;
    int create_pg_num = 0;

    printf("---------------------------\n");
    printf("| parent_pg | children_pg |\n");
    printf("---------------------------\n");
    for(int i=0; i<=old_pg_num-1; i++)
    {
        int ret = is_split(pool_id, old_pg_num, new_pg_num, i);
        if (ret > 0)
        {
            split_pg_num ++;
            create_pg_num += ret;
        }
    }
    printf("---------------------------\n");
    printf("pool: %d, will be split pg number: %d, new create pg number: %d\n", pool_id, split_pg_num, create_pg_num);
}


int main(int argc, char ** argv)
{
    int pool_id = 0;
    int old_pg_num = 16;
    int new_pg_num = 32;

    switch (argc) {
    case 1:
        printf("\n%s: <pool old pg num> <pool new pg num> [<pool id>]\n\n", argv[0]);
        break;
    case 3:
        old_pg_num = atoi(argv[1]);
        new_pg_num = atoi(argv[2]);
        printf("pool: %d, old pg num: %d, new pg num: %d\n", pool_id, old_pg_num, new_pg_num);
        calc_pg_split(pool_id, old_pg_num, new_pg_num);
        break;
    case 4:
        old_pg_num = atoi(argv[1]);
        new_pg_num = atoi(argv[2]);
        pool_id = atoi(argv[3]);
        printf("pool: %d, old pg num: %d, new pg num: %d\n", pool_id, old_pg_num, new_pg_num);
        calc_pg_split(pool_id, old_pg_num, new_pg_num);
        break;
    default:
        printf("Parameter error !\n");
    }
    return 0;
}

