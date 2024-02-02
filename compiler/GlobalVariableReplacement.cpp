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
        std::cout << "parser state name = " << v.first << std::endl;
        for (auto mem : v.second) {
            std::cout << "key = " << mem.first << std::endl;
            for (size_t i = 0; i < mem.second.size(); i++) {
                std::cout << mem.second[i] << " ";
            }
        }
        std::cout << std::endl;
    }
}

class CollectInfo : public Inspector {
    TypeMap *typeMap;
    map_var_to_pos_appear* read_mp;
    map_var_to_pos_appear* write_mp;
    std::map<cstring, std::map<cstring, int>> read_write_cnt; // record the line of statement for read/write
    map_replace_width_mp* replace_width_mp;
    cstring curr_state = "";
public: 
    CollectInfo(TypeMap *typeMap, map_var_to_pos_appear* read_mp, map_var_to_pos_appear* write_mp,
    map_replace_width_mp* replace_width_mp) :
    typeMap(typeMap), read_mp(read_mp), write_mp(write_mp), replace_width_mp(replace_width_mp) {
        setName("CollectInfo");
    }
    bool preorder(const IR::ParserState *parser_state) override {
        std::cout << "bool preorder parser_state = " << parser_state << std::endl;
        curr_state = parser_state->getName();
        if ((*read_mp).count(curr_state) == 0) {
            (*read_mp)[curr_state] = {};
        }
        if ((*write_mp).count(curr_state) == 0) {
            (*write_mp)[curr_state] = {};
        }
        if ((*replace_width_mp).count(curr_state) == 0) {
            (*replace_width_mp)[curr_state] = {};
        }
        if (read_write_cnt.count(curr_state) == 0) {
            read_write_cnt[curr_state] = {};
        }
        return true;
    }
    bool preorder(const IR::AssignmentStatement *assn_stmt) override {
        std::cout << "preorder(IR::AssignmentStatement *assn_stmt) in CollectInfo" << std::endl;
        std::cout << "assn_stmt = " << assn_stmt << std::endl;
        if (auto mem = assn_stmt->left->to<IR::PathExpression>()) {
            
            auto ltype = typeMap->getType(assn_stmt->left);
            int width = ltype->width_bits();
            cstring key = mem->path->name.name;
            std::cout << "key = " << key << " width = " << width << std::endl;
            ((*replace_width_mp)[curr_state])[key] = width;
            // x = ...; x can be converted to an object belonging to PathExpression
            if (((*write_mp)[curr_state]).count(key) == 0) {
                ((*write_mp)[curr_state])[key] = {};
            }
            if (read_write_cnt[curr_state].count(key) == 0) {
                read_write_cnt[curr_state][key] = 0;
            }
            (*write_mp)[curr_state][key].push_back(read_write_cnt[curr_state][key]);
            read_write_cnt[curr_state][key]++;
        }
        std::cout << "write_mp size = " << (*write_mp).size() << std::endl;
        print_mp(write_mp);
        return true;
    }

    bool preorder(const IR::MethodCallStatement *methodcall) override {
        // One type of method call statement pkt.extract(hdr, x);
        // std::cout << "methodcall = " << methodcall->methodCall << std::endl;
        auto call = methodcall->methodCall;
        // std::cout << "call->method = " << call->method << std::endl;
        std::cout << "MethodCallStatement curr_state = " << curr_state << std::endl;
        if (call->method->is<IR::Member>()) {
            // std::cout << "call->is<IR::Member> Come here\n";
            for (size_t i = 0; i < (*(call->arguments)).size(); i++) {
                auto argv = call->arguments->at(i);
                std::cout << "argv =" << argv << std::endl;
                // Current we only deal with args with the type to be IR::PathExpression, and IR::Cast
                std::cout << "argv->expression->node_type_name() = " << argv->expression->node_type_name() << std::endl;
                // assert(argv->expression->node_type_name() == "PathExpression" || argv->expression->node_type_name() == "Member");
                cstring key;
                // auto ltype = typeMap->getType(argv->expression);
                // int width = ltype->width_bits();
                int width = -1;
                if (auto mem3 = argv->expression->to<IR::PathExpression>()) {
                    key = mem3->path->name.name;
                    auto ltype = typeMap->getType(argv->expression);
                    width = ltype->width_bits();
                } else if (auto mem3 = argv->expression->to<IR::Cast>()) {
                    // std::cout << "Cast: mem3->expr = " << mem3->expr << std::endl;
                    if (auto cast_expr = mem3->expr->to<IR::PathExpression>()) {
                        auto ltype = typeMap->getType(cast_expr);
                        width = ltype->width_bits();
                        key = cast_expr->path->name.name;
                        std::cout << "cast_expr->path->name.name = " << cast_expr->path->name.name << std::endl;
                    }
                }
                if (i >= 0) {    
                    ((*replace_width_mp)[curr_state])[key] = width;
                    // pkt.extract(hdr, x), x would be the variable to read from
                    // std::cout << "(*read_mp)[argv] = cnt;\n" << argv << std::endl;
                    if (read_write_cnt[curr_state].count(key) == 0) {
                        read_write_cnt[curr_state][key] = 0;
                    }
                    
                    if (((*read_mp)[curr_state]).count(key) == 0) {
                        ((*read_mp)[curr_state])[key] = {};
                    }
                    ((*read_mp)[curr_state])[key].push_back(read_write_cnt[curr_state][key]);
                    read_write_cnt[curr_state][key]++;
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
    // key: parser state node name; val is a map with key: old var name, val: how many times does it need replacement?
    std::map<cstring, std::map<cstring, int>> replace_time_map; 
    // key: parser state node name; val is a map with key: old var name, val: how many times has it been replaced?
    std::map<cstring, std::map<cstring, int>> actual_write_replace_time_map; 
    // key: parser state node name; val is a map with key: old var name, val: how many times has it been replaced?
    std::map<cstring, std::map<cstring, int>> actual_write_replace_time_map_statement; 
    // key: parser state node name; val is a map with key: old var name, val: whether its write version is replaced before or not
    std::map<cstring, std::map<cstring, int>> write_flag_map; 
    // key: parser state node name; val is a map with key: new var name, val: width of its type
    map_replace_width_mp *replace_width_mp; 
    // key: parser state node name; val is a map with key: new var name, val: width of its type
    std::map<cstring, std::map<cstring, int>> width_mp;
    cstring curr_state = ""; // record which parser node it is visiting

public:
    explicit ComputeDepVar(ReferenceMap *refMap, TypeMap *typeMap,
    map_var_to_pos_appear* read_mp, map_var_to_pos_appear* write_mp, map_replace_width_mp *replace_width_mp)
    : refMap(refMap), typeMap(typeMap), read_mp(read_mp), write_mp(write_mp), replace_width_mp(replace_width_mp) {
        // get how many times a variable should be replaced
        get_replace_time();
        setName("ComputeDepVar");
    }

    // TODO: change it
    void get_replace_time() {
        int replace_time = 0;
        for (auto &v : *write_mp) {
            if ((*read_mp).count(v.first)) {
                for (auto &var : v.second) {
                    if ((*read_mp)[v.first].count(var.first)) {
                        // one variable appear in both read and write
                        std::vector<int> write_vec = var.second;
                        std::vector<int> read_vec = (*read_mp)[v.first][var.first];
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
                        replace_time_map[v.first][var.first] = replace_time;
                    }
                }
            }
        }
        for (auto &v : replace_time_map) {
            std::cout << "parser state name = " << v.first << std::endl;
            width_mp[v.first] = {};
            for (auto &mem : v.second) {
                // find the bit width of a variable
                for (size_t i = 0; i < mem.second; i++) {
                    cstring new_key = "new_"+ mem.first +std::to_string(i);
                    width_mp[v.first][new_key] = (*replace_width_mp)[v.first][mem.first];
                }
            }
        }
        // std::cout << "print width mp" << std::endl;
        // for (auto &v : width_mp) {
        //     std::cout << "parser state name = " << v.first << std::endl;
        //     for (auto &mem : v.second) {
        //         std::cout << "mem.first = " << mem.first << " mem.second = " << mem.second << std::endl;
        //     }
        // }
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
            cstring key = mem->path->name.name;
            std::cout << "key = " << key << std::endl;
            if (replace_time_map[curr_state].count(key)) {
                if (actual_write_replace_time_map[curr_state].count(key) == 0) {
                    actual_write_replace_time_map[curr_state][key] = 0;
                }
                if (actual_write_replace_time_map[curr_state][key] < replace_time_map[curr_state][key]) {
                    // Start replacement
                    std::cout << "Start replacement" << std::endl;
                    IR::PathExpression *up_path = 
                    new IR::PathExpression(new const IR::Path(IR::ID("new_"+key+std::to_string(actual_write_replace_time_map[curr_state][key]))));
                    assn_stmt->left = up_path;
                    write_flag_map[curr_state][key] = 1;
                    std::cout << "assn_stmt = " << assn_stmt << std::endl;
                }
            }
        }
        // std::cout << "after assn_stmt->left = " << assn_stmt->left << std::endl;
        auto rtype = typeMap->getType(assn_stmt->right);
        if (rtype == nullptr) return assn_stmt;
        return assn_stmt;
    }

    const IR::Node *preorder(IR::ParserState *parser_state) override {
        // std::cout << "preorder parser_state = " << parser_state << std::endl;
        curr_state = parser_state->getName();
        return parser_state;
    }
    
    const IR::Node *postorder(IR::ParserState *state) override {
        // std::cout << "postorder parser_state = " << state << std::endl;
        cstring parser_state_name = state->getName();
        if (width_mp.count(parser_state_name)) {
            // Add declarations for new variables
            for (auto &v : width_mp[parser_state_name]) {
                // If the second parameter of new IR::Type_Bits is false, it means it is a bit array; Otherwise, it is an int array
                state->components.insert(state->components.begin(), new IR::Declaration_Variable(IR::ID(v.first), new IR::Type_Bits(v.second, false)));
            }
            int N = state->components.size();
            
            for (auto &v : replace_time_map[parser_state_name]) {
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
                cstring key;
                if (auto mem = argv->expression->to<IR::PathExpression>()) {
                    key = mem->path->name.name;
                } else if (auto mem = argv->expression->to<IR::Cast>()) {
                    if (auto cast_expr = mem->expr->to<IR::PathExpression>()) {
                        key = cast_expr->path->name.name;
                    }
                } else {
                    key = argv->expression->toString();
                }
                std::cout << "Here: key = " << key << std::endl;
                if (write_flag_map[curr_state].count(key) != 0 && write_flag_map[curr_state][key] == 1) {
                    // Start replacement for read part
                    if (argv->expression->to<IR::PathExpression>()) {
                        IR::PathExpression *up_path = 
                        new IR::PathExpression(new const IR::Path(IR::ID("new_"+key+std::to_string(actual_write_replace_time_map[curr_state][key]))));
                        actual_write_replace_time_map[curr_state][key]++;
                        arguments_vec->at(i) = new IR::Argument(up_path);
                        modify_flag = 1;
                        write_flag_map[curr_state][key] = 0;
                    } else if (auto mem = argv->expression->to<IR::Cast>()) {
                        // new Cast(const IR::Type* type, const IR::Expression* expr);
                        IR::Cast *up_cast = 
                        new IR::Cast(mem->destType,new const IR::PathExpression(IR::ID("new_"+key+std::to_string(actual_write_replace_time_map[curr_state][key]))));
                        actual_write_replace_time_map[curr_state][key]++;
                        arguments_vec->at(i) = new IR::Argument(up_cast);
                        modify_flag = 1;
                        write_flag_map[curr_state][key] = 0;
                    }
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
    map_var_to_pos_appear* read_mp, map_var_to_pos_appear* write_mp, map_replace_width_mp* replace_width_mp) {
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