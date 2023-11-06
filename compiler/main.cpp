#include <fstream>

#include "midend.h"
#include "options.h"

#include "frontends/common/options.h"
#include "frontends/common/parseInput.h"
#include "frontends/p4/frontend.h"
#include "frontends/p4/toP4/toP4.h"
#include "lib/compile_context.h"

int main(int argc, char *argv[]) {
  // Initialize p4c configurations.
  using ::cairn::CairnContext;
  using ::cairn::CairnOptions;
  AutoCompileContext compile_context(new CairnContext);
  CairnOptions &options = CairnContext::get().options();
  options.langVersion = CompilerOptions::FrontendVersion::P4_16;

  // Process command line options.
  if (options.process(argc, argv) != nullptr) {
    options.setInputFile();
  }

  // Use debug hook to enable compiler pass dump.
  auto hook = options.getDebugHook();

  // Parse input P4 file.
  const ::IR::P4Program *program = ::P4::parseP4File(options);

  // Apply standard front end passes.
  ::P4::FrontEnd front_end;
  front_end.addDebugHook(hook);
  program = front_end.run(options, program);

  // Apply selected mid end passes.
  using ::cairn::MidEnd;
  MidEnd mid_end;
  mid_end.addDebugHook(hook);
  program = program->apply(mid_end);

  // Print the final program to the output file.
  if (options.output_file_ != nullptr) {
    std::ofstream cout(options.output_file_);
    auto to_p4 = ::P4::ToP4(&cout, options.show_ir_);
    program->apply(to_p4);
  }

  return 0;
}
