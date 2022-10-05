#!/bin/sh
export QT_DEBUG_PLUGINS=1

appname=`basename "$0" | sed s,\.sh$,,`

dirname=`dirname "$0"`
tmp="${dirname#?}"

if [ "${dirname%$tmp}" != "/" ]; then
dirname=$PWD/$dirname
fi

TCL_LIBRARY=$dirname/python/lib/tcl8.6
TK_LIBRARY=$dirname/python/lib/tk8.6
export TCL_LIBRARY
export TK_LIBRARY

LD_LIBRARY_PATH=$dirname/lib:$dirname/python/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH

"$dirname/$appname" "$@"

