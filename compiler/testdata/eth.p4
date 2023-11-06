#include <core.p4>

header eth_h {
    bit<48> dst_addr;
    bit<48> src_addr;
    bit<16> ether_type;
}

struct header_t {
    eth_h eth;
}

struct metadata_t {}

parser TestParser(
    packet_in pkt,
    out header_t hdr,
    inout metadata_t meta
) {
    state start {
        pkt.extract(hdr.eth);
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
