"""
Self-Deploy: CI/CD Pipeline Generator
Автоматическая генерация GitLab CI пайплайнов через анализ Git-репозиториев

Usage:
    # Интерактивный режим (по умолчанию)
    python self_deploy.py

    # Режим с аргументами (для автоматизации)
    python self_deploy.py <repository_url>
"""

import sys
import os
import argparse
import re
from typing import Dict, Optional
from datetime import datetime

from analyzers.repository_analyzer import RepositoryAnalyzer
from analyzers.pipeline_generator import PipelineGenerator


class SelfDeploy:
    """
    Главный класс для генерации CI/CD пайплайнов
    """

    def __init__(self):
        """Инициализация"""
        self.analyzer = RepositoryAnalyzer()
        self.generator = PipelineGenerator()
        self.output_dir = 'generated_pipelines'

    def print_welcome(self):
        """Выводит приветственное сообщение"""
        print("\n" + "=" * 80)
        print("  🚀 Self-Deploy: CI/CD Pipeline Generator")
        print("=" * 80)
        print("\nАвтоматическая генерация GitLab CI пайплайнов")
        print("на основе анализа структуры Git-репозитория.")
        print("\n📋 Поддерживаемые языки:")
        print("   • Java/Kotlin (Maven, Gradle)")
        print("   • Go (Go Modules)")
        print("   • TypeScript/JavaScript (npm, yarn, pnpm)")
        print("   • Python (pip, poetry, pipenv)")
        print("\n💡 Примеры URL:")
        print("   • https://github.com/spring-projects/spring-boot")
        print("   • https://gitlab.com/gitlab-org/gitlab")
        print("=" * 80 + "\n")

    def validate_url(self, url: str) -> bool:
        """
        Проверяет корректность URL репозитория

        Args:
            url: URL для проверки

        Returns:
            bool: True если URL корректен
        """
        if not url or not url.strip():
            return False

        # Проверяем GitHub и GitLab URL
        github_pattern = r'https?://github\.com/[\w\-]+/[\w\-.]+'
        gitlab_pattern = r'https?://gitlab\.com/[\w\-]+/[\w\-.]+'

        return bool(re.match(github_pattern, url) or re.match(gitlab_pattern, url))

    def get_repository_url(self) -> Optional[str]:
        """
        Запрашивает URL репозитория у пользователя

        Returns:
            Optional[str]: URL репозитория или None при выходе
        """
        while True:
            try:
                url = input("Введите URL Git-репозитория (или 'exit' для выхода):\n> ").strip()

                # Проверка на команды выхода
                if url.lower() in ['exit', 'quit', 'q']:
                    return None

                # Проверка на пустой ввод
                if not url:
                    print("❌ Ошибка: URL не может быть пустым\n")
                    continue

                # Валидация URL
                if not self.validate_url(url):
                    print("❌ Ошибка: Некорректный URL")
                    print("   Поддерживаются только GitHub и GitLab репозитории")
                    print("   Примеры:")
                    print("   • https://github.com/user/repo")
                    print("   • https://gitlab.com/user/project\n")
                    continue

                return url

            except (KeyboardInterrupt, EOFError):
                print("\n\n👋 Прервано пользователем")
                return None

    def ask_continue(self) -> bool:
        """
        Спрашивает пользователя, хочет ли он продолжить

        Returns:
            bool: True если пользователь хочет продолжить
        """
        while True:
            try:
                answer = input("\nХотите проанализировать еще один репозиторий? (y/n): ").strip().lower()

                if answer in ['y', 'yes', 'да']:
                    return True
                elif answer in ['n', 'no', 'нет']:
                    return False
                elif answer in ['exit', 'quit', 'q']:
                    return False
                else:
                    print("❌ Пожалуйста, введите 'y' (да) или 'n' (нет)")

            except (KeyboardInterrupt, EOFError):
                print("\n")
                return False

    def run_interactive(self):
        """Запускает интерактивный режим"""
        self.print_welcome()

        while True:
            # Получаем URL от пользователя
            repository_url = self.get_repository_url()

            if repository_url is None:
                print("\n👋 Спасибо за использование Self-Deploy!")
                break

            # Выполняем анализ
            print("\n🔍 Анализируем репозиторий...\n")
            success = self.run_analysis(repository_url)

            if not success:
                print("\n❌ Анализ завершился с ошибкой")

            # Спрашиваем, хочет ли пользователь продолжить
            if not self.ask_continue():
                print("\n👋 Спасибо за использование Self-Deploy!")
                break

            print("\n" + "-" * 80 + "\n")

    def run_analysis(self, repository_url: str) -> bool:
        """
        Выполняет анализ репозитория

        Args:
            repository_url: URL Git-репозитория

        Returns:
            bool: True если анализ успешен
        """
        print("=" * 80)
        print(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Репозиторий: {repository_url}")
        print("=" * 80)

        try:
            # Шаг 1: Анализ репозитория
            print("\n[Шаг 1/3] Анализ структуры репозитория...")
            analysis_result = self.analyzer.analyze_repository(repository_url)

            # Шаг 2: Вывод отчета об анализе
            print("\n[Шаг 2/3] Результаты анализа:")
            self._print_analysis_report(analysis_result)

            # Шаг 3: Генерация пайплайна
            print("\n[Шаг 3/3] Генерация GitLab CI пайплайна...")
            pipeline_content = self.generator.generate_gitlab_pipeline(analysis_result)

            # Сохранение результатов
            self._save_results(analysis_result, pipeline_content)

            print("\n" + "=" * 80)
            print("✅ Анализ завершен успешно!")
            print("=" * 80)

            return True

        except Exception as e:
            print(f"\n❌ Ошибка: {str(e)}")
            if '--debug' in sys.argv:
                import traceback
                traceback.print_exc()
            return False
        finally:
            # Очистка временных файлов
            self.analyzer.cleanup()

    def _print_analysis_report(self, analysis_result: Dict):
        """Выводит подробный отчет об анализе"""
        tech_stack = analysis_result['tech_stack']
        repository = analysis_result['repository']
        confidence = analysis_result['confidence_level']

        print(f"\n📊 Репозиторий: {repository['full_name']}")
        print(f"   Платформа: {repository['platform']}")
        print(f"   Метод анализа: {analysis_result['analysis_method']}")
        print(f"   Уровень уверенности: {confidence:.0%}")

        print(f"\n💻 Основной язык: {tech_stack['primary_language']}")

        # Статистика по языкам
        if tech_stack['language_stats']:
            print("\n📈 Статистика по языкам:")
            for lang, stats in list(tech_stack['language_stats'].items())[:5]:
                print(f"   • {lang}: {stats['lines']} строк ({stats['percentage']}%)")

        # Версия языка
        version_info = tech_stack.get('version_info', {})
        if version_info:
            print(f"\n🔢 Версия: {version_info.get('language_version', 'не определена')}")

        # Фреймворки
        if tech_stack['frameworks']:
            print(f"\n🎯 Фреймворки: {', '.join(tech_stack['frameworks'])}")

        # Инструменты сборки
        if tech_stack['build_tools']:
            print(f"\n🔨 Инструменты сборки: {', '.join(tech_stack['build_tools'])}")

        # Менеджеры пакетов
        if tech_stack['package_managers']:
            print(f"\n📦 Менеджеры пакетов: {', '.join(tech_stack['package_managers'])}")

        # Тесты и Docker
        print(f"\n✅ Наличие тестов: {'Да' if tech_stack['has_tests'] else 'Нет'}")
        print(f"🐳 Наличие Dockerfile: {'Да' if tech_stack['has_dockerfile'] else 'Нет'}")

        # Рекомендации
        if analysis_result['recommendations']:
            print("\n💡 Рекомендации:")
            for rec in analysis_result['recommendations']:
                print(f"   {rec}")

    def _save_results(self, analysis_result: Dict, pipeline_content: str):
        """Сохраняет результаты генерации"""
        repository = analysis_result['repository']
        repo_name = repository['name']

        # Создаем директорию для результатов
        os.makedirs(self.output_dir, exist_ok=True)

        # Создаем поддиректорию для конкретного репозитория
        repo_dir = os.path.join(self.output_dir, repo_name)
        os.makedirs(repo_dir, exist_ok=True)

        # Сохраняем .gitlab-ci.yml
        gitlab_ci_path = os.path.join(repo_dir, '.gitlab-ci.yml')
        with open(gitlab_ci_path, 'w', encoding='utf-8') as f:
            f.write(pipeline_content)

        print(f"\n📄 Сгенерированные файлы:")
        print(f"   • GitLab CI: {gitlab_ci_path}")

        # Сохраняем отчет об анализе
        report_path = os.path.join(repo_dir, 'analysis_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_text_report(analysis_result))

        print(f"   • Отчет: {report_path}")

        # Создаем README с инструкциями
        readme_path = os.path.join(repo_dir, 'README.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_readme(analysis_result))

        print(f"   • Инструкции: {readme_path}")

        print(f"\n📁 Все файлы сохранены в: {repo_dir}")

    def _generate_text_report(self, analysis_result: Dict) -> str:
        """Генерирует текстовый отчет"""
        tech_stack = analysis_result['tech_stack']
        repository = analysis_result['repository']

        report = f"""
Self-Deploy: Отчет об анализе репозитория
==========================================

Репозиторий: {repository['full_name']}
Платформа: {repository['platform']}
URL: {repository['url']}
Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Технологический стек
--------------------
Основной язык: {tech_stack['primary_language']}
Версия: {tech_stack.get('version_info', {}).get('language_version', 'не определена')}
Фреймворки: {', '.join(tech_stack['frameworks']) if tech_stack['frameworks'] else 'не обнаружены'}
Инструменты сборки: {', '.join(tech_stack['build_tools']) if tech_stack['build_tools'] else 'не обнаружены'}
Менеджеры пакетов: {', '.join(tech_stack['package_managers']) if tech_stack['package_managers'] else 'не обнаружены'}

Дополнительная информация
-------------------------
Наличие тестов: {'Да' if tech_stack['has_tests'] else 'Нет'}
Наличие Dockerfile: {'Да' if tech_stack['has_dockerfile'] else 'Нет'}
Уровень уверенности: {analysis_result['confidence_level']:.0%}

Статистика по языкам
--------------------
"""
        for lang, stats in tech_stack['language_stats'].items():
            report += f"{lang}: {stats['lines']} строк ({stats['percentage']}%)\n"

        if analysis_result['recommendations']:
            report += "\nРекомендации\n------------\n"
            for rec in analysis_result['recommendations']:
                report += f"• {rec}\n"

        return report

    def _generate_readme(self, analysis_result: Dict) -> str:
        """Генерирует README с инструкциями"""
        repository = analysis_result['repository']
        tech_stack = analysis_result['tech_stack']

        readme = f"""# GitLab CI/CD Pipeline для {repository['name']}

Этот пайплайн был автоматически сгенерирован с помощью **Self-Deploy**.

## 📋 Информация о проекте

- **Язык программирования**: {tech_stack['primary_language']}
- **Фреймворки**: {', '.join(tech_stack['frameworks']) if tech_stack['frameworks'] else 'не обнаружены'}
- **Инструменты сборки**: {', '.join(tech_stack['build_tools']) if tech_stack['build_tools'] else 'не обнаружены'}

## 🚀 Использование

1. Скопируйте файл `.gitlab-ci.yml` в корень вашего репозитория:
   ```bash
   cp .gitlab-ci.yml /path/to/your/repo/
   ```

2. Настройте переменные окружения в GitLab CI/CD Settings:
   - `SONAR_HOST_URL` - URL вашего SonarQube сервера
   - `SONAR_TOKEN` - токен для доступа к SonarQube
   - `NEXUS_URL` - URL вашего Nexus Repository
   - `NEXUS_USER` - имя пользователя Nexus
   - `NEXUS_PASSWORD` - пароль Nexus

3. Закоммитьте и запушьте изменения:
   ```bash
   git add .gitlab-ci.yml
   git commit -m "Add GitLab CI/CD pipeline"
   git push
   ```

## 📊 Этапы пайплайна

Пайплайн включает следующие этапы:

1. **Build** - Сборка проекта
2. **Test** - Запуск тестов
3. **Quality** - Проверка качества кода
4. **Package** - Упаковка артефактов
5. **Docker Build** - Сборка Docker образа (если есть Dockerfile)
6. **Deploy Staging** - Развертывание в staging
7. **Deploy Production** - Развертывание в production

## 🔧 Настройка

### SonarQube

Для работы SonarQube анализа создайте файл `sonar-project.properties` в корне проекта:

```properties
sonar.projectKey={repository['name']}
sonar.projectName={repository['name']}
sonar.sources=.
sonar.sourceEncoding=UTF-8
```

### Nexus Repository

Убедитесь, что в Nexus настроен репозиторий для хранения артефактов.

### Kubernetes

Для развертывания в Kubernetes убедитесь, что:
- Настроены контексты `staging` и `production`
- Созданы Deployment манифесты для вашего приложения

## 📝 Примечания

- Пайплайн оптимизирован для {tech_stack['primary_language']}
- Используется кеширование зависимостей для ускорения сборки
- Включена интеграция с SonarQube для анализа качества кода
- Поддерживается загрузка артефактов в Nexus Repository

## 🆘 Поддержка

Если у вас возникли вопросы или проблемы с пайплайном, обратитесь к документации GitLab CI/CD:
https://docs.gitlab.com/ee/ci/

---
Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return readme


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Self-Deploy: Автоматическая генерация GitLab CI пайплайнов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Режимы работы:

  1. Интерактивный режим (по умолчанию):
     python self_deploy.py

     Приложение запросит URL репозитория и предложит
     проанализировать несколько репозиториев подряд.

  2. Режим с аргументами (для автоматизации):
     python self_deploy.py <repository_url>

     Выполнит анализ указанного репозитория и завершит работу.

Примеры:
  python self_deploy.py
  python self_deploy.py https://github.com/spring-projects/spring-boot
  python self_deploy.py https://gitlab.com/gitlab-org/gitlab

Поддерживаемые языки:
  • Java/Kotlin (Maven, Gradle)
  • Go (Go Modules)
  • TypeScript/JavaScript (npm, yarn, pnpm)
  • Python (pip, poetry, pipenv)
        """
    )

    parser.add_argument(
        'repository_url',
        nargs='?',
        help='URL Git-репозитория (GitHub или GitLab). Если не указан, запускается интерактивный режим'
    )

    parser.add_argument(
        '-o', '--output',
        default='generated_pipelines',
        help='Директория для сохранения результатов (по умолчанию: generated_pipelines)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Включить отладочный вывод'
    )

    args = parser.parse_args()

    # Создаем экземпляр
    deployer = SelfDeploy()
    deployer.output_dir = args.output

    # Выбираем режим работы
    if args.repository_url:
        # Режим с аргументами - выполняем анализ и завершаем
        success = deployer.run_analysis(args.repository_url)
        sys.exit(0 if success else 1)
    else:
        # Интерактивный режим
        try:
            deployer.run_interactive()
        except KeyboardInterrupt:
            print("\n\n👋 Прервано пользователем")
            sys.exit(0)


if __name__ == '__main__':
    main()