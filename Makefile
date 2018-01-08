mkfile_path = $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir = $(dir $(mkfile_path))

all:
	python3 -m venv venv
	venv/bin/pip install antlr4-python3-runtime typing
	echo "#!/bin/bash" >latc
	echo "$(mkfile_dir)venv/bin/python3 $(mkfile_dir)src/compile.py \"\$$@\"" >>latc
	echo "clang \"\$${@%.*}.ll\" $(mkfile_dir)src/stdlatte.c -o \"\$${@%.*}.o\" >>latc
	chmod +x latc

clean:
	rm -rf venv
	rm latc