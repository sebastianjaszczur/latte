mkfile_path = $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir = $(dir $(mkfile_path))

all:
	python3 -m venv venv
	venv/bin/pip install antlr4-python3-runtime
	echo "#!/bin/bash" >insc_llvm
	echo "$(mkfile_dir)venv/bin/python3 $(mkfile_dir)src/llvm.py \"\$$@\"" >>insc_llvm
	chmod +x insc_llvm
	echo "#!/bin/bash" >insc_jvm
	echo "$(mkfile_dir)venv/bin/python3 $(mkfile_dir)src/jvm.py \"\$$@\"" >>insc_jvm
	chmod +x insc_jvm

clean:
	rm -rf venv
	rm insc_llvm
	rm insc_jvm