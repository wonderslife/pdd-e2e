@echo off
rem BDRM Test System - testcase CLI launcher
rem Usage: bin\testcase init <name> [-f] | list | help
rem NOTE: do NOT double-click the .js directly - Windows runs it with
rem       Script Host (JScript) instead of node, which fails with 800A03F6.
node "%~dp0testcase.js" %*
