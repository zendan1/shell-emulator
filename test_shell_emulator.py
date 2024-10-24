class TestVirtualFileSystem(unittest.TestCase):
    def setUp(self):
        # Создаем временный zip-архив для тестов
        self.test_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.test_dir, 'folder'))
        with open(os.path.join(self.test_dir, 'file.txt'), 'w') as f:
            f.write('Test file')
        self.zip_path = os.path.join(self.test_dir, 'test.zip')
        shutil.make_archive(self.zip_path.replace('.zip', ''), 'zip', self.test_dir)
        self.vfs = VirtualFileSystem(self.zip_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.vfs.temp_dir)

    def test_ls(self):
        self.assertIn('folder', self.vfs.ls())
        self.assertIn('file.txt', self.vfs.ls())

    def test_cd(self):
        self.vfs.cd('folder')
        self.assertEqual(self.vfs.pwd(), 'folder')
        with self.assertRaises(FileNotFoundError):
            self.vfs.cd('nonexistent')

    def test_pwd(self):
        self.assertEqual(self.vfs.pwd(), '.')
        self.vfs.cd('folder')
        self.assertEqual(self.vfs.pwd(), 'folder')

    def test_mv(self):
        self.vfs.mv('file.txt', 'file2.txt')
        self.assertIn('file2.txt', self.vfs.ls())
        self.assertNotIn('file.txt', self.vfs.ls())
        with self.assertRaises(FileNotFoundError):
            self.vfs.mv('nonexistent.txt', 'file3.txt')

    def test_exit(self):
        with self.assertRaises(SystemExit):
            self.vfs.exit()
        self.assertFalse(os.path.exists(self.vfs.temp_dir))

unittest.main(argv=[''], exit=False)
