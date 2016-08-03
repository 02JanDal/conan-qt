#!/usr/bin/env python3
from pyratemp import Template
from yaml import load as yamlload
from os import mkdir, getenv, walk, path, makedirs
from shutil import rmtree, copytree
import subprocess
from toposort import toposort_flatten
from argparse import ArgumentParser
from string import Template as StringTemplate
from sys import platform


class DictObject:
    def __init__(self, d):
        for k, v in d.items():
            if isinstance(v, (list, tuple)):
                self.__dict__[k] = [DictObject(x) if isinstance(x, dict) else x for x in v]
            else:
                self.__dict__[k] = DictObject(v) if isinstance(v, dict) else v

    def __contains__(self, key):
        return key in self.__dict__

    def __getitem__(self, key):
        return self.__dict__[key] if key in self else None

    def __missing__(self, key):
        return None

    def __getattr__(self, key):
        return self.__getitem__(key)

    @staticmethod
    def maybe_wrap(value):
        return DictObject(value) if isinstance(value, dict) else value


class Generator:
    __templates = {}
    __data = None

    def __process_template(self, filein, fileout, data):
        if path.exists(fileout):
            return
        filein = 'templates/' + filein + '.template'
        if filein not in self.__templates:
            self.__templates[filein] = Template(filename=filein, escape=None)
        with open(fileout, 'w') as f:
            template = self.__templates[filein]
            f.write(template(**{k: DictObject.maybe_wrap(v) for k, v in data.items()}))

    def __load_data(self):
        self.__data = self.__data or yamlload(open('data.yaml', 'r'))

    def __dir(self, package, version):
        return package + '-' + version

    def packages(self):
        return set([entry.name for entry in self.__data['packages']])

    def versions_for_package(self, package):
        self.__load_data()
        versions = []
        for entry in self.__data['packages']:
            if entry.name == package:
                versions += entry.versions
        return set(versions)

    def packages_for_version(self, version):
        self.__load_data()
        packages = []
        for entry in self.__data['packages']:
            if version in entry['versions']:
                packages.append(entry['name'])
        return set(packages)

    def entry(self, package, version):
        self.__load_data()
        try:
            return next(entry for entry in self.__data['packages'] if entry['name'] == package and version in entry['versions'])
        except StopIteration:
            return None

    def generate(self, package, version):
        self.__load_data()

        dir = self.__dir(package, version)
        testdir = dir + '/test'
        if path.exists('data/{}-{}'.format(package, version)):
            copytree('data/{}-{}'.format(package, version), dir)
        elif path.exists('data/{}'.format(package)):
            copytree('data/{}'.format(package), dir)
        if not path.exists(dir):
            mkdir(dir)
        if not path.exists(testdir):
            mkdir(testdir)

        data = self.entry(package, version)
        if not data:
            print('{} version {} is not available from data.yaml'.format(package, version))
            return False
        data['version'] = version
        data['mkspecname'] = data['mkspecname'] if 'mkspecname' in data else data['name'].replace('Qt5', '').lower()

        subargs = {
            'version': version,
            'version_majmin': '.'.join(version.split('.')[:2])
        }
        if 'src' in data:
            if 'git' in data['src'] and 'tag' in data['src']['git']:
                data['src']['git']['tag'] = StringTemplate(data['src']['git']['tag']).safe_substitute(**subargs)
            if 'tar' in data['src']:
                if 'file' in data['src']['tar']:
                    data['src']['tar']['file'] = StringTemplate(data['src']['tar']['file']).safe_substitute(**subargs)
                if 'url' in data['src']['tar']:
                    data['src']['tar']['url'] = StringTemplate(data['src']['tar']['url']).safe_substitute(**subargs)
                if 'root' in data['src']['tar']:
                    data['src']['tar']['root'] = StringTemplate(data['src']['tar']['root']).safe_substitute(**subargs)

        self.__process_template('build.py', dir + '/build.py', data)
        if package == 'Qt5Everything':
            self.__process_template('conanfile-qteverything-fromsrc.py', dir + '/conanfile.py', data)
        elif isinstance(data['src'], str):
            self.__process_template('conanfile-frominherit.py', dir + '/conanfile.py', data)
        else:
            self.__process_template('conanfile-fromsrc.py', dir + '/conanfile.py', data)
        self.__process_template('test/conanfile.py', testdir + '/conanfile.py', data)

        if not 'isvirtual' in data or not data['isvirtual']:
            self.__process_template('test/CMakeLists.txt', testdir + '/CMakeLists.txt', data)

            if 'test' in data:
                if 'function' in data['test'] or 'object' in data['test']:
                    self.__process_template('test/main.cpp', '{}/tst_{}.cpp'.format(testdir, data['name']), data)
                if 'item' in data['test']:
                    self.__process_template('test/main.qml', '{}/main.qml'.format(testdir), data)
                    self.__process_template('test/qml_main.cpp', '{}/qml_main.cpp'.format(testdir), data)

        return True

    def remove(self, package, version):
        rmtree(self.__dir(package, version), ignore_errors=True)


def export_package(username, channel, package, version):
    dir = package + '-' + version
    subprocess.check_call(['conan', 'export', username + '/' + channel], cwd=dir)


def test_package(package, version):
    dir = package + '-' + version
    subprocess.check_call(['conan', 'test_package'], cwd=dir)


def dependencies(entry):
    deps = entry['selfdependencies'] if 'selfdependencies' in entry else []
    if isinstance(entry['src'], str):
        deps.append(entry['src'])
    return set(deps)


def current_operating_system():
    os = platform
    if os.startswith('linux'):
        return 'linux'
    elif os == 'darwin':
        return 'osx'
    else:
        return 'windows'

version = '5.7.0'
username = getenv('CONAN_USERNAME', "jandal")
channel = getenv('CONAN_CHANNEL', 'testing')

if __name__ == '__main__':
    parser = ArgumentParser(description='Generate conanfiles for Qt modules')
    parser.add_argument('-e', metavar='PKG', dest='exclude', type=str, nargs='+', help='packages to not build/test')
    parser.add_argument('packages', metavar='PKG', type=str, nargs='*', help='only build/test these packages')
    parser.add_argument('-g', dest='generateonly', action='store_true', help='Only generate files, do not build/install/test anything')
    args = parser.parse_args()

    g = Generator()

    if args.packages:
        packages = args.packages
    else:
        packages = g.packages_for_version(version)
    package_entries = [g.entry(pkg, version) for pkg in packages]
    packages_dependencies = {e['name']: dependencies(e) for e in package_entries if 'os' not in e or current_operating_system() == e['os']}
    packages_sorted = toposort_flatten(packages_dependencies)

    def should_build(package):
        if args.exclude and pkg in args.exclude:
            return False
        else:
            return package in packages

    for pkg in packages_sorted:
        print('Re-generating {} {}'.format(pkg, version))
        g.remove(pkg, version)
        if g.generate(pkg, version):
            if not args.generateonly:
                export_package(username, channel, pkg, version)
                if should_build(pkg):
                    test_package(pkg, version)
