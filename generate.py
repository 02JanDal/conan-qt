from pyratemp import Template
from yaml import load as yamlload
from os import mkdir, getenv
from shutil import rmtree
import subprocess
from toposort import toposort_flatten
from argparse import ArgumentParser


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
        try:
            return next(entry for entry in self.__data['packages'] if entry['name'] == package and version in entry['versions'])
        except StopIteration:
            return None

    def generate(self, package, version):
        self.__load_data()

        dir = self.__dir(package, version)
        testdir = dir + '/test'
        mkdir(dir)
        mkdir(testdir)

        data = self.entry(package, version)
        data['version'] = version
        self.__process_template('build.py', dir + '/build.py', data)
        if package == 'Qt5Base':
            self.__process_template('conanfile-qtbase-fromsrc.py', dir + '/conanfile.py', data)
        elif isinstance(data['src'], str):
            self.__process_template('conanfile-frominherit.py', dir + '/conanfile.py', data)
        else:
            self.__process_template('conanfile-fromsrc.py', dir + '/conanfile.py', data)
        self.__process_template('test/conanfile.py', testdir + '/conanfile.py', data)
        self.__process_template('test/CMakeLists.txt', testdir + '/CMakeLists.txt', data)

    def remove(self, package, version):
        rmtree(self.__dir(package, version), ignore_errors=True)


def export_package(username, package, version):
    dir = package + '-' + version
    subprocess.check_call(['conan', 'export', username], cwd=dir)


def test_package(package, version):
    dir = package + '-' + version
    subprocess.check_call(['conan', 'test_package'], cwd=dir)


def dependencies(entry):
    deps = entry['selfdependencies'] if 'selfdependencies' in entry else []
    if isinstance(entry['src'], str):
        deps.append(entry['src'])
    return set(deps)

if __name__ == '__main__':
    parser = ArgumentParser(description='Generate conanfiles for Qt modules')
    parser.add_argument('-e', metavar='PKG', dest='exclude', type=str, nargs='+', help='packages to not build/test')
    parser.add_argument('packages', metavar='PKG', type=str, nargs='*', help='only build/test these packages')
    args = parser.parse_args()

    g = Generator()

    version = '5.7.0'
    username = getenv("CONAN_USERNAME", "jandal")

    package_entries = [g.entry(pkg, version) for pkg in g.packages_for_version(version)]
    packages_dependencies = {e['name']: dependencies(e) for e in package_entries}
    packages_sorted = toposort_flatten(packages_dependencies)

    for pkg in packages_sorted:
        print('Re-generating {} {}'.format(pkg, version))
        g.remove(pkg, version)
        g.generate(pkg, version)
        export_package(username, pkg, version)
        if (not args.exclude or pkg not in args.exclude) and (not args.packages or pkg in args.packages):
            test_package(pkg, version)
