#include <stdio.h>
#include <linux/types.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h> 

#define CEPH_STR_HASH_LINUX      0x1  /* linux dcache hash */
#define CEPH_STR_HASH_RJENKINS   0x2  /* robert jenkins' */
/*
 * Robert Jenkin's hash function.
 * http://burtleburtle.net/bob/hash/evahash.html
 * This is in the public domain.
 */
#define mix(a, b, c)						\
	do {							\
		a = a - b;  a = a - c;  a = a ^ (c >> 13);	\
		b = b - c;  b = b - a;  b = b ^ (a << 8);	\
		c = c - a;  c = c - b;  c = c ^ (b >> 13);	\
		a = a - b;  a = a - c;  a = a ^ (c >> 12);	\
		b = b - c;  b = b - a;  b = b ^ (a << 16);	\
		c = c - a;  c = c - b;  c = c ^ (b >> 5);	\
		a = a - b;  a = a - c;  a = a ^ (c >> 3);	\
		b = b - c;  b = b - a;  b = b ^ (a << 10);	\
		c = c - a;  c = c - b;  c = c ^ (b >> 15);	\
	} while (0)

unsigned ceph_str_hash_rjenkins(const char *str, unsigned length)
{
	const unsigned char *k = (const unsigned char *)str;
	__u32 a, b, c;  /* the internal state */
	__u32 len;      /* how many key bytes still need mixing */

	/* Set up the internal state */
	len = length;
	a = 0x9e3779b9;      /* the golden ratio; an arbitrary value */
	b = a;
	c = 0;               /* variable initialization of internal state */

	/* handle most of the key */
	while (len >= 12) {
		a = a + (k[0] + ((__u32)k[1] << 8) + ((__u32)k[2] << 16) +
			 ((__u32)k[3] << 24));
		b = b + (k[4] + ((__u32)k[5] << 8) + ((__u32)k[6] << 16) +
			 ((__u32)k[7] << 24));
		c = c + (k[8] + ((__u32)k[9] << 8) + ((__u32)k[10] << 16) +
			 ((__u32)k[11] << 24));
		mix(a, b, c);
		k = k + 12;
		len = len - 12;
	}

	/* handle the last 11 bytes */
	c = c + length;
	switch (len) {            /* all the case statements fall through */
	case 11:
		c = c + ((__u32)k[10] << 24);
	case 10:
		c = c + ((__u32)k[9] << 16);
	case 9:
		c = c + ((__u32)k[8] << 8);
		/* the first byte of c is reserved for the length */
	case 8:
		b = b + ((__u32)k[7] << 24);
	case 7:
		b = b + ((__u32)k[6] << 16);
	case 6:
		b = b + ((__u32)k[5] << 8);
	case 5:
		b = b + k[4];
	case 4:
		a = a + ((__u32)k[3] << 24);
	case 3:
		a = a + ((__u32)k[2] << 16);
	case 2:
		a = a + ((__u32)k[1] << 8);
	case 1:
		a = a + k[0];
		/* case 0: nothing left to add */
	}
	mix(a, b, c);

	return c;
}

/*
 * linux dcache hash
 */
unsigned ceph_str_hash_linux(const char *str, unsigned length)
{
	unsigned hash = 0;

	while (length--) {
		unsigned char c = *str++;
		hash = (hash + (c << 4) + (c >> 4)) * 11;
	}
	return hash;
}


unsigned ceph_str_hash(int type, const char *s, unsigned len)
{
	switch (type) {
	case CEPH_STR_HASH_LINUX:
		return ceph_str_hash_linux(s, len);
	case CEPH_STR_HASH_RJENKINS:
		return ceph_str_hash_rjenkins(s, len);
	default:
		return -1;
	}
}

const char *ceph_str_hash_name(int type)
{
	switch (type) {
	case CEPH_STR_HASH_LINUX:
		return "linux";
	case CEPH_STR_HASH_RJENKINS:
		return "rjenkins";
	default:
		return "unknown";
	}
}

bool ceph_str_hash_valid(int type)
{
        switch (type) {
        case CEPH_STR_HASH_LINUX:
        case CEPH_STR_HASH_RJENKINS:
                return true;
        default:
                return false;
        }
}

int calc_bits_of(int t)
{
  int b = 0; 
  while (t > 0) { 
    t = t >> 1;
    ++b; 
  }
  return b;
}

int calc_pg_masks(int pg_num)
{
  return (1 << calc_bits_of(pg_num-1)) - 1; 
}

/*
 * stable_mod func is used to control number of placement groups.
 * similar to straight-up modulo, but produces a stable mapping as b
 * increases over time.  b is the number of bins, and bmask is the
 * containing power of 2 minus 1.
 *
 * b <= bmask and bmask=(2**n)-1
 * e.g., b=12 -> bmask=15, b=123 -> bmask=127
 */
static inline int ceph_stable_mod(int x, int b, int bmask)
{
    if ((x & bmask) < b)
        return x & bmask;
    else
        return x & (bmask >> 1); 
}


int main (int argc, char * argv[])
{
    unsigned length = 0;
    const char *obj_name = NULL;
    unsigned hash_value = 0;
    unsigned pg_num = 0;
    unsigned pg_m_seek = 0;
    switch (argc) {
    case 2:
        obj_name = argv[1];
        length = strlen(obj_name);
        hash_value = ceph_str_hash_rjenkins(obj_name, length);
        printf("0x%x", hash_value);
        break;
    case 3:
        obj_name = argv[1];
        pg_num = atoi(argv[2]);
        length = strlen(obj_name);
        hash_value = ceph_str_hash_rjenkins(obj_name, length);
        pg_m_seek = ceph_stable_mod(hash_value, pg_num, calc_pg_masks(pg_num));
        printf("0x%x 0x%x", hash_value, pg_m_seek);
        break;
    }

    // const char *str = "bar";
    // unsigned length = strlen(str);
	// unsigned ret;
    // ret = ceph_str_hash_rjenkins(str, length);
    // printf("str=%s\n", str);
    // printf("str len=%d\n", length);
    // printf("ret=%ld\n", ret);
    return 0;
}

