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
#include "ExtractandLookaheadConversion.h"

#include "ir/pass_manager.h"

#include <typeinfo>
#include <assert.h>
#include <string>

namespace P4 {
namespace {


class ImplExtractLookahead : public Transform {
    ReferenceMap *refMap;
    TypeMap *typeMap;
    int global_pos;
    std::string varbit_v;

public:
    explicit ImplExtractLookahead(ReferenceMap *refMap, TypeMap *typeMap)
    : refMap(refMap), typeMap(typeMap) {
        global_pos = 0;
        varbit_v = "";
        setName("ImplExtractLookahead");
    }

    const IR::Node *preorder(IR::Declaration_Variable *dec) override {
        return dec;
    }
    const IR::Node *preorder(IR::AssignmentStatement *assn_stmt) override {
        std::cout << "ImplExtractLookahead preorder(IR::AssignmentStatement assn_stmt = " << assn_stmt << std::endl;
        auto ltype = typeMap->getType(assn_stmt->left);
        cstring updated_name = "";
        // Get updated name
        if (auto mem = assn_stmt->left->to<IR::PathExpression>()) {
            updated_name = mem->path->name.name;
        }
        
        if (ltype == nullptr) return assn_stmt;
        auto rtype = typeMap->getType(assn_stmt->right);
        if (rtype == nullptr) return assn_stmt;
        if (auto mem = assn_stmt->right->to<IR::MethodCallExpression>()) {
            if (auto new_mem = mem->method->to<IR::Member>()) {
                if (new_mem->member.name == "lookahead") {
                    // std::cout << assn_stmt->left->toString() << " = " << "packet[" << std::to_string(global_pos) 
                    // << ":" << std::to_string(global_pos + rtype->width_bits() - 1) << "]" << std::endl;
                    if (updated_name != "") {
                        IR::PathExpression *up_path_left = 
                            new IR::PathExpression(new const IR::Path(IR::ID(updated_name)));
                        assn_stmt->left = up_path_left;
                    }
                    
                    IR::PathExpression *up_path_right = 
                    new IR::PathExpression(new const IR::Path(IR::ID("packet[" + std::to_string(global_pos) + varbit_v + 
                    " : " + std::to_string(global_pos + rtype->width_bits() - 1) + varbit_v + "]")));
                    assn_stmt->right = up_path_right;
                }
            }
        }
        return assn_stmt;
    }

    const IR::Node *preorder(IR::ParserState *state) override {
        return state;
    }
    const IR::Node *postorder(IR::ParserState *state) override {
        if (state->getName() == "start") {
            int N = state->components.size();
            // Output Move statement
            // TODO: the idea case is to check whether the last statement is 
            state->components.insert(state->components.begin() + N - 1,
                new IR::CAIRNMoveStatement(std::to_string(global_pos - 1) + varbit_v));
        }
        return state;
    }
    const IR::Node *preorder(IR::MethodCallStatement *methodcall) override {
        // One type of method call statement pkt.extract(hdr, x);
        auto call = methodcall->methodCall;
        cstring method_to_string = call->method->toString();
        // TODO: need to extend to other types of methodcall as well
        if (auto mem = call->method->to<IR::Member>()) {
            if (mem->member.name == "extract") {
                int pre_global = global_pos;
                
                int idx = 0;
                for (auto &v : *(call->arguments)) {
                    if (idx == 0) {
                        global_pos += typeMap->getType(v)->width_bits();
                    } 
                    idx++;
                }
                cstring mem1 = "\"" + call->arguments->at(0)->toString() + "\"";
                cstring mem2;
                if (idx == 1) {
                    mem2 = "packet[" + std::to_string(pre_global) + varbit_v + " : " + 
                        std::to_string(global_pos - 1) + varbit_v + "]";
                } else {
                    assert (idx == 2);
                    cstring arg_name = "";
                    // TODO: need to deal with IR of type in addition to PathExpression and Cast
                    if (auto mem3 = call->arguments->at(1)->expression->to<IR::PathExpression>()) {
                        arg_name = mem3->path->name.name;
                    } else if (auto mem3 = call->arguments->at(1)->expression->to<IR::Cast>()) {
                        if (auto cast_expr = mem3->expr->to<IR::PathExpression>()) {
                            arg_name = cast_expr->path->name.name;
                        }
                    }
                    mem2 = "packet[" + std::to_string(pre_global) + varbit_v + " : " + 
                        std::to_string(global_pos - 1) + varbit_v + "+" + arg_name + "]";
                    
                    varbit_v += "+" + arg_name;
                }
                // TODO: find a better way to name it
                return new IR::CAIRNExtractHeaderStatement(mem1, mem2);
            }
        }
        
        return methodcall;
    }
    
};

// This is invoked on each parser separately
class UpdateParserByReplacingGlobalVar : public PassManager {

 public:
    explicit UpdateParserByReplacingGlobalVar(ReferenceMap *refMap, TypeMap *typeMap) {
        passes.push_back(new ImplExtractLookahead(refMap, typeMap));
    }
};

}

    const IR::Node *DoExtractandLookaheadConversion::postorder(IR::P4Parser *parser) {
        UpdateParserByReplacingGlobalVar simpl(refMap, typeMap);
        simpl.setCalledBy(this);
        return parser->apply(simpl);
    }
}