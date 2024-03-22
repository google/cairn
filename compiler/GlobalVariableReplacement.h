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

#ifndef MIDEND_GLOBALVARIABLEREPLACEMENT_H_
#define MIDEND_GLOBALVARIABLEREPLACEMENT_H_

/// Given an assignment like
/// state foo {
/// packet.extract(hdr.eth, (bit<32>)x); // x is an 32-bit global. This uses the original value of x
/// x = packet.lookahead<bit<8>>();
/// packet.extract(hdr.eth, (bit<32>)x); // This uses the new value of x
/// transition accept;
/// }
/// this is transformed into
/// state foo { 
/// packet.extract(hdr1, (bit<32>)x); // x is an 8-bit global. This uses the original value of x 
/// x_new = packet.lookahead<bit<8>>();
/// packet.extract(hdr2, (bit<32>)x_new); // This uses the new value of x 
/// x = x_new;
/// transition accept; }
/// ...
///

#include "frontends/common/resolveReferences/referenceMap.h"
#include "frontends/p4/typeChecking/typeChecker.h"
#include "frontends/p4/typeMap.h"
#include "ir/ir.h"


namespace P4 {

// key: parser state name
typedef std::map<cstring, std::map<cstring, std::vector<int>>> map_var_to_pos_appear;
typedef std::map<cstring, std::map<cstring, int>> map_replace_width_mp;

class FindReadWriteVariable final : public Inspector {
    ReferenceMap *refMap;
    TypeMap *typeMap;
    map_var_to_pos_appear* read_mp;
    map_var_to_pos_appear* write_mp;
    map_replace_width_mp* replace_width_mp;

    bool preorder(const IR::P4Parser *parser) override;

 public:
    FindReadWriteVariable(
        ReferenceMap *refMap, TypeMap *typeMap, map_var_to_pos_appear* read_mp, 
        map_var_to_pos_appear* write_mp, map_replace_width_mp* replace_width_mp)
        : refMap(refMap),
          typeMap(typeMap),
          read_mp(read_mp),
          write_mp(write_mp),
          replace_width_mp(replace_width_mp) {}
};

class DoGlobalVariableReplacement : public Transform {
    P4::ReferenceMap *refMap;
    P4::TypeMap *typeMap;
    map_var_to_pos_appear* read_mp;
    map_var_to_pos_appear* write_mp;
    map_replace_width_mp* replace_width_mp;
    public:
        DoGlobalVariableReplacement(ReferenceMap *refMap, TypeMap *typeMap,
        map_var_to_pos_appear* read_mp, map_var_to_pos_appear* write_mp, 
        map_replace_width_mp* replace_width_mp)
        : refMap(refMap), typeMap(typeMap), read_mp(read_mp), write_mp(write_mp), replace_width_mp(replace_width_mp){
            CHECK_NULL(refMap);
            CHECK_NULL(typeMap);
            setName("DoGlobalVariableReplacement");
        }
        const IR::Node *postorder(IR::P4Parser *parser) override;

};

class GlobalVariableReplacement : public PassManager {
    public:
        GlobalVariableReplacement(ReferenceMap *refMap, TypeMap *typeMap, TypeChecking *typeChecking = nullptr) {
            std::cout << "GlobalVariableReplacement pass" << std::endl;
            if (!typeChecking) typeChecking = new TypeChecking(refMap, typeMap);
            passes.push_back(typeChecking);
            auto read_mp = new map_var_to_pos_appear;
            auto write_mp = new map_var_to_pos_appear;
            auto replace_width_mp = new map_replace_width_mp;

            passes.push_back(new FindReadWriteVariable(refMap, typeMap, read_mp, write_mp, replace_width_mp));
            passes.push_back(new DoGlobalVariableReplacement(refMap, typeMap, read_mp, write_mp, replace_width_mp));
            setName("GlobalVariableReplacement");
        }

};

}

#endif