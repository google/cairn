#ifndef CAIRN_MIDEND_H_
#define CAIRN_MIDEND_H_

#include "frontends/common/resolveReferences/referenceMap.h"
#include "frontends/p4/typeMap.h"
#include "ir/pass_manager.h"
#include "midend/expandLookahead.h"
#include "midend/midEndLast.h"

namespace cairn {

class MidEnd : public PassManager {
  ::P4::ReferenceMap ref_map_;
  ::P4::TypeMap type_map_;

 public:
  explicit MidEnd() {
    // Set internal name explicitly. Otherwise the pass dump file will use the
    // fully qualified class name namespace::to::MidEnd.
    internalName = "MidEnd";

    addPasses({
        new ::P4::ExpandLookahead(&ref_map_, &type_map_),
        new ::P4::MidEndLast(),
    });
  }
};

}  // namespace cairn

#endif  // CAIRN_MIDEND_H_
