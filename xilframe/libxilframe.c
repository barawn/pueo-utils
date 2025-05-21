// xilframe P.S. Allison <allison.122@osu.edu> 11/25/24
//
// process framesets into data
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>

void xilframe(uint8_t *src, uint8_t *dst);
void xilprocess(uint8_t *src, uint8_t *dst);

#define FRAME_SIZE 93*4
// 95704 bytes
// 23926 int32s
// 118 dummy words + 256*(frames of 93 uint32 words)
#define FULL_SIZE (118*4+256*FRAME_SIZE)
// each BRAM is 36 kbit but we only use 32 kbit = 4096
// the size is actually 256 frames of 16 bytes
#define BRAM_SIZE_PER_FRAME (16)
#define NUM_FRAME (256)
#define BRAM_SIZE ((BRAM_SIZE_PER_FRAME)*(NUM_FRAME))
// and we have 12 of 'em
#define NUM_BRAM (12)
#define DATA_SIZE ((NUM_BRAM)*(BRAM_SIZE))

void xilframe(uint8_t *src, uint8_t *dst) {
  uint8_t *s;
  uint8_t *d;
  uint8_t *fp;
  int frame_offsets[] = {
    0,
    30,
    60,
    90,
    120,
    150,
    192,
    222,
    252,
    282,
    312,
    342
  };
// BRAM0: bit 0 (byte offset 0)
// BRAM1: bit 240 (byte offset 30)
// BRAM2: bit 480 (byte offset 60)
// BRAM3: bit 720 (byte offset 90)
// BRAM4: bit 960 (byte offset 120)
// BRAM5: bit 1200 (byte offset 150)
// BRAM6: bit 1536 (byte offset 192)
// BRAM7: bit 1776 (byte offset 222)
// BRAM8: bit 2016 (byte offset 252)
// BRAM9: bit 2256 (byte offset 282)
// BRAM10: bit 2496 (byte offset 312)
// BRAM11: bit 2736 (byte offset 342)
  s = src;
  d = dst;
  fp = s + 118*4;
  // fp now points to the frames
  // to access a specific frame, it's just
  // fp[frameno*FRAME_SIZE]
  // to access a specific BRAM it's
  // fp[frameno*FRAME_SIZE+frame_offsets[bram]]
  // so to rearrange, we write
  // xilprocess(s[frameno*FRAME_SIZE+frame_offsets[bram]],
  //            d[16*frameno + bram*BRAM_SIZE]);
  for (int bram=0;bram<NUM_BRAM;bram++) {
    for (int frame=0;frame<NUM_FRAME;frame++) {	  
      xilprocess(&fp[frame*FRAME_SIZE+frame_offsets[bram]],
		 &d[BRAM_SIZE_PER_FRAME*frame + bram*BRAM_SIZE]);
    }
  }
}


// extract 128 bits from 2976 bits
// this only generates 16 bytes of data for each BRAM,
// but each BRAM in the same clock region also has
// data stored there as well. they're offset by byte
// multiples:
// so overall you get 1536 bits from 2976 bits
//
void xilprocess(uint8_t *src, uint8_t *dst) {
  uint8_t *r = dst;
  uint8_t *f = src;

  // EQUATE THE FIRST BIT, DON'T SET
  r[ 0 ] = ((f[ 30 - 30 ] >>  0 )&0x1) <<  0;

  r[ 0 ] |= ((f[ 46 - 30 ] >>  4 )&0x1) <<  1;
  r[ 0 ] |= ((f[ 31 - 30 ] >>  4 )&0x1) <<  2;
  r[ 0 ] |= ((f[ 48 - 30 ] >>  0 )&0x1) <<  3;
  r[ 0 ] |= ((f[ 33 - 30 ] >>  0 )&0x1) <<  4;
  r[ 0 ] |= ((f[ 49 - 30 ] >>  4 )&0x1) <<  5;
  r[ 0 ] |= ((f[ 34 - 30 ] >>  4 )&0x1) <<  6;
  r[ 0 ] |= ((f[ 51 - 30 ] >>  0 )&0x1) <<  7;  

  r[ 1 ] = ((f[ 37 - 30 ] >>  4 )&0x1) <<  0;

  r[ 1 ] |= ((f[ 54 - 30 ] >>  0 )&0x1) <<  1;
  r[ 1 ] |= ((f[ 39 - 30 ] >>  0 )&0x1) <<  2;
  r[ 1 ] |= ((f[ 55 - 30 ] >>  4 )&0x1) <<  3;
  r[ 1 ] |= ((f[ 40 - 30 ] >>  4 )&0x1) <<  4;
  r[ 1 ] |= ((f[ 57 - 30 ] >>  0 )&0x1) <<  5;
  r[ 1 ] |= ((f[ 42 - 30 ] >>  0 )&0x1) <<  6;
  r[ 1 ] |= ((f[ 58 - 30 ] >>  4 )&0x1) <<  7;

  r[ 2 ] = ((f[ 30 - 30 ] >>  6 )&0x1) <<  0;

  r[ 2 ] |= ((f[ 47 - 30 ] >>  2 )&0x1) <<  1;
  r[ 2 ] |= ((f[ 32 - 30 ] >>  2 )&0x1) <<  2;
  r[ 2 ] |= ((f[ 48 - 30 ] >>  6 )&0x1) <<  3;
  r[ 2 ] |= ((f[ 33 - 30 ] >>  6 )&0x1) <<  4;
  r[ 2 ] |= ((f[ 50 - 30 ] >>  2 )&0x1) <<  5;
  r[ 2 ] |= ((f[ 35 - 30 ] >>  2 )&0x1) <<  6;
  r[ 2 ] |= ((f[ 51 - 30 ] >>  6 )&0x1) <<  7;

  r[ 3 ] = ((f[ 38 - 30 ] >>  2 )&0x1) <<  0;

  r[ 3 ] |= ((f[ 54 - 30 ] >>  6 )&0x1) <<  1;
  r[ 3 ] |= ((f[ 39 - 30 ] >>  6 )&0x1) <<  2;
  r[ 3 ] |= ((f[ 56 - 30 ] >>  2 )&0x1) <<  3;
  r[ 3 ] |= ((f[ 41 - 30 ] >>  2 )&0x1) <<  4;
  r[ 3 ] |= ((f[ 57 - 30 ] >>  6 )&0x1) <<  5;
  r[ 3 ] |= ((f[ 42 - 30 ] >>  6 )&0x1) <<  6;
  r[ 3 ] |= ((f[ 59 - 30 ] >>  2 )&0x1) <<  7;

  r[ 4 ] = ((f[ 30 - 30 ] >>  3 )&0x1) <<  0;

  r[ 4 ] |= ((f[ 46 - 30 ] >>  7 )&0x1) <<  1;
  r[ 4 ] |= ((f[ 31 - 30 ] >>  7 )&0x1) <<  2;
  r[ 4 ] |= ((f[ 48 - 30 ] >>  3 )&0x1) <<  3;
  r[ 4 ] |= ((f[ 33 - 30 ] >>  3 )&0x1) <<  4;
  r[ 4 ] |= ((f[ 49 - 30 ] >>  7 )&0x1) <<  5;
  r[ 4 ] |= ((f[ 34 - 30 ] >>  7 )&0x1) <<  6;
  r[ 4 ] |= ((f[ 51 - 30 ] >>  3 )&0x1) <<  7;

  r[ 5 ] = ((f[ 37 - 30 ] >>  7 )&0x1) <<  0;

  r[ 5 ] |= ((f[ 54 - 30 ] >>  3 )&0x1) <<  1;
  r[ 5 ] |= ((f[ 39 - 30 ] >>  3 )&0x1) <<  2;
  r[ 5 ] |= ((f[ 55 - 30 ] >>  7 )&0x1) <<  3;
  r[ 5 ] |= ((f[ 40 - 30 ] >>  7 )&0x1) <<  4;
  r[ 5 ] |= ((f[ 57 - 30 ] >>  3 )&0x1) <<  5;
  r[ 5 ] |= ((f[ 42 - 30 ] >>  3 )&0x1) <<  6;
  r[ 5 ] |= ((f[ 58 - 30 ] >>  7 )&0x1) <<  7;

  r[ 6 ] = ((f[ 31 - 30 ] >>  1 )&0x1) <<  0;

  r[ 6 ] |= ((f[ 47 - 30 ] >>  5 )&0x1) <<  1;
  r[ 6 ] |= ((f[ 32 - 30 ] >>  5 )&0x1) <<  2;
  r[ 6 ] |= ((f[ 49 - 30 ] >>  1 )&0x1) <<  3;
  r[ 6 ] |= ((f[ 34 - 30 ] >>  1 )&0x1) <<  4;
  r[ 6 ] |= ((f[ 50 - 30 ] >>  5 )&0x1) <<  5;
  r[ 6 ] |= ((f[ 35 - 30 ] >>  5 )&0x1) <<  6;
  r[ 6 ] |= ((f[ 52 - 30 ] >>  1 )&0x1) <<  7;

  r[ 7 ] = ((f[ 38 - 30 ] >>  5 )&0x1) <<  0;

  r[ 7 ] |= ((f[ 55 - 30 ] >>  1 )&0x1) <<  1;
  r[ 7 ] |= ((f[ 40 - 30 ] >>  1 )&0x1) <<  2;
  r[ 7 ] |= ((f[ 56 - 30 ] >>  5 )&0x1) <<  3;
  r[ 7 ] |= ((f[ 41 - 30 ] >>  5 )&0x1) <<  4;
  r[ 7 ] |= ((f[ 58 - 30 ] >>  1 )&0x1) <<  5;
  r[ 7 ] |= ((f[ 43 - 30 ] >>  1 )&0x1) <<  6;
  r[ 7 ] |= ((f[ 59 - 30 ] >>  5 )&0x1) <<  7;

  r[ 8 ] = ((f[ 30 - 30 ] >>  2 )&0x1) <<  0;

  r[ 8 ] |= ((f[ 46 - 30 ] >>  6 )&0x1) <<  1;
  r[ 8 ] |= ((f[ 31 - 30 ] >>  6 )&0x1) <<  2;
  r[ 8 ] |= ((f[ 48 - 30 ] >>  2 )&0x1) <<  3;
  r[ 8 ] |= ((f[ 33 - 30 ] >>  2 )&0x1) <<  4;
  r[ 8 ] |= ((f[ 49 - 30 ] >>  6 )&0x1) <<  5;
  r[ 8 ] |= ((f[ 34 - 30 ] >>  6 )&0x1) <<  6;
  r[ 8 ] |= ((f[ 51 - 30 ] >>  2 )&0x1) <<  7;

  r[ 9 ] = ((f[ 37 - 30 ] >>  6 )&0x1) <<  0;

  r[ 9 ] |= ((f[ 54 - 30 ] >>  2 )&0x1) <<  1;
  r[ 9 ] |= ((f[ 39 - 30 ] >>  2 )&0x1) <<  2;
  r[ 9 ] |= ((f[ 55 - 30 ] >>  6 )&0x1) <<  3;
  r[ 9 ] |= ((f[ 40 - 30 ] >>  6 )&0x1) <<  4;
  r[ 9 ] |= ((f[ 57 - 30 ] >>  2 )&0x1) <<  5;
  r[ 9 ] |= ((f[ 42 - 30 ] >>  2 )&0x1) <<  6;
  r[ 9 ] |= ((f[ 58 - 30 ] >>  6 )&0x1) <<  7;

  r[ 10 ] = ((f[ 31 - 30 ] >>  0 )&0x1) <<  0;

  r[ 10 ] |= ((f[ 47 - 30 ] >>  4 )&0x1) <<  1;
  r[ 10 ] |= ((f[ 32 - 30 ] >>  4 )&0x1) <<  2;
  r[ 10 ] |= ((f[ 49 - 30 ] >>  0 )&0x1) <<  3;
  r[ 10 ] |= ((f[ 34 - 30 ] >>  0 )&0x1) <<  4;
  r[ 10 ] |= ((f[ 50 - 30 ] >>  4 )&0x1) <<  5;
  r[ 10 ] |= ((f[ 35 - 30 ] >>  4 )&0x1) <<  6;
  r[ 10 ] |= ((f[ 52 - 30 ] >>  0 )&0x1) <<  7;

  r[ 11 ] = ((f[ 38 - 30 ] >>  4 )&0x1) <<  0;

  r[ 11 ] |= ((f[ 55 - 30 ] >>  0 )&0x1) <<  1;
  r[ 11 ] |= ((f[ 40 - 30 ] >>  0 )&0x1) <<  2;
  r[ 11 ] |= ((f[ 56 - 30 ] >>  4 )&0x1) <<  3;
  r[ 11 ] |= ((f[ 41 - 30 ] >>  4 )&0x1) <<  4;
  r[ 11 ] |= ((f[ 58 - 30 ] >>  0 )&0x1) <<  5;
  r[ 11 ] |= ((f[ 43 - 30 ] >>  0 )&0x1) <<  6;
  r[ 11 ] |= ((f[ 59 - 30 ] >>  4 )&0x1) <<  7;

  r[ 12 ] = ((f[ 30 - 30 ] >>  5 )&0x1) <<  0;

  r[ 12 ] |= ((f[ 47 - 30 ] >>  1 )&0x1) <<  1;
  r[ 12 ] |= ((f[ 32 - 30 ] >>  1 )&0x1) <<  2;
  r[ 12 ] |= ((f[ 48 - 30 ] >>  5 )&0x1) <<  3;
  r[ 12 ] |= ((f[ 33 - 30 ] >>  5 )&0x1) <<  4;
  r[ 12 ] |= ((f[ 50 - 30 ] >>  1 )&0x1) <<  5;
  r[ 12 ] |= ((f[ 35 - 30 ] >>  1 )&0x1) <<  6;
  r[ 12 ] |= ((f[ 51 - 30 ] >>  5 )&0x1) <<  7;

  r[ 13 ] = ((f[ 38 - 30 ] >>  1 )&0x1) <<  0;

  r[ 13 ] |= ((f[ 54 - 30 ] >>  5 )&0x1) <<  1;
  r[ 13 ] |= ((f[ 39 - 30 ] >>  5 )&0x1) <<  2;
  r[ 13 ] |= ((f[ 56 - 30 ] >>  1 )&0x1) <<  3;
  r[ 13 ] |= ((f[ 41 - 30 ] >>  1 )&0x1) <<  4;
  r[ 13 ] |= ((f[ 57 - 30 ] >>  5 )&0x1) <<  5;
  r[ 13 ] |= ((f[ 42 - 30 ] >>  5 )&0x1) <<  6;
  r[ 13 ] |= ((f[ 59 - 30 ] >>  1 )&0x1) <<  7;

  r[ 14 ] = ((f[ 31 - 30 ] >>  3 )&0x1) <<  0;

  r[ 14 ] |= ((f[ 47 - 30 ] >>  7 )&0x1) <<  1;
  r[ 14 ] |= ((f[ 32 - 30 ] >>  7 )&0x1) <<  2;
  r[ 14 ] |= ((f[ 49 - 30 ] >>  3 )&0x1) <<  3;
  r[ 14 ] |= ((f[ 34 - 30 ] >>  3 )&0x1) <<  4;
  r[ 14 ] |= ((f[ 50 - 30 ] >>  7 )&0x1) <<  5;
  r[ 14 ] |= ((f[ 35 - 30 ] >>  7 )&0x1) <<  6;
  r[ 14 ] |= ((f[ 52 - 30 ] >>  3 )&0x1) <<  7;

  r[ 15 ] = ((f[ 38 - 30 ] >>  7 )&0x1) <<  0;

  r[ 15 ] |= ((f[ 55 - 30 ] >>  3 )&0x1) <<  1;
  r[ 15 ] |= ((f[ 40 - 30 ] >>  3 )&0x1) <<  2;
  r[ 15 ] |= ((f[ 56 - 30 ] >>  7 )&0x1) <<  3;
  r[ 15 ] |= ((f[ 41 - 30 ] >>  7 )&0x1) <<  4;
  r[ 15 ] |= ((f[ 58 - 30 ] >>  3 )&0x1) <<  5;
  r[ 15 ] |= ((f[ 43 - 30 ] >>  3 )&0x1) <<  6;
  r[ 15 ] |= ((f[ 59 - 30 ] >>  7 )&0x1) <<  7;        
}
