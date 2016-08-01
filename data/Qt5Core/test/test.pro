TEMPLATE = app

CONFIG += conan_basic_setup
include($$OUT_PWD/../conanbuildinfo.pri)

HEADERS = TestObject.h
SOURCES = TestObject.cpp
TARGET = qmake_test
QT = core