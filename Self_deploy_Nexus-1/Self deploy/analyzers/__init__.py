"""
Self-Deploy Analyzers Package
Модули для анализа Git-репозиториев и генерации CI/CD пайплайнов
"""

from .repository_analyzer import RepositoryAnalyzer
from .tech_stack_detector import TechStackDetector
from .pipeline_generator import PipelineGenerator

__all__ = ['RepositoryAnalyzer', 'TechStackDetector', 'PipelineGenerator']
__version__ = '1.0.0'