/*
 Copyright 2024 Google LLC

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
#ifndef MIDEND_EXTRACTANDLOOKAHEADCONVERSION_H_
#define MIDEND_EXTRACTANDLOOKAHEADCONVERSION_H_

// Given an assignment like
// state foo {
//   packet.extract(hdrs.ethernet); // 112 bits long
//   x = packet.lookahead(bit<8>);  // 8 bits long
//   packet.extract(hdrs.ipv4, x);  // 160+x bits long
//   transition accept;
// }

// this is transformed into
// state foo {
//   ExtractHeader "hdrs.ethernet" packet[0:111]
//   x = packet[112:119]
//   ExtactHeader "hdrs.ipv4" packet[112:271+x]
//   Move 272+x
//   transition accept;
// }
// ...
//

#include "frontends/common/resolveReferences/referenceMap.h"
#include "frontends/p4/typeChecking/typeChecker.h"
#include "frontends/p4/typeMap.h"
#include "ir/ir.h"


namespace P4 {

class DoExtractandLookaheadConversion : public Transform {
    P4::ReferenceMap *refMap;
    P4::TypeMap *typeMap;
    public:
        DoExtractandLookaheadConversion(ReferenceMap *refMap, TypeMap *typeMap)
        : refMap(refMap), typeMap(typeMap){
            std::cout << "DoExtractandLookaheadConversion pass" << std::endl;
            CHECK_NULL(refMap);
            CHECK_NULL(typeMap);
            setName("DoExtractandLookaheadConversion");
        }
        const IR::Node *postorder(IR::P4Parser *parser) override;

};

class ExtractandLookaheadConversion : public PassManager {
    public:
        ExtractandLookaheadConversion(ReferenceMap *refMap, TypeMap *typeMap, TypeChecking *typeChecking = nullptr) {
            std::cout << "ExtractandLookaheadConversion pass" << std::endl;
            if (!typeChecking) typeChecking = new TypeChecking(refMap, typeMap);
            passes.push_back(typeChecking);
            passes.push_back(new DoExtractandLookaheadConversion(refMap, typeMap));
            setName("ExtractandLookaheadConversion");
        }

};

}

#endif