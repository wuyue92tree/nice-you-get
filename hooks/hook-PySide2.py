import os
from PyInstaller.utils.hooks import collect_system_data_files
from PyInstaller.utils.hooks.qt import pyside2_library_info, get_qt_binaries
from PyInstaller.compat import is_win

# Only proceed if PySide2 can be imported.
if pyside2_library_info.version is not None:

    hiddenimports = ['shiboken2']

    # Collect the ``qt.conf`` file.
    if is_win:
        target_qt_conf_dir = ['PySide2']
    else:
        target_qt_conf_dir = ['PySide2', 'Qt']

    datas = [x for x in
             collect_system_data_files(pyside2_library_info.location['PrefixPath'],
                                       os.path.join(*target_qt_conf_dir))
             if os.path.basename(x[0]) == 'qt.conf']

    # Collect required Qt binaries.
    # binaries = get_qt_binaries(pyside2_library_info)

    # new_binaries = []
    # for b in binaries:
    #     path, _ = b
    #     if 'opengl32sw.dll' in path:
    #         continue
    #     new_binaries.append(b)
    # binaries = new_binaries
    binaries = []
