#pragma once

#include <QObject>

class TestObject : public QObject
{
    Q_OBJECT
public:
    explicit TestObject(QObject *parent = nullptr);

signals:
    void signal(const QString &arg);

public slots:
    void slot(const QString &arg);
};