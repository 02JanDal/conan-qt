#include "TestObject.h"

#include <QCoreApplication>

TestObject::TestObject(QObject *parent)
    : QObject(parent) {}

void TestObject::slot(const QString &arg)
{
    emit signal(arg);
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    TestObject a, b;
    QObject::connect(&a, SIGNAL(signal(QString)), &b, SLOT(slot(QString)));
    a.slot("adsf");

    return 0;
}