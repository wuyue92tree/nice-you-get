import os
import sys
import subprocess

BASE_DIR = os.path.dirname(__file__)

app_name = 'nice-you-get'

def main():
    args = [
        'pyinstaller',
        '--specpath', os.path.join(BASE_DIR, 'spec', sys.platform),
        '--distpath', os.path.join(BASE_DIR, 'dist', sys.platform),
        '--workpath', os.path.join(BASE_DIR, 'build', sys.platform),
        '-n', app_name,
        '--hidden-import', 'you_get.extractors',
        '--hidden-import', 'you_get.cli_wrapper',
        '--hidden-import', 'you_get.processor',
        '--hidden-import', 'you_get.util'
    ]

    if sys.platform == 'darwin':
        args.extend([
            # '-w',
            # '-i', os.path.join(BASE_DIR, 'icon/darwin/icon.icns')
        ])
    elif sys.platform == 'linux':
        args.extend([
            '-F',
            # '-i', os.path.join(BASE_DIR, 'icon/linux/icon.png')
        ])
    elif sys.platform == 'win32':
        args.extend([
            '-F',
            # '-i', os.path.join(BASE_DIR, 'icon/win32/icon.ico')
            ]
        )
        args.insert(0, '/c')
        args.insert(0, 'cmd')

    args.extend(['main.py'])
    print(' '.join(args))

    subprocess.run(args)


if __name__ == '__main__':
    main()
