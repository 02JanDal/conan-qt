#!/bin/sh

CONAN_DATA=$HOME/.conan/data/
CONAN_USERNAME=jandal
CONAN_CHANNEL=testing
PACKAGE_VERSION=5.7.0

tmpdir=`mktemp -d`
cd $tmpdir
mkdir single merged

function cleanup() {
    rm -rf $tmpdir
}
trap cleanup EXIT

function appendHash() {
    echo $1/`ls $1 | head -n1`
}

for module in `ls $CONAN_DATA | grep -vF Qt5Everything | grep -P "^Qt5.*"`
do
    echo "Copying $module to temporary storage..."
    dir=$CONAN_DATA/$module/$PACKAGE_VERSION/$CONAN_USERNAME/$CONAN_CHANNEL/package
    dir=`appendHash $dir`
    cp -r $dir $tmpdir/single/$module
    rm $tmpdir/single/$module/conan*.txt
done

for module in `ls $tmpdir/single`
do
    echo "Merging $module..."
    rsync -ar $tmpdir/single/$module/* $tmpdir/merged
done

everything_dir=$CONAN_DATA/Qt5Everything/$PACKAGE_VERSION/$CONAN_USERNAME/$CONAN_CHANNEL/package
everything_dir=`appendHash $everything_dir`
diff --recursive --brief $everything_dir $tmpdir/merged | sed s,$everything_dir,ORIGIN, | sed s,$tmpdir/merged,MERGED,