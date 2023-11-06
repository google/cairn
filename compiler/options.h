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
