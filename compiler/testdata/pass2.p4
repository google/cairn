/*
 Copyright 2023 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

#include <core.p4>

header eth_h {
    bit<48> dst_addr;
    bit<48> src_addr;
    bit<16> ether_type;
}

header ipv4_h {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
    varbit<256>    var;
}

struct header_t {
    eth_h eth;
    ipv4_h ipv4;
}

struct metadata_t {}

parser TestParser(
    packet_in pkt,
    out header_t hdr,
    inout metadata_t meta
) {
    bit<32> x;
    state start {
        pkt.extract(hdr.eth); // 112 bits long
        x = pkt.lookahead<bit<32>>();  // 32 bits long
        pkt.extract(hdr.ipv4, x);  // 160+x bits long
        transition accept;
    }
}

// Construct the package.
parser Parser<H, M>(
  packet_in pkt,
  out H hdr,
  inout M meta
);
package Package<H, M>(
  Parser<H, M> p
);
Package(TestParser()) main;
