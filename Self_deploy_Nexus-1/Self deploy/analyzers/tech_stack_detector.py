"""
Tech Stack Detector
Улучшенный анализ с подсчетом строк кода и точным определением фреймворков
Поддержка 4 базовых языков: Java/Kotlin, Go, TypeScript/JavaScript, Python
"""

import os
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Optional
from collections import defaultdict


class TechStackDetector:
    """
    Улучшенный класс для определения технологического стека проекта
    Обязательная поддержка: Java/Kotlin, Go, TypeScript/JavaScript, Python
    """

    def __init__(self):
        """Инициализация детектора"""
        # Расширения файлов и соответствующие языки
        self.language_extensions = {
            # JavaScript/TypeScript
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.mjs': 'JavaScript',
            '.cjs': 'JavaScript',

            # Python
            '.py': 'Python',
            '.pyw': 'Python',
            '.pyx': 'Python',

            # Java/Kotlin
            '.java': 'Java',
            '.kt': 'Kotlin',
            '.kts': 'Kotlin',

            # Go
            '.go': 'Go',

            # Дополнительные языки
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.cc': 'C++',
            '.cxx': 'C++',
            '.c': 'C',
            '.h': 'C/C++',
            '.hpp': 'C++',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.scala': 'Scala',
            '.dart': 'Dart',
        }

        # Версии по умолчанию для базовых языков
        self.default_versions = {
            'Java': '11',
            'Kotlin': '1.8',
            'Go': '1.19',
            'TypeScript': '5.0',
            'JavaScript': 'ES2022',
            'Python': '3.9'
        }

    def detect_tech_stack(self, file_structure: List[Dict], project_dir: Optional[str] = None) -> Dict:
        """
        Улучшенное определение технологического стека

        Args:
            file_structure: Список файлов проекта
            project_dir: Путь к директории проекта

        Returns:
            Dict: Детальная информация о технологическом стеке
        """
        # Подсчитываем строки кода по языкам
        language_stats = self._count_lines_by_language(file_structure, project_dir)

        # Определяем основной язык
        primary_language = self._detect_primary_language(language_stats)

        # Определяем версию языка/фреймворка
        version_info = self._detect_versions(file_structure, project_dir, primary_language)

        # Определяем фреймворки
        frameworks = self._detect_frameworks(file_structure, project_dir, primary_language)

        # Определяем инструменты сборки
        build_tools = self._detect_build_tools(file_structure)

        # Определяем менеджеры пакетов
        package_managers = self._detect_package_managers(build_tools)

        # Проверяем наличие тестов
        has_tests = self._check_tests(file_structure)

        # Проверяем Docker
        has_dockerfile = self._check_dockerfile(file_structure)

        return {
            'primary_language': primary_language,
            'language_stats': language_stats,
            'version_info': version_info,
            'frameworks': frameworks,
            'build_tools': build_tools,
            'package_managers': package_managers,
            'has_tests': has_tests,
            'has_dockerfile': has_dockerfile
        }

    def _count_lines_by_language(self, file_structure: List[Dict], project_dir: Optional[str]) -> Dict:
        """
        Подсчитывает строки кода по языкам программирования

        Returns:
            Dict: Статистика по языкам с процентами
        """
        language_lines = defaultdict(int)
        total_lines = 0

        for file_info in file_structure:
            if file_info.get('type') != 'file':
                continue

            extension = file_info.get('extension', '').lower()
            if extension not in self.language_extensions:
                continue

            language = self.language_extensions[extension]

            # Подсчитываем строки в файле
            lines_count = self._count_file_lines(file_info, project_dir)
            if lines_count > 0:
                language_lines[language] += lines_count
                total_lines += lines_count

        # Вычисляем проценты
        language_stats = {}
        if total_lines > 0:
            for language, lines in language_lines.items():
                percentage = round((lines / total_lines) * 100, 1)
                language_stats[language] = {
                    'lines': lines,
                    'percentage': percentage
                }

        # Сортируем по количеству строк
        language_stats = dict(sorted(language_stats.items(),
                                   key=lambda x: x[1]['lines'],
                                   reverse=True))

        return language_stats

    def _count_file_lines(self, file_info: Dict, project_dir: Optional[str]) -> int:
        """
        Подсчитывает значимые строки кода в файле (исключая пустые строки)
        """
        try:
            # Определяем путь к файлу
            if project_dir and file_info.get('full_path'):
                file_path = file_info['full_path']
            else:
                return 0

            if not os.path.exists(file_path):
                return 0

            # Ограничиваем размер файла для анализа (максимум 1MB)
            if os.path.getsize(file_path) > 1024 * 1024:
                return 0

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Считаем непустые строки
            significant_lines = sum(1 for line in lines if line.strip())

            return significant_lines

        except Exception:
            return 0

    def _detect_primary_language(self, language_stats: Dict) -> str:
        """
        Определяет основной язык программирования
        """
        if not language_stats:
            return 'Unknown'

        # Исключаем конфигурационные языки при определении основного
        exclude_languages = {'JSON', 'YAML', 'XML', 'Markdown', 'HTML', 'CSS'}

        for language, stats in language_stats.items():
            if language not in exclude_languages:
                return language

        # Если остались только конфигурационные файлы
        return list(language_stats.keys())[0] if language_stats else 'Unknown'

    def _detect_versions(self, file_structure: List[Dict], project_dir: Optional[str],
                        primary_language: str) -> Dict:
        """
        Определяет версии языка программирования и фреймворков
        """
        version_info = {
            'language_version': self.default_versions.get(primary_language, 'latest'),
            'framework_versions': {}
        }

        # Java - из pom.xml или build.gradle
        if primary_language == 'Java':
            pom_path = self._find_file(file_structure, 'pom.xml')
            if pom_path and project_dir:
                java_version = self._extract_java_version_from_pom(pom_path)
                if java_version:
                    version_info['language_version'] = java_version

            gradle_path = self._find_file(file_structure, 'build.gradle')
            if gradle_path and project_dir:
                java_version = self._extract_java_version_from_gradle(gradle_path)
                if java_version:
                    version_info['language_version'] = java_version

        # Go - из go.mod
        elif primary_language == 'Go':
            go_mod_path = self._find_file(file_structure, 'go.mod')
            if go_mod_path and project_dir:
                go_version = self._extract_go_version(go_mod_path)
                if go_version:
                    version_info['language_version'] = go_version

        # Python - из pyproject.toml или runtime.txt
        elif primary_language == 'Python':
            pyproject_path = self._find_file(file_structure, 'pyproject.toml')
            if pyproject_path and project_dir:
                python_version = self._extract_python_version_from_pyproject(pyproject_path)
                if python_version:
                    version_info['language_version'] = python_version

        # TypeScript/JavaScript - из package.json
        elif primary_language in ['TypeScript', 'JavaScript']:
            package_json_path = self._find_file(file_structure, 'package.json')
            if package_json_path and project_dir:
                node_version = self._extract_node_version(package_json_path)
                if node_version:
                    version_info['language_version'] = node_version

        return version_info

    def _detect_frameworks(self, file_structure: List[Dict], project_dir: Optional[str],
                          primary_language: str) -> List[str]:
        """
        Улучшенное определение фреймворков через анализ зависимостей
        """
        frameworks = set()

        # Анализируем package.json для JavaScript/TypeScript проектов
        if primary_language in ['JavaScript', 'TypeScript']:
            package_json_path = self._find_file(file_structure, 'package.json')
            if package_json_path and project_dir:
                js_frameworks = self._analyze_package_json(package_json_path)
                frameworks.update(js_frameworks)

        # Анализируем requirements.txt для Python проектов
        elif primary_language == 'Python':
            requirements_path = self._find_file(file_structure, 'requirements.txt')
            if requirements_path and project_dir:
                python_frameworks = self._analyze_requirements_txt(requirements_path)
                frameworks.update(python_frameworks)

            # Также проверяем pyproject.toml
            pyproject_path = self._find_file(file_structure, 'pyproject.toml')
            if pyproject_path and project_dir:
                python_frameworks = self._analyze_pyproject_toml(pyproject_path)
                frameworks.update(python_frameworks)

        # Анализируем pom.xml для Java проектов
        elif primary_language in ['Java', 'Kotlin']:
            pom_xml_path = self._find_file(file_structure, 'pom.xml')
            if pom_xml_path and project_dir:
                java_frameworks = self._analyze_pom_xml(pom_xml_path)
                frameworks.update(java_frameworks)

            # Также проверяем build.gradle
            gradle_path = self._find_file(file_structure, 'build.gradle')
            if gradle_path and project_dir:
                java_frameworks = self._analyze_gradle(gradle_path)
                frameworks.update(java_frameworks)

        # Анализируем go.mod для Go проектов
        elif primary_language == 'Go':
            go_mod_path = self._find_file(file_structure, 'go.mod')
            if go_mod_path and project_dir:
                go_frameworks = self._analyze_go_mod(go_mod_path)
                frameworks.update(go_frameworks)

        # Дополнительный анализ по структуре файлов
        file_based_frameworks = self._analyze_by_file_structure(file_structure)
        frameworks.update(file_based_frameworks)

        return sorted(list(frameworks))

    def _find_file(self, file_structure: List[Dict], filename: str) -> Optional[str]:
        """Находит путь к файлу в структуре проекта"""
        for file_info in file_structure:
            if file_info.get('name') == filename:
                return file_info.get('full_path')
        return None

    def _extract_java_version_from_pom(self, file_path: str) -> Optional[str]:
        """Извлекает версию Java из pom.xml"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Ищем maven.compiler.source или java.version
            namespace = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            properties = root.find('.//maven:properties', namespace) or root.find('.//properties')

            if properties is not None:
                for prop in properties:
                    if 'java.version' in prop.tag or 'maven.compiler.source' in prop.tag:
                        return prop.text

            return None
        except:
            return None

    def _extract_java_version_from_gradle(self, file_path: str) -> Optional[str]:
        """Извлекает версию Java из build.gradle"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ищем sourceCompatibility или targetCompatibility
            match = re.search(r'sourceCompatibility\s*=\s*["\']?(\d+(?:\.\d+)?)["\']?', content)
            if match:
                return match.group(1)

            match = re.search(r'JavaVersion\.VERSION_(\d+)', content)
            if match:
                return match.group(1)

            return None
        except:
            return None

    def _extract_go_version(self, file_path: str) -> Optional[str]:
        """Извлекает версию Go из go.mod"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            match = re.search(r'go\s+(\d+\.\d+(?:\.\d+)?)', content)
            if match:
                return match.group(1)

            return None
        except:
            return None

    def _extract_python_version_from_pyproject(self, file_path: str) -> Optional[str]:
        """Извлекает версию Python из pyproject.toml"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ищем python version в requires-python
            match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version_spec = match.group(1)
                # Извлекаем версию из спецификации типа ">=3.9"
                version_match = re.search(r'(\d+\.\d+)', version_spec)
                if version_match:
                    return version_match.group(1)

            return None
        except:
            return None

    def _extract_node_version(self, file_path: str) -> Optional[str]:
        """Извлекает версию Node.js из package.json"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Проверяем engines.node
            engines = data.get('engines', {})
            if 'node' in engines:
                node_version = engines['node']
                # Извлекаем версию из спецификации типа ">=18.0.0"
                version_match = re.search(r'(\d+(?:\.\d+)?)', node_version)
                if version_match:
                    return version_match.group(1)

            return None
        except:
            return None

    def _analyze_package_json(self, file_path: str) -> Set[str]:
        """Анализирует package.json для определения JavaScript/TypeScript фреймворков"""
        frameworks = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            dependencies = {}
            dependencies.update(data.get('dependencies', {}))
            dependencies.update(data.get('devDependencies', {}))

            # Детальное сопоставление фреймворков
            framework_mapping = {
                'react': 'React',
                '@types/react': 'React',
                'react-dom': 'React',
                'react-scripts': 'React',
                'next': 'Next.js',
                'nuxt': 'Nuxt.js',
                'vue': 'Vue.js',
                '@vue/cli': 'Vue.js',
                '@angular/core': 'Angular',
                'svelte': 'Svelte',
                'express': 'Express.js',
                'koa': 'Koa',
                'fastify': 'Fastify',
                '@nestjs/core': 'NestJS',
                'typescript': 'TypeScript',
                'webpack': 'Webpack',
                'vite': 'Vite',
                'jest': 'Jest',
                'mocha': 'Mocha',
                'cypress': 'Cypress'
            }

            for dep_name, framework_name in framework_mapping.items():
                if dep_name in dependencies:
                    frameworks.add(framework_name)

        except:
            pass

        return frameworks

    def _analyze_requirements_txt(self, file_path: str) -> Set[str]:
        """Анализирует requirements.txt для Python фреймворков"""
        frameworks = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            framework_mapping = {
                'django': 'Django',
                'flask': 'Flask',
                'fastapi': 'FastAPI',
                'tornado': 'Tornado',
                'sanic': 'Sanic',
                'starlette': 'Starlette',
                'aiohttp': 'aiohttp',
                'streamlit': 'Streamlit',
                'pandas': 'Pandas',
                'numpy': 'NumPy',
                'tensorflow': 'TensorFlow',
                'pytorch': 'PyTorch',
                'torch': 'PyTorch',
                'pytest': 'pytest',
                'unittest': 'unittest'
            }

            for line in lines:
                line = line.strip().lower()
                if line and not line.startswith('#'):
                    package_name = re.split(r'[><=!]', line)[0].strip()

                    for framework_key, framework_name in framework_mapping.items():
                        if framework_key in package_name:
                            frameworks.add(framework_name)

        except:
            pass

        return frameworks

    def _analyze_pyproject_toml(self, file_path: str) -> Set[str]:
        """Анализирует pyproject.toml для Python фреймворков"""
        frameworks = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            framework_mapping = {
                'django': 'Django',
                'flask': 'Flask',
                'fastapi': 'FastAPI',
                'poetry': 'Poetry'
            }

            for framework_key, framework_name in framework_mapping.items():
                if framework_key in content.lower():
                    frameworks.add(framework_name)

        except:
            pass

        return frameworks

    def _analyze_pom_xml(self, file_path: str) -> Set[str]:
        """Анализирует pom.xml для Java фреймворков"""
        frameworks = set()

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            namespace = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            dependencies = root.findall('.//maven:dependency', namespace) or root.findall('.//dependency')

            framework_mapping = {
                'spring-boot': 'Spring Boot',
                'spring-core': 'Spring Framework',
                'spring-web': 'Spring Web',
                'hibernate': 'Hibernate',
                'junit': 'JUnit',
                'mockito': 'Mockito'
            }

            for dependency in dependencies:
                artifact_id = dependency.find('artifactId') or dependency.find('.//{http://maven.apache.org/POM/4.0.0}artifactId')

                if artifact_id is not None:
                    artifact_name = artifact_id.text.lower()
                    for framework_key, framework_name in framework_mapping.items():
                        if framework_key in artifact_name:
                            frameworks.add(framework_name)

        except:
            pass

        return frameworks

    def _analyze_gradle(self, file_path: str) -> Set[str]:
        """Анализирует build.gradle для Java/Kotlin фреймворков"""
        frameworks = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            framework_mapping = {
                'spring-boot': 'Spring Boot',
                'spring': 'Spring Framework',
                'hibernate': 'Hibernate',
                'junit': 'JUnit',
                'kotlin': 'Kotlin'
            }

            for framework_key, framework_name in framework_mapping.items():
                if framework_key in content.lower():
                    frameworks.add(framework_name)

        except:
            pass

        return frameworks

    def _analyze_go_mod(self, file_path: str) -> Set[str]:
        """Анализирует go.mod для Go фреймворков"""
        frameworks = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            framework_mapping = {
                'gin-gonic/gin': 'Gin',
                'gorilla/mux': 'Gorilla Mux',
                'labstack/echo': 'Echo',
                'fiber': 'Fiber',
                'gorm.io/gorm': 'GORM',
                'go-chi/chi': 'Chi'
            }

            for framework_key, framework_name in framework_mapping.items():
                if framework_key in content:
                    frameworks.add(framework_name)

        except:
            pass

        return frameworks

    def _analyze_by_file_structure(self, file_structure: List[Dict]) -> Set[str]:
        """Анализирует фреймворки по структуре файлов"""
        frameworks = set()

        # Собираем все пути файлов
        file_paths = [f.get('path', '') for f in file_structure if f.get('type') == 'file']

        # React проекты
        if any('.jsx' in path or '.tsx' in path for path in file_paths):
            frameworks.add('React')

        # Vue проекты
        if any('.vue' in path for path in file_paths):
            frameworks.add('Vue.js')

        # Django проекты
        if any('manage.py' in path or 'settings.py' in path for path in file_paths):
            frameworks.add('Django')

        return frameworks

    def _detect_build_tools(self, file_structure: List[Dict]) -> List[str]:
        """Определяет инструменты сборки"""
        tools = set()

        file_mapping = {
            'package.json': 'npm',
            'yarn.lock': 'yarn',
            'pnpm-lock.yaml': 'pnpm',
            'requirements.txt': 'pip',
            'pyproject.toml': 'poetry',
            'Pipfile': 'pipenv',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'build.gradle.kts': 'gradle',
            'Cargo.toml': 'cargo',
            'go.mod': 'go',
            'Makefile': 'make',
            'webpack.config.js': 'webpack',
            'vite.config.js': 'vite',
            'vite.config.ts': 'vite'
        }

        for file_info in file_structure:
            if file_info.get('type') == 'file':
                name = file_info.get('name', '')
                if name in file_mapping:
                    tools.add(file_mapping[name])

        return sorted(list(tools))

    def _detect_package_managers(self, build_tools: List[str]) -> List[str]:
        """Определяет менеджеры пакетов из инструментов сборки"""
        return build_tools  # В нашем случае они совпадают

    def _check_tests(self, file_structure: List[Dict]) -> bool:
        """Проверяет наличие тестов"""
        test_patterns = [
            r'test.*\.py$', r'.*_test\.py$', r'.*\.test\.js$', r'.*\.spec\.js$',
            r'.*\.test\.ts$', r'.*\.spec\.ts$', r'.*Test\.java$', r'.*_test\.go$',
            r'test_.*\.py$', r'.*\.test\.jsx$', r'.*\.spec\.tsx$'
        ]

        test_directories = ['test', 'tests', '__tests__', 'spec', 'specs']

        for file_info in file_structure:
            name = file_info.get('name', '')
            path = file_info.get('path', '')

            # Проверяем паттерны имен файлов
            for pattern in test_patterns:
                if re.match(pattern, name, re.IGNORECASE):
                    return True

            # Проверяем директории с тестами
            for test_dir in test_directories:
                if f'/{test_dir}/' in path or path.startswith(f'/{test_dir}'):
                    return True

        return False

    def _check_dockerfile(self, file_structure: List[Dict]) -> bool:
        """Проверяет наличие Dockerfile"""
        dockerfile_names = ['Dockerfile', 'dockerfile', 'Dockerfile.prod', 'Dockerfile.dev']

        for file_info in file_structure:
            if file_info.get('type') == 'file':
                name = file_info.get('name', '')
                if name in dockerfile_names:
                    return True

        return False