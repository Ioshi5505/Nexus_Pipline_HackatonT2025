"""
Repository Analyzer
Анализирует структуру Git-репозитория и определяет технологический стек
"""

import os
import re
import tempfile
import shutil
import zipfile
import io
import stat
from typing import Dict, List, Optional
import requests

# Проверяем доступность Git
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    print("⚠️  Git недоступен, используем API режим")

from .tech_stack_detector import TechStackDetector


class RepositoryAnalyzer:
    """
    Класс для анализа Git-репозиториев
    Поддерживает GitHub и GitLab с fallback на API
    """

    def __init__(self):
        """Инициализация анализатора"""
        self.detector = TechStackDetector()
        self.temp_dir = None
        self.git_available = GIT_AVAILABLE

    def analyze_repository(self, url: str) -> Dict:
        """
        Основной метод анализа репозитория

        Args:
            url (str): URL репозитория

        Returns:
            Dict: Результаты анализа
        """
        try:
            # Парсим URL
            repo_info = self._parse_repo_url(url)
            if not repo_info:
                raise ValueError("Неподдерживаемый URL. Поддерживаются GitHub и GitLab")

            print(f"\n📦 Анализ репозитория: {repo_info['full_name']}")
            print(f"🔗 Платформа: {repo_info['platform']}")

            # Получаем файлы
            if self.git_available:
                files = self._clone_and_analyze(url)
            else:
                files = self._download_and_analyze(repo_info)

            print(f"📁 Найдено файлов: {len(files)}")

            # Анализируем технологический стек
            tech_stack = self.detector.detect_tech_stack(files, self.temp_dir)

            # Генерируем рекомендации
            recommendations = self._generate_recommendations(tech_stack, files)

            # Рассчитываем уверенность
            confidence = self._calculate_confidence(tech_stack, files)

            return {
                'repository': repo_info,
                'tech_stack': tech_stack,
                'confidence_level': confidence,
                'recommendations': recommendations,
                'file_structure': files[:100],  # Ограничиваем для отображения
                'analysis_method': 'git' if self.git_available else 'api',
                'temp_dir': self.temp_dir
            }

        except Exception as e:
            raise Exception(f"Ошибка анализа репозитория: {str(e)}")

    def _parse_repo_url(self, url: str) -> Optional[Dict]:
        """Парсит URL репозитория"""
        # GitHub
        github_match = re.search(r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
        if github_match:
            owner, name = github_match.groups()
            return {
                'url': url,
                'platform': 'github',
                'owner': owner,
                'name': name,
                'full_name': f"{owner}/{name}"
            }

        # GitLab
        gitlab_match = re.search(r'gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
        if gitlab_match:
            owner, name = gitlab_match.groups()
            return {
                'url': url,
                'platform': 'gitlab',
                'owner': owner,
                'name': name,
                'full_name': f"{owner}/{name}"
            }

        return None

    def _clone_and_analyze(self, url: str) -> List[Dict]:
        """Клонирует репозиторий через Git"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix='self_deploy_')
            print(f"🔄 Клонируем репозиторий: {url}")

            git.Repo.clone_from(url, self.temp_dir, depth=1)
            print("✅ Репозиторий успешно клонирован")
            return self._analyze_files()

        except Exception as e:
            raise Exception(f"Ошибка клонирования: {str(e)}")

    def _download_and_analyze(self, repo_info: Dict) -> List[Dict]:
        """Загружает репозиторий через API"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix='self_deploy_')
            print(f"🔄 Загружаем через API: {repo_info['full_name']}")

            if repo_info['platform'] == 'github':
                return self._download_github(repo_info)
            elif repo_info['platform'] == 'gitlab':
                return self._download_gitlab(repo_info)
            else:
                raise ValueError("Неподдерживаемая платформа")

        except Exception as e:
            raise Exception(f"Ошибка загрузки через API: {str(e)}")

    def _download_github(self, repo_info: Dict) -> List[Dict]:
        """Загружает GitHub репозиторий"""
        branches = ['main', 'master', 'develop']

        for branch in branches:
            try:
                url = f"https://github.com/{repo_info['owner']}/{repo_info['name']}/archive/refs/heads/{branch}.zip"
                print(f"🔄 Пробуем ветку: {branch}")

                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    print(f"✅ Загружена ветка: {branch}")
                    return self._extract_and_analyze(response.content, repo_info['name'])

            except requests.RequestException:
                continue

        # Fallback на Tree API
        return self._download_github_tree(repo_info)

    def _download_gitlab(self, repo_info: Dict) -> List[Dict]:
        """Загружает GitLab репозиторий"""
        branches = ['main', 'master', 'develop']

        for branch in branches:
            try:
                url = f"https://gitlab.com/{repo_info['owner']}/{repo_info['name']}/-/archive/{branch}/{repo_info['name']}-{branch}.zip"
                print(f"🔄 Пробуем ветку: {branch}")

                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    print(f"✅ Загружена ветка: {branch}")
                    return self._extract_and_analyze(response.content, repo_info['name'])

            except requests.RequestException:
                continue

        raise Exception("Не удалось загрузить ни одну ветку")

    def _download_github_tree(self, repo_info: Dict) -> List[Dict]:
        """Загружает структуру через GitHub Tree API"""
        try:
            url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['name']}/git/trees/HEAD?recursive=1"
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                raise Exception(f"GitHub API ошибка: {response.status_code}")

            data = response.json()
            files = []

            for item in data.get('tree', []):
                path = item['path']

                # Пропускаем служебные файлы
                if self._should_skip_file(path):
                    continue

                file_info = {
                    'name': os.path.basename(path),
                    'type': 'directory' if item['type'] == 'tree' else 'file',
                    'path': '/' + path,
                    'full_path': path
                }

                if item['type'] == 'blob':
                    _, ext = os.path.splitext(file_info['name'])
                    file_info['extension'] = ext
                    file_info['size'] = item.get('size', 0)

                files.append(file_info)

            print(f"✅ Загружено {len(files)} файлов через GitHub Tree API")
            return files

        except Exception as e:
            raise Exception(f"Ошибка GitHub Tree API: {str(e)}")

    def _extract_and_analyze(self, zip_content: bytes, repo_name: str) -> List[Dict]:
        """Распаковывает ZIP и анализирует"""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)

            # Находим распакованную директорию
            dirs = [d for d in os.listdir(self.temp_dir)
                   if os.path.isdir(os.path.join(self.temp_dir, d))]

            if not dirs:
                raise Exception("Не найдена распакованная директория")

            self.temp_dir = os.path.join(self.temp_dir, dirs[0])
            return self._analyze_files()

        except Exception as e:
            raise Exception(f"Ошибка распаковки: {str(e)}")

    def _analyze_files(self) -> List[Dict]:
        """Анализирует файлы в директории"""
        files = []

        for root, dirs, filenames in os.walk(self.temp_dir):
            # Убираем служебные директории
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]

            rel_root = os.path.relpath(root, self.temp_dir)
            if rel_root == '.':
                rel_root = ''

            # Добавляем директории
            for dirname in dirs:
                rel_path = os.path.join(rel_root, dirname) if rel_root else dirname
                files.append({
                    'name': dirname,
                    'type': 'directory',
                    'path': '/' + rel_path.replace('\\', '/'),
                    'full_path': os.path.join(root, dirname)
                })

            # Добавляем файлы
            for filename in filenames:
                if self._should_skip_file(filename):
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.join(rel_root, filename) if rel_root else filename

                _, ext = os.path.splitext(filename)

                try:
                    size = os.path.getsize(file_path)
                except:
                    size = 0

                files.append({
                    'name': filename,
                    'type': 'file',
                    'extension': ext,
                    'path': '/' + rel_path.replace('\\', '/'),
                    'full_path': file_path,
                    'size': size
                })

        print(f"✅ Проанализировано {len(files)} файлов")
        return files

    def _should_skip_dir(self, dirname: str) -> bool:
        """Проверяет, нужно ли пропустить директорию"""
        skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', 'env',
                    'target', 'build', 'dist', '.idea', '.vscode', '.gradle'}
        return dirname.startswith('.') or dirname in skip_dirs

    def _should_skip_file(self, filename: str) -> bool:
        """Проверяет, нужно ли пропустить файл"""
        if filename.startswith('.'):
            # Разрешаем некоторые важные скрытые файлы
            allowed = {'.gitignore', '.env.example', '.dockerignore', '.gitlab-ci.yml'}
            return filename not in allowed
        return False

    def _generate_recommendations(self, tech_stack: Dict, files: List[Dict]) -> List[str]:
        """Генерирует рекомендации"""
        recommendations = []

        # Проверка тестов
        if not tech_stack.get('has_tests', False):
            lang = tech_stack.get('primary_language', '')
            if lang in ['JavaScript', 'TypeScript']:
                recommendations.append("💡 Добавьте тесты с Jest или Mocha")
            elif lang == 'Python':
                recommendations.append("💡 Настройте pytest для тестирования")
            elif lang in ['Java', 'Kotlin']:
                recommendations.append("💡 Используйте JUnit для unit-тестов")
            elif lang == 'Go':
                recommendations.append("💡 Добавьте Go тесты (go test)")

        # Проверка Docker
        if not tech_stack.get('has_dockerfile', False):
            recommendations.append("💡 Создайте Dockerfile для контейнеризации")

        # Проверка CI/CD
        has_gitlab_ci = any('.gitlab-ci.yml' in f.get('name', '') for f in files)
        if not has_gitlab_ci:
            recommendations.append("✅ Будет создан .gitlab-ci.yml пайплайн")

        return recommendations

    def _calculate_confidence(self, tech_stack: Dict, files: List[Dict]) -> float:
        """Рассчитывает уровень уверенности"""
        confidence = 0.4  # Базовый уровень

        # Конфигурационные файлы
        config_files = ['package.json', 'requirements.txt', 'pom.xml', 'build.gradle',
                       'Cargo.toml', 'go.mod', 'pyproject.toml']
        for config_file in config_files:
            if any(f.get('name') == config_file for f in files):
                confidence += 0.15
                break

        # Инструменты сборки
        if tech_stack.get('build_tools'):
            confidence += 0.1

        # Тесты
        if tech_stack.get('has_tests', False):
            confidence += 0.1

        # Фреймворки
        if tech_stack.get('frameworks'):
            confidence += 0.1

        # Основной язык
        if tech_stack.get('primary_language') and tech_stack.get('primary_language') != 'Unknown':
            confidence += 0.15

        return min(confidence, 1.0)

    def _handle_remove_readonly(self, func, path, exc_info):
        """
        Обработчик ошибок для удаления readonly файлов на Windows

        Args:
            func: Функция, которая вызвала ошибку
            path: Путь к файлу
            exc_info: Информация об исключении
        """
        # Если ошибка связана с правами доступа
        if not os.access(path, os.W_OK):
            # Изменяем права доступа
            os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
            # Повторяем попытку удаления
            func(path)
        else:
            raise

    def cleanup(self):
        """Очищает временные файлы"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # Используем onerror для обработки readonly файлов на Windows
                shutil.rmtree(self.temp_dir, onerror=self._handle_remove_readonly)
                self.temp_dir = None
            except Exception:
                # Игнорируем ошибки очистки - временные файлы будут удалены ОС
                # Не выводим ошибку пользователю
                pass

    def __del__(self):
        """Деструктор"""
        self.cleanup()