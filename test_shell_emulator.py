import unittest
import tempfile
import zipfile
import os
import sys
from unittest import mock
from io import BytesIO

class VirtualFileSystem:
    def __init__(self, zip_path):
        self.zip_path = zip_path

        # Загружаем zip-архив в оперативную память
        with open(zip_path, 'rb') as f:
            self.zip_memory = BytesIO(f.read())

        self.zip_file = zipfile.ZipFile(self.zip_memory, 'r')
        self.current_path = "/"

    def ls(self):
        # Получаем список файлов и папок в текущей директории
        files = []
        for name in self.zip_file.namelist():
            if name.startswith(self.current_path.lstrip('/')):
                relative_path = name[len(self.current_path.lstrip('/')):].strip('/')
                if '/' not in relative_path and relative_path:
                    files.append(relative_path)
        return files

    def cd(self, path):
        # Переход в другую директорию
        if path == "..":
            # Переход на уровень вверх
            if self.current_path != "/":
                self.current_path = "/".join(self.current_path.strip('/').split('/')[:-1]) + '/'
            return

        # Обработка абсолютного и относительного пути
        new_path = os.path.normpath(os.path.join(self.current_path, path)).replace("\\", "/") + '/'

        # Проверяем, существует ли такая директория
        if any(name.startswith(new_path.lstrip('/')) and name.endswith('/') for name in self.zip_file.namelist()):
            self.current_path = new_path
        else:
            raise FileNotFoundError("Directory not found")

    def pwd(self):
        # Текущая директория
        return self.current_path

    def mv(self, src, dst):
        # Нормализация и построение абсолютных путей
        src_path = os.path.normpath(os.path.join(self.current_path, src)).replace("\\", "/").lstrip('/')
        dst_path = os.path.normpath(os.path.join(self.current_path, dst)).replace("\\", "/").lstrip('/')

        # Проверяем, является ли 'dst' директорией (существуют ли файлы, начинающиеся с 'dst/')
        is_dst_dir = any(name.startswith(dst_path + '/') for name in self.zip_file.namelist())

        if dst.endswith('/') or is_dst_dir:
            # Если 'dst' — директория, добавляем к пути имя файла
            dst_path = os.path.join(dst_path, os.path.basename(src_path)).replace("\\", "/")

        # Проверяем наличие исходного файла
        if src_path not in self.zip_file.namelist():
            raise FileNotFoundError(f"Source file '{src}' not found")

        # Создаем новый zip-архив в памяти
        new_zip_memory = BytesIO()
        with zipfile.ZipFile(new_zip_memory, 'w', zipfile.ZIP_DEFLATED) as new_zip:
            for item in self.zip_file.infolist():
                if item.filename == src_path:
                    # Читаем содержимое исходного файла
                    with self.zip_file.open(item.filename) as source_file:
                        data = source_file.read()
                    # Создаем новый ZipInfo для целевого файла, сохраняя метаданные
                    new_info = zipfile.ZipInfo(dst_path)
                    new_info.date_time = item.date_time
                    new_info.compress_type = item.compress_type
                    new_info.external_attr = item.external_attr
                    # Записываем файл в новый архив
                    new_zip.writestr(new_info, data)
                else:
                    # Копируем остальные файлы как есть
                    new_zip.writestr(item, self.zip_file.read(item.filename))

        # Обновляем архив в памяти
        self.zip_memory = new_zip_memory
        self.zip_file.close()  # Закрываем текущий zip_file перед повторным открытием
        self.zip_file = zipfile.ZipFile(self.zip_memory, 'r')

        # Сохраняем изменения в оригинальный архив
        self._save_changes()

    def _save_changes(self):
        # Сохраняем текущие изменения из памяти обратно в zip-файл на диске
        with open(self.zip_path, 'wb') as f:
            f.write(self.zip_memory.getvalue())

    def exit(self):
        # Закрываем архив и завершаем работу
        self.zip_file.close()
        self.zip_memory.close()
        sys.exit()

    def close(self):
        # Метод для закрытия zip_file и zip_memory
        self.zip_file.close()
        self.zip_memory.close()

class TestVirtualFileSystem(unittest.TestCase):
    def setUp(self):
        # Создаем временный zip-архив с известной структурой
        self.temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        with zipfile.ZipFile(self.temp_zip, 'w') as z:
            # Корневая папка
            z.writestr('file.txt', 'Content of file.txt')
            z.writestr('file2.txt', 'Content of file2.txt')
            z.writestr('file3.txt', 'Content of file3.txt')
            # Папка del1
            z.writestr('del1/', '')  # Создание папки
            z.writestr('del1/super.txt', 'Content of super.txt')
            z.writestr('del1/super1.txt', 'Content of super1.txt')
            # Папка del2/archive2/
            z.writestr('del2/', '')  # Создание папки del2
            z.writestr('del2/archive2/', '')  # Создание папки del2/archive2
            z.writestr('del2/archive2/class1.txt', 'Content of class1.txt')
            z.writestr('del2/archive2/class2.txt', 'Content of class2.txt')
        
        self.vfs = VirtualFileSystem(self.temp_zip.name)

    def tearDown(self):
        try:
            # Закрываем файловую систему перед удалением файла
            self.vfs.close()
        except Exception as e:
            print(f"Error closing VirtualFileSystem: {e}")
        try:
            # Удаляем временный zip-архив
            os.unlink(self.temp_zip.name)
        except Exception as e:
            print(f"Error deleting temporary zip file: {e}")

    # Тесты для команды ls
    def test_ls_root(self):
        expected = ['file.txt', 'file2.txt', 'file3.txt', 'del1', 'del2']
        result = self.vfs.ls()
        self.assertCountEqual(result, expected)

    def test_ls_subdirectory(self):
        self.vfs.cd('del1')
        expected = ['super.txt', 'super1.txt']
        result = self.vfs.ls()
        self.assertCountEqual(result, expected)

    # Тесты для команды cd
    def test_cd_into_subdirectory(self):
        self.vfs.cd('del2/archive2')
        self.assertEqual(self.vfs.pwd(), '/del2/archive2/')

    def test_cd_up_one_level(self):
        self.vfs.cd('del1')
        self.vfs.cd('..')
        self.assertEqual(self.vfs.pwd(), '/')

    # Тесты для команды pwd
    def test_pwd_root(self):
        self.assertEqual(self.vfs.pwd(), '/')

    def test_pwd_after_cd(self):
        self.vfs.cd('del2/archive2')
        self.assertEqual(self.vfs.pwd(), '/del2/archive2/')

    # Тесты для команды mv
    def test_mv_move_file_to_subdirectory(self):
        # Перемещаем 'file.txt' в 'del1/'
        self.vfs.mv('file.txt', 'del1/')
        self.vfs.cd('del1')
        files = self.vfs.ls()
        self.assertIn('file.txt', files)
        # Проверяем, что файл больше не в корне
        self.vfs.cd('..')
        files_root = self.vfs.ls()
        self.assertNotIn('file.txt', files_root)

    def test_mv_move_file_back_to_root(self):
        # Перемещаем 'del1/super.txt' обратно в корень
        self.vfs.cd('del1')
        self.vfs.mv('super.txt', '../')
        self.vfs.cd('..')
        files_root = self.vfs.ls()
        self.assertIn('super.txt', files_root)
        # Проверяем, что файл больше не в del1
        self.vfs.cd('del1')
        files_del1 = self.vfs.ls()
        self.assertNotIn('super.txt', files_del1)

    # Тесты для команды exit
    @mock.patch('sys.exit')
    def test_exit_calls_sys_exit(self, mock_exit):
        self.vfs.exit()
        mock_exit.assert_called_once()

    @mock.patch('sys.exit')
    def test_exit_with_code(self, mock_exit):
        # В текущей реализации exit не принимает аргументы, поэтому тестируем просто вызов
        self.vfs.exit()
        mock_exit.assert_called_once()

    # Дополнительные тесты для команд, чтобы убедиться в корректности
    def test_mv_invalid_source(self):
        with self.assertRaises(FileNotFoundError):
            self.vfs.mv('nonexistent.txt', 'del1/')

    def test_cd_nonexistent_directory(self):
        with self.assertRaises(FileNotFoundError):
            self.vfs.cd('nonexistent_dir')

    def test_ls_empty_directory(self):
        # Создадим пустую директорию
        with zipfile.ZipFile(self.temp_zip.name, 'a') as z:
            z.writestr('empty_dir/', '')
        # Перезагружаем файловую систему, чтобы учесть изменения
        self.vfs.close()
        self.vfs = VirtualFileSystem(self.temp_zip.name)
        self.vfs.cd('empty_dir')
        result = self.vfs.ls()
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
