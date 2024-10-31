import argparse
import zipfile
import io
import os
import sys
import tkinter as tk
from tkinter import scrolledtext
import shutil
from tkinter import font

class VirtualFileSystem:
    def __init__(self, zip_path):
        self.zip_path = zip_path

        # Загружаем zip-архив в оперативную память
        with open(zip_path, 'rb') as f:
            self.zip_memory = io.BytesIO(f.read())

        self.zip_file = zipfile.ZipFile(self.zip_memory, 'r')
        self.current_path = "/"

    def ls(self):
        # Получаем список файлов и папок в текущей директории
        files = []
        for name in self.zip_file.namelist():
            if name.startswith(self.current_path.lstrip('/')):
                relative_path = name[len(self.current_path.lstrip('/')):].strip('/')
                if '/' not in relative_path:
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

        # Создаем новый zip-архив в памяти
        new_zip_memory = io.BytesIO()
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
        sys.exit()

class ShellGUI:
    def __init__(self, vfs):
        self.vfs = vfs
        self.root = tk.Tk()
        self.root.title("Shell Emulator")
        self.root.configure(bg='black')
        self.root.geometry("800x600")

        self.font = font.Font(family="Courier", size=12)

        self.output = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            bg='black',
            fg='white',
            insertbackground='white',
            font=self.font,
            borderwidth=0,
            highlightthickness=0,
            state='disabled'
        )
        self.output.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.input_frame = tk.Frame(self.root, bg='black')
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        self.prompt_label = tk.Label(
            self.input_frame,
            text=f"{self.vfs.pwd()}$ ",
            bg='black',
            fg='white',
            font=self.font
        )
        self.prompt_label.pack(side=tk.LEFT)

        self.input_entry = tk.Entry(
            self.input_frame,
            bg='black',
            fg='white',
            insertbackground='white',
            font=self.font,
            borderwidth=0,
            highlightthickness=0
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_entry.bind("<Return>", self.execute_command)
        self.input_entry.focus_set()

        self.display_prompt()

    def display_prompt(self):
        prompt_text = f"{self.vfs.pwd()}$ "
        self.prompt_label.config(text=prompt_text)

    def execute_command(self, event):
        command = self.input_entry.get()
        self.input_entry.delete(0, tk.END)

        self.append_output(f"{self.vfs.pwd()}$ {command}\n")

        try:
            if command.startswith('ls'):
                files = self.vfs.ls()
                output_text = '\n'.join(files) + '\n'
                self.append_output(output_text)
            elif command.startswith('cd'):
                path = command[3:].strip()
                self.vfs.cd(path)
                self.display_prompt()
            elif command == 'pwd':
                self.append_output(self.vfs.pwd() + '\n')
            elif command.startswith('mv'):
                parts = command.split()
                if len(parts) != 3:
                    raise Exception("Invalid mv command")
                self.vfs.mv(parts[1], parts[2])
            elif command == 'exit':
                self.vfs.exit()
            else:
                self.append_output("Command not found\n")
        except Exception as e:
            self.append_output(f"Error: {e}\n")

    def append_output(self, text):
        self.output.configure(state='normal')
        self.output.insert(tk.END, text)
        self.output.configure(state='disabled')
        self.output.see(tk.END)

    def run(self):
        self.root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="Shell Emulator")
    parser.add_argument('zip_path', help='Path to the virtual file system zip archive')
    args = parser.parse_args()

    vfs = VirtualFileSystem(args.zip_path)
    gui = ShellGUI(vfs)
    gui.run()

if __name__ == '__main__':
    main()
