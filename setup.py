import os
import sys
import shutil
import subprocess
from optparse import OptionParser
from conf import settings

app_name = 'NiceYouGet'

def update_windows():
    """将ui文件转换为py文件"""
    _dir_ui = os.path.join(settings.BASE_DIR, 'ui')
    _dir_windows = os.path.join(settings.BASE_DIR, 'windows', 'ui')
    for file in os.listdir(_dir_ui):
        if file.endswith('.ui'):
            os.system('pyside2-uic -o {} {}'.format(
                os.path.join(_dir_windows, file).rstrip('.ui') + '.py',
                os.path.join(_dir_ui, file)
            ))
    """将资源文件转换为py文件"""
    os.system('pyside2-rcc -o {} {}'.format(
        os.path.join(settings.BASE_DIR, 'resource_rc.py'),
        os.path.join(settings.BASE_DIR, 'resource.qrc')
    ))

def build():
    update_windows()
    args = [
        'pyinstaller',
        '--specpath', os.path.join(settings.BASE_DIR, 'spec', sys.platform),
        '--distpath', os.path.join(settings.BASE_DIR, 'dist', sys.platform),
        '--workpath', os.path.join(settings.BASE_DIR, 'build', sys.platform),
        '-n', app_name,
        '--hidden-import', 'you_get.extractors',
        '--hidden-import', 'you_get.cli_wrapper',
        '--hidden-import', 'you_get.processor',
        '--hidden-import', 'you_get.util',
        '--additional-hooks-dir', os.path.join(settings.BASE_DIR, 'hooks')
        # '--debug', 'all'
    ]

    if sys.platform == 'darwin':
        args.extend([
            '-w',
            '-i', os.path.join(settings.BASE_DIR, 'static/icon/darwin/icon.icns')
        ])
    elif sys.platform == 'linux':
        args.extend([
            '-F',
            '-i', os.path.join(settings.BASE_DIR, 'static/icon/linux/icon.png')
        ])
    elif sys.platform == 'win32':
        args.extend([
            '-w',
            # '-F',
            # '-c',
            '-i', os.path.join(settings.BASE_DIR, 'static/icon/win32/icon.ico')
            ]
        )
        args.insert(0, '/c')
        args.insert(0, 'cmd')

    args.extend(['main.py'])

    subprocess.run(args)


def clean():
    shutil.rmtree(
        os.path.join(settings.BASE_DIR, 'dist/{}'.format(sys.platform)))
    shutil.rmtree(
        os.path.join(settings.BASE_DIR, 'build/{}'.format(sys.platform)))
    shutil.rmtree(
        os.path.join(settings.BASE_DIR, 'spec/{}'.format(sys.platform)))



if __name__ == "__main__":
    parser = OptionParser(usage="Usage: %prog [options] arg1 arg2",
                          version=settings.VERSION)
    parser.add_option(
        '-t', '--target', help='target: build/update_windows/clean')
    options, args = parser.parse_args()
    if not options.target:
        parser.print_help()
    elif options.target == 'build':
        build()
    elif options.target == 'update_windows':
        update_windows()
    elif options.target == 'clean':
        clean()
    else:
        parser.print_help()
