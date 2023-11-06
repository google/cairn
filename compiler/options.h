#ifndef CAIRN_OPTIONS_H_
#define CAIRN_OPTIONS_H_

#include "frontends/common/options.h"
#include "frontends/common/parser_options.h"
#include "lib/cstring.h"

namespace cairn {

class CairnOptions : public CompilerOptions {
 public:
  bool show_ir_ = false;
  cstring output_file_ = nullptr;

  virtual ~CairnOptions() = default;

  CairnOptions() {
    registerOption(
        /*option=*/"-o", /*argName=*/"outfile",
        /*processor=*/
        [this](const char* file_name) {
          this->output_file_ = file_name;
          return true;
        },
        /*description=*/"Write the output to outfile.");
    registerOption(
        /*option=*/"--showIR", /*argName=*/nullptr,
        /*processor=*/
        [this](const char*) {
          this->show_ir_ = true;
          return true;
        },
        /*description=*/"Dump IR as comments in outfile.");
  }
  CairnOptions(const CairnOptions&) = default;
  CairnOptions& operator=(const CairnOptions&) = default;
  CairnOptions(CairnOptions&&) = delete;
  CairnOptions& operator=(CairnOptions&&) = delete;
};

using CairnContext = P4CContextWithOptions<CairnOptions>;

}  // namespace cairn

#endif  // CAIRN_OPTIONS_H_
