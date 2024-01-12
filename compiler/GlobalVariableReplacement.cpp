#include "GlobalVariableReplacement.h"

#include "ir/pass_manager.h"

#include <typeinfo>
#include <assert.h>
#include <string>

namespace P4 {
namespace {

// For debug purpose
void print_mp(map_var_to_pos_appear* mp) {
    for (auto v : *mp) {
        std::cout << "key = " << v.first << std::endl;
        std::cout << "val = ";
        for (size_t i = 0; i < v.second.size(); i++) {
            std::cout << v.second[i] << " ";
        }
        std::cout << std::endl;
    }
}

class CollectInfo : public Inspector {
    TypeMap *typeMap;
    map_var_to_pos_appear* read_mp;
    map_var_to_pos_appear* write_mp;
    std::map<cstring, int> read_write_cnt; // record the line of statement for read/write
    std::map<cstring, int>* replace_width_mp;
public: 
    CollectInfo(TypeMap *typeMap, map_var_to_pos_appear* read_mp, map_var_to_pos_appear* write_mp,
    std::map<cstring, int>* replace_width_mp) :
    typeMap(typeMap), read_mp(read_mp), write_mp(write_mp), replace_width_mp(replace_width_mp) {
        setName("CollectInfo");
    }
    bool preorder(const IR::AssignmentStatement *assn_stmt) override {
        // std::cout << "preorder(IR::AssignmentStatement *assn_stmt) in CollectInfo" << std::endl;
        if (auto mem = assn_stmt->left->to<IR::PathExpression>()) {
            auto ltype = typeMap->getType(assn_stmt->left);
            int width = ltype->width_bits();
            cstring key = mem->path->name.name;
            // std::cout << "width = " << width << std::endl;
            (*replace_width_mp)[key] = width;
            // x = ...; x can be converted to an object belonging to PathExpression
            if ((*write_mp).count(key) == 0) {
                (*write_mp)[key] = {};
            }
            if (read_write_cnt.count(key) == 0) {
                read_write_cnt[key] = 0;
            }
            (*write_mp)[key].push_back(read_write_cnt[key]);
            read_write_cnt[key]++;
        }
        // std::cout << "write_mp size = " << (*write_mp).size() << std::endl;
        // print_mp(write_mp);
        return true;
    }

    bool preorder(const IR::MethodCallStatement *methodcall) override {
        // One type of method call statement pkt.extract(hdr, x);
        // std::cout << "methodcall = " << methodcall->methodCall << std::endl;
        auto call = methodcall->methodCall;
        // std::cout << "call->method = " << call->method << std::endl;
        if (call->method->is<IR::Member>()) {
            // std::cout << "call->is<IR::Member> Come here\n";
            for (size_t i = 0; i < (*(call->arguments)).size(); i++) {
                auto argv = call->arguments->at(i);
                std::cout << "argv =" << argv << std::endl;
                // Current we only deal with args with the type to be IR::PathExpression
                std::cout << "argv->expression->node_type_name() = " << argv->expression->node_type_name() << std::endl;
                // assert(argv->expression->node_type_name() == "PathExpression" || argv->expression->node_type_name() == "Member");
                cstring key;
                if (auto mem3 = argv->expression->to<IR::PathExpression>()) {
                    key = mem3->path->name.name;
                }
                if (i >= 0) {
                    auto ltype = typeMap->getType(argv->expression);
                    int width = ltype->width_bits();
                    (*replace_width_mp)[key] = width;
                    // pkt.extract(hdr, x), x would be the variable to read from
                    // std::cout << "(*read_mp)[argv] = cnt;\n" << argv << std::endl;
                    if (read_write_cnt.count(key) == 0) {
                        read_write_cnt[key] = 0;
                    }
                    if ((*read_mp).count(key) == 0) {
                        (*read_mp)[key] = {};
                    }
                    (*read_mp)[key].push_back(read_write_cnt[key]);
                    read_write_cnt[key]++;
                }

            }
        }
        // std::cout << "read_mp size = " << (*read_mp).size() << std::endl;
        // print_mp(read_mp);
        return true;
    }
};

class ComputeDepVar : public Transform {
    ReferenceMap *refMap;
    TypeMap *typeMap;
    map_var_to_pos_appear* read_mp;
    map_var_to_pos_appear* write_mp;
    std::map<cstring, int> replace_time_map; // key: old var name, val: how many times does it need replacement?
    std::map<cstring, int> actual_write_replace_time_map; // key: old var name, val: how many times has it been replaced?
    std::map<cstring, int> actual_write_replace_time_map_statement; // key: old var name, val: how many times has it been replaced?
    std::map<cstring, int> write_flag_map; // key: old var name, val: whether its write version is replaced before or not
    std::map<cstring, int> *replace_width_mp; // key: new var name, val: width of its type
    std::map<cstring, int> width_mp; // key: new var name, val: width of its type

public:
    explicit ComputeDepVar(ReferenceMap *refMap, TypeMap *typeMap,
    map_var_to_pos_appear* read_mp, map_var_to_pos_appear* write_mp, std::map<cstring, int> *replace_width_mp)
    : refMap(refMap), typeMap(typeMap), read_mp(read_mp), write_mp(write_mp), replace_width_mp(replace_width_mp) {
        // get how many times a variable should be replaced
        get_replace_time();
        setName("ComputeDepVar");
    }

    void get_replace_time() {
        int replace_time = 0;
        for (auto &v : *write_mp) {
            if ((*read_mp).count(v.first)) {
                // one variable appear in both read and write
                std::vector<int> write_vec = v.second;
                std::vector<int> read_vec = (*read_mp)[v.first];
                size_t j = 0;
                for (size_t i = 0; i < write_vec.size(); i++) {
                    while (j < read_vec.size()) {
                        if (read_vec[j] > write_vec[i]) {
                            replace_time++;
                            j++;
                            break;
                        } else {
                            j++;
                        }
                    }
                }
                replace_time_map[v.first] = replace_time;
            }
        }
        for (auto &v : replace_time_map) {
            // find the bit width of a variable
            for (size_t i = 0; i < v.second; i++) {
                cstring new_key = "new_"+ v.first +std::to_string(i);
                width_mp[new_key] = (*replace_width_mp)[v.first];
            }
        }
    }

    const IR::Node *preorder(IR::Declaration_Variable *dec) override {
        // std::cout << "*preorder(IR::Declaration_Variable *dec) = " << dec << std::endl;
        // std::cout << "dec->node_type_name() = " << dec->node_type_name() << std::endl;
        return dec;
    }
    const IR::Node *preorder(IR::AssignmentStatement *assn_stmt) override {
        std::cout << "assn_stmt = " << assn_stmt << std::endl;
        // std::cout << "Enter ComputeDepVar preorder(...)" << std::endl;
        auto ltype = typeMap->getType(assn_stmt->left);
        if (ltype == nullptr) return assn_stmt;
        std::cout << "before assn_stmt->left = " << assn_stmt->left << std::endl;
        std::cout << "ltype = " << ltype << std::endl;
        // std::cout << "ltype->node_type_name() = " << ltype->node_type_name() << std::endl;
        if (auto mem = assn_stmt->left->to<IR::Member>()) {
            // std::cout << "left mem = " << mem << std::endl;
        } else if (auto mem = assn_stmt->left->to<IR::PathExpression>()) {
            cstring key = mem->toString();
            std::cout << "key = " << key << std::endl;
            if (replace_time_map.count(key)) {
                if (actual_write_replace_time_map.count(key) == 0) {
                    actual_write_replace_time_map[key] = 0;
                }
                if (actual_write_replace_time_map[key] < replace_time_map[key]) {
                    // Start replacement
                    IR::PathExpression *up_path = 
                    new IR::PathExpression(new const IR::Path(IR::ID("new_"+key+std::to_string(actual_write_replace_time_map[key]))));
                    assn_stmt->left = up_path;
                    write_flag_map[key] = 1;
                }
            }
        }
        // std::cout << "after assn_stmt->left = " << assn_stmt->left << std::endl;
        auto rtype = typeMap->getType(assn_stmt->right);
        if (rtype == nullptr) return assn_stmt;
        return assn_stmt;
    }

    const IR::Node *preorder(IR::ParserState *state) override {
        return state;
    }
    
    const IR::Node *postorder(IR::ParserState *state) override {
        // TODO: tofix later, will put this into the width_mp map
        if (state->getName() == "start") {
            for (auto &v : width_mp) {
                state->components.insert(state->components.begin(), new IR::Declaration_Variable(IR::ID(v.first), new IR::Type_Bits(v.second, true)));
            }
            int N = state->components.size();
            
            for (auto &v : replace_time_map) {
                // Update the global var's final value
                state->components.insert(state->components.begin() + N, 
                    new IR::AssignmentStatement(
                        new IR::PathExpression(new const IR::Path(IR::ID(v.first))),
                        new IR::PathExpression(new const IR::Path(IR::ID("new_"+v.first+std::to_string(v.second - 1))))
                    )
                );
            }
        }
        return state;
    }

    const IR::Node *preorder(IR::MethodCallStatement *methodcall) override {
        std::cout << "GlobalVariableReplacement methodcall = " << methodcall << std::endl;
        // One type of method call statement pkt.extract(hdr, x);
        auto call = methodcall->methodCall;
        IR::Vector<IR::Argument>* arguments_vec = new IR::Vector<IR::Argument>;
        int modify_flag = 0;
        if (call->method->is<IR::Member>()) {
            // Copy to a new argument_vec because the existing argument vec is read-only
            for (size_t i = 0; i < (*call->arguments).size(); i++) {
                arguments_vec->emplace_back(*call->arguments->at(i));
            }
            for (size_t i = 0; i < (*arguments_vec).size(); i++) {
                auto argv = arguments_vec->at(i);
                // Current we only deal with args with the type to be IR::PathExpression
                // assert(argv->expression->node_type_name() == "PathExpression");
                cstring key = argv->expression->toString();
                if (write_flag_map.count(key) != 0 && write_flag_map[key] == 1) {
                    // Start replacement for read part
                    IR::PathExpression *up_path = 
                    new IR::PathExpression(new const IR::Path(IR::ID("new_"+key+std::to_string(actual_write_replace_time_map[key]))));
                    actual_write_replace_time_map[key]++;
                    arguments_vec->at(i) = new IR::Argument(up_path);
                    modify_flag = 1;
                    write_flag_map[key] = 0;
                }
            }
        }
        if (modify_flag == 0) {
            return methodcall;
        }
        return new IR::MethodCallStatement(new IR::MethodCallExpression(call->method, call->typeArguments, arguments_vec));
    }
    
};

// This is invoked on each parser separately
class UpdateParserByReplacingGlobalVar : public PassManager {

 public:
    explicit UpdateParserByReplacingGlobalVar(ReferenceMap *refMap, TypeMap *typeMap,
    map_var_to_pos_appear* read_mp, map_var_to_pos_appear* write_mp, std::map<cstring, int>* replace_width_mp) {
        passes.push_back(new ComputeDepVar(refMap, typeMap, read_mp, write_mp, replace_width_mp));
    }
};

}

    bool FindReadWriteVariable::preorder(const IR::P4Parser *parser) {
        CollectInfo collectIn(typeMap, read_mp, write_mp, replace_width_mp);
        collectIn.setCalledBy(this);
        parser->apply(collectIn);
        return true;
    }

    const IR::Node *DoGlobalVariableReplacement::postorder(IR::P4Parser *parser) {
        // std::cout << "Enter DoGlobalVariableReplacement::postorder(IR::P4Parser *parser)" << std::endl;
        // for (auto &v : parser->states) {
        //     for (auto &comp : v->components)
        //         std::cout << "comp = " << comp << std::endl;
        // }
        // std::cout << "Exit DoGlobalVariableReplacement::postorder(IR::P4Parser *parser)" << std::endl;
        UpdateParserByReplacingGlobalVar simpl(refMap, typeMap, read_mp, write_mp, replace_width_mp);
        simpl.setCalledBy(this);
        return parser->apply(simpl);
    }
}