import argparse
import zipfile
import os
import sys
import shutil
import tempfile
import tkinter as tk
from tkinter import scrolledtext
import unittest
from tkinter import font

class VirtualFileSystem:
    def __init__(self, zip_path):
        self.zip_path = zip_path
        self.temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
        self.current_path = self.temp_dir

    def ls(self):
        return os.listdir(self.current_path)

    def cd(self, path):
        new_path = os.path.normpath(os.path.join(self.current_path, path))
        if os.path.commonpath([self.temp_dir, new_path]) != self.temp_dir:
            raise Exception("Access denied")
        if os.path.isdir(new_path):
            self.current_path = new_path
        else:
            raise FileNotFoundError("Directory not found")

    def pwd(self):
        return os.path.relpath(self.current_path, self.temp_dir)

    def mv(self, src, dst):
        src_path = os.path.join(self.current_path, src)
        dst_path = os.path.join(self.current_path, dst)
        if not os.path.exists(src_path):
            raise FileNotFoundError("Source file not found")
        shutil.move(src_path, dst_path)
        self._update_zip()

    def exit(self):
        shutil.rmtree(self.temp_dir)
        sys.exit()

    def _update_zip(self):
        shutil.make_archive(self.zip_path.replace('.zip', ''), 'zip', self.temp_dir)
        os.remove(self.zip_path)
        shutil.move(self.zip_path.replace('.zip', '') + '.zip', self.zip_path)

class ShellGUI:
    def __init__(self, vfs):
        self.vfs = vfs
        self.root = tk.Tk()
        self.root.title("Shell Emulator")
        self.root.configure(bg='black')
        self.root.geometry("800x600")  # Установка начального размера окна

        # Настройка шрифта: моноширинный для командной строки
        self.font = font.Font(family="Courier", size=12)

        # Создание ScrolledText для вывода с черным фоном и белым текстом
        self.output = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            bg='black',
            fg='white',
            insertbackground='white',  # Цвет курсора (не используется в ScrolledText)
            font=self.font,
            borderwidth=0,
            highlightthickness=0,
            state='disabled'
        )
        self.output.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Создание Frame для ввода команды
        self.input_frame = tk.Frame(self.root, bg='black')
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        # Создание Label для приглашения
        self.prompt_label = tk.Label(
            self.input_frame,
            text=f"{self.vfs.pwd()}$ ",
            bg='black',
            fg='white',
            font=self.font
        )
        self.prompt_label.pack(side=tk.LEFT)

        # Создание Entry для ввода с черным фоном и белым текстом
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
        # Обновить текст приглашения
        prompt_text = f"{self.vfs.pwd()}$ "
        self.prompt_label.config(text=prompt_text)

    def execute_command(self, event):
        command = self.input_entry.get()
        self.input_entry.delete(0, tk.END)

        # Отобразить введенную команду в выводе
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
