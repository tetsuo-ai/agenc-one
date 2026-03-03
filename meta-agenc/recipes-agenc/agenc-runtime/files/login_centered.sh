#!/bin/sh
printf '\033[33;115H'
exec /bin/login "$@"
