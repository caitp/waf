#!/usr/bin/env bash

set -e

function noop {
	local nothing=$0
}

if [ -z $PYTHON_VERSION ]; then
	PYTHON_VERSION="2"
fi

if [[ "$TRAVIS_OS_NAME" = "osx" ]]; then
	# TODO: Eventually, Travis-CI should support Python on the OSX VMs
	ulimit -n 4096
	# TODO: Use a submodule for this?
	mkdir terrify
	curl -L https://github.com/MacPython/terryfy/archive/master.tar.gz | tar --strip-components=1 -xzf - -C terrify
	source terrify/travis_tools.sh
	source terrify/library_installers.sh

	get_python_environment homebrew $PYTHON_VERSION

elif [[ "$TRAVIS_OS_NAME" = "linux" ]]; then
	# Not supported ATM
	noop
fi
