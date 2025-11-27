"""
Pipeline Generator
Генератор GitLab CI/CD пайплайнов на основе анализа технологического стека
Поддержка: Java/Kotlin, Go, TypeScript/JavaScript, Python
"""

from typing import Dict, List
import yaml


class PipelineGenerator:
    """
    Класс для генерации GitLab CI/CD пайплайнов
    Создает персонализированные .gitlab-ci.yml конфигурации
    """

    def __init__(self):
        """Инициализация генератора"""
        self.sonarqube_enabled = True
        self.nexus_enabled = True

    def generate_gitlab_pipeline(self, analysis_result: Dict) -> str:
        """
        Генерирует GitLab CI/CD пайплайн (.gitlab-ci.yml)

        Args:
            analysis_result (Dict): Результаты анализа репозитория

        Returns:
            str: Содержимое .gitlab-ci.yml
        """
        tech_stack = analysis_result['tech_stack']
        repository = analysis_result['repository']

        primary_language = tech_stack['primary_language']
        build_tools = tech_stack['build_tools']
        frameworks = tech_stack.get('frameworks', [])
        has_tests = tech_stack['has_tests']
        has_dockerfile = tech_stack['has_dockerfile']
        version_info = tech_stack.get('version_info', {})

        print(f"\n🔧 Генерация GitLab CI пайплайна для {primary_language}")

        # Определяем образ Docker и переменные
        docker_image, variables = self._get_docker_image_and_variables(
            primary_language, frameworks, version_info
        )

        # Генерируем этапы
        stages = ['build', 'test', 'quality', 'package']
        if has_dockerfile:
            stages.extend(['docker-build', 'deploy-staging', 'deploy-production'])
        else:
            stages.extend(['deploy-staging', 'deploy-production'])

        # Базовая конфигурация пайплайна
        pipeline_dict = {
            'stages': stages,
            'variables': variables,
            'image': docker_image,
            'cache': self._generate_cache_config(primary_language, build_tools),
            'before_script': self._generate_before_script(primary_language, build_tools, frameworks)
        }

        # Конвертируем базовую конфигурацию в YAML
        pipeline_yaml = yaml.dump(pipeline_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Добавляем задачи
        pipeline_yaml += "\n# ==================== BUILD STAGE ====================\n"
        pipeline_yaml += self._generate_build_job(primary_language, build_tools, frameworks)

        if has_tests:
            pipeline_yaml += "\n# ==================== TEST STAGE ====================\n"
            pipeline_yaml += self._generate_test_job(primary_language, build_tools, frameworks)

        pipeline_yaml += "\n# ==================== CODE QUALITY STAGE ====================\n"
        pipeline_yaml += self._generate_quality_job(primary_language, frameworks)

        if self.sonarqube_enabled:
            pipeline_yaml += "\n# SonarQube анализ\n"
            pipeline_yaml += self._generate_sonarqube_job(primary_language)

        pipeline_yaml += "\n# ==================== PACKAGE STAGE ====================\n"
        pipeline_yaml += self._generate_package_job(primary_language, frameworks)

        if self.nexus_enabled:
            pipeline_yaml += "\n# Загрузка артефактов в Nexus\n"
            pipeline_yaml += self._generate_nexus_upload_job(primary_language)

        if has_dockerfile:
            pipeline_yaml += "\n# ==================== DOCKER BUILD STAGE ====================\n"
            pipeline_yaml += self._generate_docker_build_job(repository['name'])
            pipeline_yaml += "\n# Docker Security Scan\n"
            pipeline_yaml += self._generate_docker_security_scan_job(repository['name'])

        pipeline_yaml += "\n# ==================== DEPLOYMENT STAGES ====================\n"
        pipeline_yaml += self._generate_deployment_jobs(repository['name'], has_dockerfile)

        return pipeline_yaml

    def _get_docker_image_and_variables(self, primary_language: str, frameworks: List[str],
                                       version_info: Dict) -> tuple:
        """Определяет Docker образ и переменные для GitLab CI"""
        language_version = version_info.get('language_version', '')

        if primary_language in ['JavaScript', 'TypeScript']:
            node_version = language_version if language_version else '18'
            return f'node:{node_version}-alpine', {
                'NPM_CONFIG_CACHE': '$CI_PROJECT_DIR/.npm',
                'NODE_OPTIONS': '--max-old-space-size=4096',
                'CI': 'true'
            }

        elif primary_language == 'Python':
            python_version = language_version if language_version else '3.9'
            return f'python:{python_version}-slim', {
                'PIP_CACHE_DIR': '$CI_PROJECT_DIR/.cache/pip',
                'PYTHONPATH': '$CI_PROJECT_DIR',
                'PYTHONUNBUFFERED': '1'
            }

        elif primary_language in ['Java', 'Kotlin']:
            java_version = language_version if language_version else '11'
            return f'maven:3.8-openjdk-{java_version}', {
                'MAVEN_OPTS': '-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository -Xmx1024m',
                'MAVEN_CLI_OPTS': '--batch-mode --errors --fail-at-end --show-version'
            }

        elif primary_language == 'Go':
            go_version = language_version if language_version else '1.19'
            return f'golang:{go_version}-alpine', {
                'GOCACHE': '$CI_PROJECT_DIR/.cache/go-build',
                'GOPATH': '$CI_PROJECT_DIR/.go',
                'CGO_ENABLED': '0'
            }

        else:
            return 'alpine:latest', {}

    def _generate_cache_config(self, primary_language: str, build_tools: List[str]) -> Dict:
        """Генерирует конфигурацию кеша для GitLab CI"""
        cache_paths = []

        if primary_language in ['JavaScript', 'TypeScript']:
            cache_paths.extend(['.npm/', 'node_modules/'])
        elif primary_language == 'Python':
            cache_paths.extend(['.cache/pip/', '__pycache__/', '.pytest_cache/'])
        elif primary_language in ['Java', 'Kotlin']:
            cache_paths.extend(['.m2/repository/', '.gradle/'])
        elif primary_language == 'Go':
            cache_paths.extend(['.cache/go-build/', '.go/'])

        return {
            'key': '$CI_COMMIT_REF_SLUG',
            'paths': cache_paths,
            'policy': 'pull-push'
        }

    def _generate_before_script(self, primary_language: str, build_tools: List[str],
                                frameworks: List[str]) -> List[str]:
        """Генерирует before_script для GitLab CI"""
        scripts = []

        if primary_language in ['JavaScript', 'TypeScript']:
            if 'npm' in build_tools:
                scripts.append('npm ci --cache .npm --prefer-offline')
            elif 'yarn' in build_tools:
                scripts.append('yarn install --frozen-lockfile --cache-folder .yarn')
            elif 'pnpm' in build_tools:
                scripts.append('pnpm install --frozen-lockfile')

        elif primary_language == 'Python':
            scripts.extend([
                'python -m pip install --upgrade pip',
                'pip install -r requirements.txt --cache-dir .cache/pip'
            ])

        elif primary_language in ['Java', 'Kotlin'] and 'maven' in build_tools:
            scripts.append('mvn dependency:go-offline $MAVEN_CLI_OPTS')

        return scripts

    def _generate_build_job(self, primary_language: str, build_tools: List[str],
                           frameworks: List[str]) -> str:
        """Генерирует задачу сборки для GitLab CI"""

        if primary_language in ['JavaScript', 'TypeScript']:
            script_commands = []

            if 'React' in frameworks or 'Vue.js' in frameworks or 'Angular' in frameworks or 'Next.js' in frameworks:
                script_commands.append('npm run build')
            else:
                script_commands.append('npm run build || echo "No build script found"')

            return f"""
build:
  stage: build
  script:
    - {chr(10).join(f'    - {cmd}' for cmd in script_commands)}
  artifacts:
    paths:
      - dist/
      - build/
      - .next/
      - out/
    expire_in: 1 hour
  only:
    - branches
"""

        elif primary_language == 'Python':
            script_commands = ['python -m compileall .']

            if 'Django' in frameworks:
                script_commands.extend([
                    'python manage.py collectstatic --noinput',
                    'python manage.py check --deploy'
                ])

            return f"""
build:
  stage: build
  script:
    - {chr(10).join(f'    - {cmd}' for cmd in script_commands)}
  artifacts:
    paths:
      - staticfiles/
      - "*.pyc"
    expire_in: 1 hour
"""

        elif primary_language in ['Java', 'Kotlin']:
            if 'maven' in build_tools:
                return """
build:
  stage: build
  script:
    - mvn clean compile $MAVEN_CLI_OPTS
    - mvn package -DskipTests $MAVEN_CLI_OPTS
  artifacts:
    paths:
      - target/*.jar
      - target/*.war
    expire_in: 1 hour
"""
            elif 'gradle' in build_tools:
                return """
build:
  stage: build
  script:
    - ./gradlew clean build -x test --no-daemon
  artifacts:
    paths:
      - build/libs/*.jar
    expire_in: 1 hour
"""

        elif primary_language == 'Go':
            return """
build:
  stage: build
  script:
    - go mod download
    - go build -v -o app ./...
  artifacts:
    paths:
      - app
    expire_in: 1 hour
"""

        return """
build:
  stage: build
  script:
    - echo "Настройте команды сборки для вашего проекта"
  artifacts:
    paths:
      - "build/"
    expire_in: 1 hour
"""

    def _generate_test_job(self, primary_language: str, build_tools: List[str],
                          frameworks: List[str]) -> str:
        """Генерирует задачу тестирования для GitLab CI"""

        if primary_language in ['JavaScript', 'TypeScript']:
            test_commands = []
            if 'React' in frameworks:
                test_commands = ['npm test -- --coverage --watchAll=false --ci']
            elif 'Vue.js' in frameworks:
                test_commands = ['npm run test:unit']
            elif 'Angular' in frameworks:
                test_commands = ['npm run test -- --watch=false --browsers=ChromeHeadless --code-coverage']
            else:
                test_commands = ['npm test']

            return f"""
test:
  stage: test
  script:
    - {chr(10).join(f'    - {cmd}' for cmd in test_commands)}
  artifacts:
    reports:
      junit: junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
    paths:
      - coverage/
    when: always
  coverage: '/Lines\\s*:\\s*(\\d+\\.?\\d*)%/'
"""

        elif primary_language == 'Python':
            if 'Django' in frameworks:
                return """
test:
  stage: test
  script:
    - coverage run --source='.' manage.py test --keepdb
    - coverage xml
    - coverage report
  artifacts:
    reports:
      junit: test-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    when: always
  coverage: '/TOTAL.+ ([0-9]{1,3}%)/'
"""
            else:
                return """
test:
  stage: test
  script:
    - pytest --junitxml=test-results.xml --cov=. --cov-report=xml --cov-report=term
  artifacts:
    reports:
      junit: test-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    when: always
  coverage: '/TOTAL.+ ([0-9]{1,3}%)/'
"""

        elif primary_language in ['Java', 'Kotlin']:
            if 'maven' in build_tools:
                return """
test:
  stage: test
  script:
    - mvn test $MAVEN_CLI_OPTS
    - mvn jacoco:report $MAVEN_CLI_OPTS
  artifacts:
    reports:
      junit: target/surefire-reports/*.xml
    paths:
      - target/site/jacoco/
    when: always
"""
            elif 'gradle' in build_tools:
                return """
test:
  stage: test
  script:
    - ./gradlew test jacocoTestReport --no-daemon
  artifacts:
    reports:
      junit: build/test-results/test/*.xml
    paths:
      - build/reports/jacoco/test/html/
    when: always
"""

        elif primary_language == 'Go':
            return """
test:
  stage: test
  script:
    - go test -v ./... -coverprofile=coverage.out
    - go tool cover -func=coverage.out
  artifacts:
    paths:
      - coverage.out
    when: always
  coverage: '/total:.*?([0-9.]+)%/'
"""

        return """
test:
  stage: test
  script:
    - echo "Настройте команды тестирования"
"""

    def _generate_quality_job(self, primary_language: str, frameworks: List[str]) -> str:
        """Генерирует задачу проверки качества кода для GitLab CI"""

        if primary_language in ['JavaScript', 'TypeScript']:
            return """
code-quality:
  stage: quality
  script:
    - npm run lint || npx eslint . --ext .js,.jsx,.ts,.tsx --format gitlab --output-file eslint-report.json || true
    - npx prettier --check . || true
  artifacts:
    reports:
      codequality: eslint-report.json
    when: always
  allow_failure: true
"""

        elif primary_language == 'Python':
            return """
code-quality:
  stage: quality
  script:
    - pip install flake8 black mypy
    - flake8 . --format=json --output-file=flake8-report.json || true
    - black --check . || true
    - mypy . --ignore-missing-imports || true
  artifacts:
    reports:
      codequality: flake8-report.json
    when: always
  allow_failure: true
"""

        elif primary_language in ['Java', 'Kotlin']:
            return """
code-quality:
  stage: quality
  script:
    - mvn checkstyle:check $MAVEN_CLI_OPTS || true
    - mvn pmd:check $MAVEN_CLI_OPTS || true
  allow_failure: true
"""

        elif primary_language == 'Go':
            return """
code-quality:
  stage: quality
  script:
    - go fmt ./...
    - go vet ./...
    - go install golang.org/x/lint/golint@latest
    - golint ./... || true
  allow_failure: true
"""

        return """
code-quality:
  stage: quality
  script:
    - echo "Настройте проверку качества кода"
  allow_failure: true
"""

    def _generate_sonarqube_job(self, primary_language: str) -> str:
        """Генерирует задачу SonarQube анализа"""
        return """
sonarqube-check:
  stage: quality
  image: sonarsource/sonar-scanner-cli:latest
  variables:
    SONAR_HOST_URL: "${SONAR_HOST_URL}"
    SONAR_TOKEN: "${SONAR_TOKEN}"
  script:
    - sonar-scanner
      -Dsonar.projectKey=$CI_PROJECT_NAME
      -Dsonar.sources=.
      -Dsonar.host.url=$SONAR_HOST_URL
      -Dsonar.login=$SONAR_TOKEN
  allow_failure: true
  only:
    - main
    - develop
"""

    def _generate_package_job(self, primary_language: str, frameworks: List[str]) -> str:
        """Генерирует задачу упаковки артефактов для GitLab CI"""
        return """
package:
  stage: package
  script:
    - echo "Упаковка артефактов для развертывания"
    - tar -czf application.tar.gz dist/ build/ staticfiles/ target/ app || true
  artifacts:
    paths:
      - application.tar.gz
    expire_in: 1 week
  only:
    - main
    - develop
"""

    def _generate_nexus_upload_job(self, primary_language: str) -> str:
        """Генерирует задачу загрузки артефактов в Nexus"""
        return """
nexus-upload:
  stage: package
  script:
    - echo "Загрузка артефактов в Nexus Repository"
    - |
      curl -v -u $NEXUS_USER:$NEXUS_PASSWORD \\
        --upload-file application.tar.gz \\
        $NEXUS_URL/repository/releases/$CI_PROJECT_NAME/$CI_COMMIT_TAG/application.tar.gz
  only:
    - tags
  when: manual
"""

    def _generate_docker_build_job(self, repo_name: str) -> str:
        """Генерирует задачу Docker сборки для GitLab CI с multi-stage builds"""
        return f"""
docker-build:
  stage: docker-build
  image: docker:24-cli
  services:
    - docker:24-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
    DOCKER_DRIVER: overlay2
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - echo "Building Docker image with multi-stage build..."
    - docker build
      --build-arg CI_COMMIT_SHA=$CI_COMMIT_SHA
      --build-arg CI_COMMIT_REF_NAME=$CI_COMMIT_REF_NAME
      --cache-from $CI_REGISTRY_IMAGE:latest
      -t $CI_REGISTRY_IMAGE:{repo_name.lower()}-$CI_COMMIT_SHA
      -t $CI_REGISTRY_IMAGE:latest
      .
    - docker push $CI_REGISTRY_IMAGE:{repo_name.lower()}-$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE:latest
    - |
      if [ "$CI_COMMIT_BRANCH" == "main" ]; then
        docker tag $CI_REGISTRY_IMAGE:{repo_name.lower()}-$CI_COMMIT_SHA $CI_REGISTRY_IMAGE:stable
        docker push $CI_REGISTRY_IMAGE:stable
      fi
  after_script:
    - docker system prune -f
  only:
    - main
    - develop
"""

    def _generate_docker_security_scan_job(self, repo_name: str) -> str:
        """Генерирует задачу сканирования безопасности Docker образа"""
        return f"""
docker-security-scan:
  stage: docker-build
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy image
      --format template
      --template "@contrib/gitlab.tpl"
      --output gl-container-scanning-report.json
      $CI_REGISTRY_IMAGE:{repo_name.lower()}-$CI_COMMIT_SHA
  artifacts:
    reports:
      container_scanning: gl-container-scanning-report.json
  dependencies:
    - docker-build
  allow_failure: true
  only:
    - main
    - develop
"""

    def _generate_deployment_jobs(self, repo_name: str, has_dockerfile: bool) -> str:
        """Генерирует задачи развертывания для GitLab CI"""
        image_ref = f"$CI_REGISTRY_IMAGE:{repo_name.lower()}-$CI_COMMIT_SHA" if has_dockerfile else "application.tar.gz"

        return f"""
deploy-staging:
  stage: deploy-staging
  image: bitnami/kubectl:latest
  script:
    - echo "Развертывание в staging окружение"
    - kubectl config use-context staging
    - |
      if [ "{has_dockerfile}" == "True" ]; then
        kubectl set image deployment/{repo_name.lower()} {repo_name.lower()}={image_ref}
        kubectl rollout status deployment/{repo_name.lower()}
      else
        echo "Развертывание без Docker (например, на VM)"
        # Добавьте команды для развертывания без контейнеров
      fi
  environment:
    name: staging
    url: https://staging.{repo_name.lower()}.com
  only:
    - develop
  when: manual

deploy-production:
  stage: deploy-production
  image: bitnami/kubectl:latest
  script:
    - echo "Развертывание в production окружение"
    - kubectl config use-context production
    - |
      if [ "{has_dockerfile}" == "True" ]; then
        kubectl set image deployment/{repo_name.lower()} {repo_name.lower()}={image_ref}
        kubectl rollout status deployment/{repo_name.lower()}
      else
        echo "Развертывание без Docker (например, на VM)"
        # Добавьте команды для развертывания без контейнеров
      fi
  environment:
    name: production
    url: https://{repo_name.lower()}.com
  only:
    - main
  when: manual
"""