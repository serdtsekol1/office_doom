#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для аналізу розмірів папок з report.txt
Дозволяє навігацію по папках та отримання їх розмірів
"""

import re
from collections import defaultdict
from pathlib import Path


def parse_size(size_str):
    """Парсить рядок розміру (наприклад, '77 KB' або '2 173 KB') в байти"""
    if not size_str or size_str.strip() == '':
        return 0
    
    size_str = size_str.strip()
    
    # Видаляємо всі пробіли з числа (наприклад, "2 173 KB" -> "2173 KB")
    # Знаходимо число (може містити пробіли як роздільники тисяч) та одиницю виміру
    match = re.match(r'([\d.\s]+)\s*([KMGT]?B?)', size_str, re.IGNORECASE)
    if not match:
        return 0
    
    # Видаляємо пробіли з числа
    value_str = match.group(1).replace(' ', '')
    value = float(value_str)
    unit = match.group(2).upper()
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4
    }
    
    return int(value * multipliers.get(unit, 1))


def normalize_path(path_str):
    """Нормалізує шлях до стандартного формату"""
    if not path_str:
        return ''
    # Замінюємо слеші на стандартні для Windows
    path_str = path_str.replace('/', '\\')
    # Видаляємо подвійні слеші
    while '\\\\' in path_str:
        path_str = path_str.replace('\\\\', '\\')
    # Якщо закінчується на :, додаємо \
    if path_str.endswith(':'):
        path_str += '\\'
    return path_str


class FolderAnalyzer:
    def __init__(self, txt_file):
        import os
        if not os.path.exists(txt_file):
            raise FileNotFoundError(f"Файл {txt_file} не знайдено")
        
        self.txt_file = txt_file
        # Визначаємо тип файлу
        if 'report_2' in txt_file:
            self.file_type = 'partial'
        else:
            self.file_type = 'full'
        
        self.files = {}  # Повний шлях -> розмір
        self.folders = defaultdict(set)  # Папка -> набір файлів/підпапок
        self.folder_sizes = defaultdict(int)  # Папка -> загальний розмір
        # Позиції колонок будуть визначені автоматично при завантаженні
        self.col_positions = None
        self._load_data()
        self._calculate_folder_sizes()
    
    def _detect_column_positions(self, header_line):
        """Автоматично визначає позиції колонок на основі заголовків"""
        name_pos = header_line.find('Name')
        loc_pos = header_line.find('Location')
        mod_pos = header_line.find('Modified')
        size_pos = header_line.find('Size')
        type_pos = header_line.find('Type')
        
        if name_pos == -1 or loc_pos == -1 or mod_pos == -1 or size_pos == -1 or type_pos == -1:
            raise ValueError("Не вдалося визначити позиції колонок")
        
        self.col_positions = {
            'name': (name_pos, loc_pos),
            'location': (loc_pos, mod_pos),
            'modified': (mod_pos, size_pos),
            'size': (size_pos, type_pos),
            'type': (type_pos, None)  # До кінця рядка
        }
    
    def _parse_line(self, line):
        """Парсить рядок з фіксованими позиціями колонок"""
        if self.col_positions is None:
            raise ValueError("Позиції колонок не визначені. Спочатку викличте _detect_column_positions")
        
        name_start, name_end = self.col_positions['name']
        loc_start, loc_end = self.col_positions['location']
        mod_start, mod_end = self.col_positions['modified']
        size_start, size_end = self.col_positions['size']
        type_start, type_end = self.col_positions['type']
        
        name = line[name_start:name_end].strip() if len(line) > name_start else ''
        location = line[loc_start:loc_end].strip() if len(line) > loc_start else ''
        modified = line[mod_start:mod_end].strip() if len(line) > mod_start else ''
        size_str = line[size_start:size_end].strip() if len(line) > size_start else ''
        file_type = line[type_start:].strip() if len(line) > type_start else ''
        
        return {
            'name': name,
            'location': location,
            'modified': modified,
            'size': size_str,
            'type': file_type
        }
    
    def _load_data(self):
        """Завантажує дані з TXT файлу"""
        file_type_label = "повний" if self.file_type == 'full' else "частковий (тільки змінені файли)"
        print(f"Завантаження даних з {self.txt_file} ({file_type_label})...")
        
        try:
            with open(self.txt_file, 'r', encoding='utf-8-sig') as f:
                all_lines = f.readlines()
            
            # Знаходимо рядок з заголовками
            header_line_num = None
            for i, line in enumerate(all_lines):
                if 'Name' in line and 'Location' in line and 'Modified' in line:
                    header_line_num = i
                    break
            
            if header_line_num is None:
                raise ValueError("Не знайдено заголовки в файлі")
            
            # Визначаємо позиції колонок на основі заголовків
            header_line = all_lines[header_line_num]
            self._detect_column_positions(header_line)
            
            # Спочатку підраховуємо загальний розмір зі звіту
            total_size_from_report = 0
            for line in all_lines[header_line_num + 2:]:  # Пропускаємо заголовок і порожній рядок
                line = line.rstrip('\n')
                if not line.strip():
                    continue
                
                row = self._parse_line(line)
                size_str = row['size']
                file_type = row['type']
                
                # Якщо це не папка і є розмір, додаємо до загального
                if file_type != 'File Folder' and size_str:
                    total_size_from_report += parse_size(size_str)
            
            print(f"Загальний розмір зі звіту (сума всіх файлів): {self.format_size(total_size_from_report)}")
            
            # Обробляємо дані починаючи з наступного рядка після заголовків
            count = 0
            files_without_size = 0
            total_size_from_txt = 0
            
            for line in all_lines[header_line_num + 2:]:  # Пропускаємо заголовок і порожній рядок
                line = line.rstrip('\n')
                # Пропускаємо порожні рядки
                if not line.strip():
                    continue
                
                # Парсимо рядок
                row = self._parse_line(line)
                
                name = row['name']
                location = row['location']
                size_str = row['size']
                file_type = row['type']
                
                if not name:
                    continue
                
                # Нормалізуємо шляхи
                location = normalize_path(location)
                
                # Формуємо повний шлях
                if location:
                    full_path = normalize_path(str(Path(location) / name))
                else:
                    full_path = normalize_path(name)
                
                # Визначаємо чи це файл чи папка
                # Якщо Type = "File Folder" - це точно папка
                # В іншому випадку - це файл (навіть якщо розмір порожній)
                is_folder = (file_type == 'File Folder')
                
                if not is_folder and not size_str:
                    # Файл без розміру
                    files_without_size += 1
                elif not is_folder and size_str:
                    # Файл з розміром
                    total_size_from_txt += parse_size(size_str)
                
                if is_folder:
                    # Це папка
                    self.folders[location].add(name)
                    # Також додаємо папку як можливий шлях для обчислення розміру
                    self.folder_sizes[full_path] = 0
                    
                    # Додаємо папку до всіх батьківських папок
                    path_obj = Path(full_path)
                    for parent in path_obj.parents:
                        parent_str = normalize_path(str(parent))
                        if parent_str and parent_str != full_path:
                            # Знаходимо ім'я папки відносно батьківської
                            try:
                                relative_name = path_obj.relative_to(parent).parts[0]
                                self.folders[parent_str].add(relative_name)
                            except (ValueError, IndexError):
                                pass
                else:
                    # Це файл
                    size = parse_size(size_str)
                    if not size_str:
                        files_without_size += 1
                    else:
                        total_size_from_txt += size
                    # Додаємо файл навіть якщо розмір = 0 (може бути порожній файл)
                    self.files[full_path] = size
                    self.folders[location].add(name)
                
                count += 1
                if count % 10000 == 0:
                    print(f"Оброблено {count} записів...")
            
            # Підраховуємо загальний розмір всіх файлів
            total_files_size = sum(self.files.values())
            
            print(f"Завантажено {count} записів")
            print(f"Знайдено {len(self.files)} файлів та {len([k for k, v in self.folders.items() if v])} папок")
            print(f"Загальний розмір всіх файлів: {self.format_size(total_files_size)}")
            print(f"Діагностика:")
            print(f"  - Файлів без розміру: {files_without_size}")
            print(f"  - Розмір з файлу (до парсингу): {self.format_size(total_size_from_txt)}")
            if self.file_type == 'full':
                print(f"  - Очікуваний розмір: 96.52 GB")
            else:
                print(f"  - Примітка: це частковий звіт (тільки змінені файли)")
        
        except Exception as e:
            print(f"Помилка при завантаженні: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _calculate_folder_sizes(self):
        """Обчислює розміри всіх папок"""
        print("Обчислення розмірів папок...")
        
        # Додаємо розміри файлів до всіх батьківських папок (рекурсивно)
        for file_path, size in self.files.items():
            path = Path(file_path)
            # Додаємо розмір до всіх батьківських папок
            for parent in path.parents:
                parent_str = normalize_path(str(parent))
                if parent_str:  # Пропускаємо корінь
                    self.folder_sizes[parent_str] += size
            
            # Додаємо розмір до безпосередньої папки файлу
            if path.parent:
                parent_str = normalize_path(str(path.parent))
                self.folder_sizes[parent_str] += size
    
    def get_folder_contents(self, folder_path):
        """Повертає вміст папки (файли та підпапки) з розмірами"""
        folder_path = normalize_path(folder_path)
        
        contents = []
        seen_items = set()  # Щоб уникнути дублікатів
        
        # Знаходимо всі файли та папки в цій папці (прямі дочірні елементи)
        for item_name in self.folders.get(folder_path, set()):
            if folder_path:
                item_path = normalize_path(str(Path(folder_path) / item_name))
            else:
                item_path = normalize_path(item_name)
            
            if item_path in seen_items:
                continue
            seen_items.add(item_path)
            
            # Перевіряємо чи це файл
            if item_path in self.files:
                size = self.files[item_path]
                contents.append(('file', item_name, size))
            else:
                # Це папка, обчислюємо її розмір
                # Перевіряємо чи папка існує в folder_sizes (навіть якщо розмір = 0)
                if item_path in self.folder_sizes:
                    size = self.folder_sizes[item_path]
                else:
                    # Якщо папки немає в folder_sizes, але вона є в folders, значить вона порожня
                    size = 0
                contents.append(('folder', item_name, size))
        
        # Також шукаємо всі папки та файли, які знаходяться всередині заданої папки
        # (на будь-якому рівні вкладеності), але показуємо тільки перший рівень
        folder_path_with_slash = folder_path.rstrip('\\') + '\\'
        
        # Шукаємо всі папки та файли, які починаються з folder_path
        all_paths = set(self.folder_sizes.keys()) | set(self.files.keys())
        
        for path in all_paths:
            path_normalized = normalize_path(path)
            if path_normalized.startswith(folder_path_with_slash) and path_normalized != folder_path:
                # Знаходимо перший рівень після folder_path
                relative_path = path_normalized[len(folder_path_with_slash):]
                if not relative_path:
                    continue
                first_level = relative_path.split('\\')[0]
                
                if first_level:
                    first_level_path = normalize_path(str(Path(folder_path) / first_level))
                    if first_level_path not in seen_items:
                        seen_items.add(first_level_path)
                        # Перевіряємо чи це файл
                        if first_level_path in self.files:
                            size = self.files[first_level_path]
                            contents.append(('file', first_level, size))
                        else:
                            # Це папка
                            size = self.folder_sizes.get(first_level_path, 0)
                            contents.append(('folder', first_level, size))
        
        return contents
    
    def format_size(self, size_bytes):
        """Форматує розмір в читабельний вигляд"""
        if size_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def list_folder(self, folder_path):
        """Виводить вміст папки"""
        folder_path = normalize_path(folder_path)
        contents = self.get_folder_contents(folder_path)
        
        # Перевіряємо чи папка існує
        # Папка існує якщо:
        # 1. Вона в folder_sizes (має розрахований розмір)
        # 2. Вона в folders (має дочірні елементи)
        # 3. Вона є батьківською для якогось файлу
        folder_exists = (folder_path in self.folder_sizes or 
                        folder_path in self.folders or
                        any(normalize_path(str(Path(p).parent)) == folder_path for p in self.files.keys()))
        
        if not contents and not folder_exists:
            print(f"Папка '{folder_path}' не знайдена")
            return
        
        if not contents:
            # Папка існує, але порожня
            total_size = self.folder_sizes.get(folder_path, 0)
            print(f"\nВміст папки: {folder_path}")
            print("=" * 80)
            print("Папка порожня")
            print("-" * 80)
            print(f"{'ЗАГАЛЬНИЙ РОЗМІР (рекурсивно):':<70} {self.format_size(total_size)}")
            print()
            return
        
        # Сортуємо за розміром (від більшого до меншого)
        contents.sort(key=lambda x: x[2], reverse=True)
        
        # Загальний розмір папки - це рекурсивний розмір з folder_sizes
        total_size = self.folder_sizes.get(folder_path, 0)
        
        print(f"\nВміст папки: {folder_path}")
        print("=" * 80)
        print(f"{'Тип':<10} {'Назва':<60} {'Розмір':<15}")
        print("-" * 80)
        
        for item_type, name, size in contents:
            type_label = '[ПАПКА]' if item_type == 'folder' else '[ФАЙЛ]'
            print(f"{type_label:<10} {name:<60} {self.format_size(size):<15}")
        
        print("-" * 80)
        print(f"{'ЗАГАЛЬНИЙ РОЗМІР (рекурсивно):':<70} {self.format_size(total_size)}")
        print()
    
    def get_sorted_folders(self, min_size=0):
        """Повертає список папок, відсортований за розміром"""
        folders_with_sizes = [
            (path, size) for path, size in self.folder_sizes.items()
            if size >= min_size
        ]
        folders_with_sizes.sort(key=lambda x: x[1], reverse=True)
        return folders_with_sizes
    
    def show_top_folders(self, top_n=20):
        """Показує топ N папок за розміром"""
        sorted_folders = self.get_sorted_folders()
        
        print(f"\nТоп {top_n} папок за розміром:")
        print("=" * 80)
        print(f"{'№':<5} {'Шлях':<60} {'Розмір':<15}")
        print("-" * 80)
        
        for i, (path, size) in enumerate(sorted_folders[:top_n], 1):
            print(f"{i:<5} {path:<60} {self.format_size(size):<15}")
        print()
    
    def get_folder_size(self, folder_path):
        """Повертає розмір папки"""
        folder_path = normalize_path(folder_path)
        return self.folder_sizes.get(folder_path, 0)
    
    def __getitem__(self, key):
        """Дозволяє використовувати синтаксис analyzer['C:\\Users']"""
        if isinstance(key, str):
            # Якщо це простий шлях
            path = normalize_path(key)
            self.list_folder(path)
            return self
        return None


class PathNavigator:
    """Клас для зручної навігації по шляхам через атрибути"""
    def __init__(self, analyzer, base_path=''):
        self.analyzer = analyzer
        self.base_path = normalize_path(base_path)
    
    def __getattr__(self, name):
        """Дозволяє використовувати C.User_Data замість C['User Data']"""
        # Замінюємо підкреслення на пробіли
        folder_name = name.replace('_', ' ')
        new_path = normalize_path(str(Path(self.base_path) / folder_name))
        return PathNavigator(self.analyzer, new_path)
    
    def __getitem__(self, key):
        """Дозволяє використовувати C['User Data']"""
        new_path = normalize_path(str(Path(self.base_path) / key))
        return PathNavigator(self.analyzer, new_path)
    
    def __call__(self, *args, **kwargs):
        """Виклик об'єкта показує вміст папки"""
        self.analyzer.list_folder(self.base_path)
        return self
    
    def __repr__(self):
        """Показує поточний шлях"""
        return f"<PathNavigator: {self.base_path}>"


def select_report_file():
    """Знаходить всі txt файли в поточній папці та дозволяє користувачу вибрати"""
    import os
    import glob
    
    # Знаходимо всі txt файли в поточній папці
    txt_files = [f for f in glob.glob('*.txt') if os.path.isfile(f)]
    
    if not txt_files:
        raise FileNotFoundError("Не знайдено жодного txt файлу в поточній папці")
    
    # Показуємо список файлів
    print("\n" + "=" * 80)
    print("ДОСТУПНІ ФАЙЛИ ЗВІТІВ:")
    print("=" * 80)
    for i, filename in enumerate(txt_files, 1):
        file_size = os.path.getsize(filename)
        size_mb = file_size / (1024 * 1024)
        print(f"  {i}. {filename} ({size_mb:.2f} MB)")
    print("=" * 80)
    
    # Запитуємо вибір користувача
    while True:
        try:
            choice = input(f"\nВиберіть файл (1-{len(txt_files)}) або введіть назву файлу: ").strip()
            
            # Спробуємо інтерпретувати як число
            try:
                file_index = int(choice) - 1
                if 0 <= file_index < len(txt_files):
                    selected_file = txt_files[file_index]
                    print(f"Вибрано: {selected_file}\n")
                    return selected_file
                else:
                    print(f"Будь ласка, введіть число від 1 до {len(txt_files)}")
            except ValueError:
                # Якщо не число, спробуємо як назву файлу
                if choice in txt_files:
                    print(f"Вибрано: {choice}\n")
                    return choice
                elif os.path.exists(choice):
                    print(f"Вибрано: {choice}\n")
                    return choice
                else:
                    print(f"Файл '{choice}' не знайдено. Спробуйте ще раз.")
        except KeyboardInterrupt:
            print("\n\nСкасовано.")
            raise
        except Exception as e:
            print(f"Помилка: {e}. Спробуйте ще раз.")


def main():
    """Головна функція з інтерактивним інтерфейсом"""
    # Спочатку вибираємо файл
    try:
        selected_file = select_report_file()
    except FileNotFoundError as e:
        print(f"Помилка: {e}")
        return
    except KeyboardInterrupt:
        return
    
    # Завантажуємо дані
    import os
    import glob
    txt_files = [f for f in glob.glob('*.txt') if os.path.isfile(f)]
    failed_files = []
    
    while True:
        try:
            analyzer = FolderAnalyzer(selected_file)
            break  # Якщо успішно завантажили, виходимо з циклу
        except Exception as e:
            failed_files.append(selected_file)
            print(f"\nПомилка при завантаженні файлу '{selected_file}': {e}")
            
            # Перевіряємо чи є інші txt файли для спроби
            remaining_files = [f for f in txt_files if f not in failed_files]
            
            if not remaining_files:
                print("\nВсі доступні txt файли не підходять. Можливо, вони мають неправильний формат.")
                print("Перевірте, чи файли містять колонки: Name, Location, Modified, Size, Type")
                return
            
            print(f"\nДоступні файли для спроби: {', '.join(remaining_files)}")
            retry = input("Спробувати інший файл? (y/n): ").strip().lower()
            
            if retry == 'y' or retry == 'yes' or retry == 'так':
                # Показуємо список знову
                print("\n" + "=" * 80)
                print("ДОСТУПНІ ФАЙЛИ ЗВІТІВ:")
                print("=" * 80)
                for i, filename in enumerate(remaining_files, 1):
                    file_size = os.path.getsize(filename)
                    size_mb = file_size / (1024 * 1024)
                    print(f"  {i}. {filename} ({size_mb:.2f} MB)")
                print("=" * 80)
                
                choice = input(f"\nВиберіть файл (1-{len(remaining_files)}) або введіть назву файлу: ").strip()
                try:
                    file_index = int(choice) - 1
                    if 0 <= file_index < len(remaining_files):
                        selected_file = remaining_files[file_index]
                    else:
                        print("Невірний вибір. Спробуйте ще раз.")
                        return
                except ValueError:
                    if choice in remaining_files:
                        selected_file = choice
                    elif os.path.exists(choice):
                        selected_file = choice
                    else:
                        print("Файл не знайдено.")
                        return
            else:
                print("Скасовано.")
                return
    
    # Створюємо навігатор для зручного доступу
    # C буде вказувати на C:\
    C = PathNavigator(analyzer, 'C:\\')
    
    print("\n" + "=" * 80)
    print("АНАЛІЗАТОР РОЗМІРІВ ПАПОК")
    print("=" * 80)
    print("\nКоманди:")
    print("  <шлях>           - показати вміст папки (наприклад: C: або C:\\Users)")
    print("  C()              - показати вміст C:\\")
    print("  C['User Data']() - показати вміст C:\\User Data")
    print("  C.Users()        - показати вміст C:\\Users (пробіли замінюються на _)")
    print("  top [N]          - показати топ N папок за розміром (за замовчуванням 20)")
    print("  help             - показати цю довідку")
    print("  exit або quit    - вийти")
    print("\nПриклади:")
    print("  C:               - показати вміст C:\\")
    print("  C()              - показати вміст C:\\")
    print("  C['Users']()     - показати вміст C:\\Users")
    print("  C.Program_Files() - показати вміст C:\\Program Files")
    print("  top 50           - показати топ 50 папок")
    print("=" * 80)
    print()
    
    python_mode = False
    
    while True:
        try:
            if python_mode:
                command = input("py> ").strip()
            else:
                command = input("> ").strip()
            
            if not command:
                continue
            
            if command.lower() in ['exit', 'quit', 'q']:
                print("До побачення!")
                break
            
            if command.lower() in ['python', 'py']:
                python_mode = True
                print("Режим Python увімкнено. Використовуйте C(), C['папка'](), тощо")
                print("Для виходу з режиму введіть 'exit' або 'normal'")
                continue
            
            if command.lower() == 'normal':
                python_mode = False
                print("Повернутося до звичайного режиму")
                continue
            
            if command.lower() == 'help':
                print("\nКоманди:")
                print("  <шлях>           - показати вміст папки")
                print("  top [N]          - показати топ N папок за розміром")
                print("  help             - показати довідку")
                print("  python або py    - увімкнути Python режим")
                print("  exit або quit    - вийти")
                print()
                continue
            
            if command.lower().startswith('top'):
                parts = command.split()
                top_n = int(parts[1]) if len(parts) > 1 else 20
                analyzer.show_top_folders(top_n)
                continue
            
            # Перевіряємо чи це синтаксис C['папка'] або C.папка або C()
            is_python_syntax = (command.startswith("C[") or 
                               command.startswith("C.") or 
                               command == "C()" or
                               (command.startswith("C(") and ')' in command))
            
            if python_mode or is_python_syntax:
                # Виконуємо команду як Python код
                try:
                    # Додаємо analyzer та C в контекст
                    if is_python_syntax and not command.endswith('()') and '(' not in command:
                        # Якщо команда не закінчується на (), додаємо виклик
                        if command.startswith('C[') or command.startswith('C.'):
                            command = command + '()'
                    result = eval(command, {'analyzer': analyzer, 'C': C, '__builtins__': __builtins__})
                    if result is not None and result != C:
                        print(result)
                except Exception as e:
                    print(f"Помилка виконання: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                # Обробка шляху
                folder_path = command
                analyzer.list_folder(folder_path)
        
        except KeyboardInterrupt:
            print("\n\nДо побачення!")
            break
        except Exception as e:
            print(f"Помилка: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
