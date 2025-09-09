# Contributing to YouTube Analytics Dashboard

Thank you for your interest in contributing to the YouTube Analytics Dashboard! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect different viewpoints and experiences
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Basic understanding of:
  - Python and web development
  - Streamlit framework
  - YouTube APIs
  - SQLAlchemy ORM

### Development Setup

1. **Fork the repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/foundryx.git
   cd foundryx
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials
   ```

4. **Initialize the database**
   ```bash
   python -c "from src.database.models import init_db; init_db()"
   ```

5. **Run tests to verify setup**
   ```bash
   python run_tests.py
   ```

## Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes**: Fix issues and improve stability
- **Feature enhancements**: Add new functionality
- **Documentation**: Improve docs, examples, and guides
- **Testing**: Add or improve test coverage
- **Performance**: Optimize code and improve efficiency
- **UI/UX**: Enhance user interface and experience

### Before You Start

1. **Check existing issues**: Look for existing issues or feature requests
2. **Create an issue**: If none exists, create one to discuss your proposal
3. **Get feedback**: Wait for maintainer feedback before starting work
4. **Assign yourself**: Comment on the issue to indicate you're working on it

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-number
   ```

2. **Make your changes**
   - Follow coding standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run all tests
   python run_tests.py
   
   # Run specific test types
   python run_tests.py --unit
   python run_tests.py --integration
   
   # Check code quality
   flake8 src/
   mypy src/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

## Pull Request Process

### PR Requirements

- [ ] Clear description of changes
- [ ] Tests pass (CI/CD pipeline)
- [ ] Code follows style guidelines
- [ ] Documentation updated (if applicable)
- [ ] No merge conflicts
- [ ] Linked to relevant issue(s)

### PR Template

When creating a PR, please include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Other (specify)

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally

## Related Issues
Closes #issue_number
```

### Review Process

1. **Automated checks**: CI/CD pipeline runs tests and quality checks
2. **Code review**: Maintainers review code and provide feedback
3. **Address feedback**: Make requested changes
4. **Approval**: PR approved by maintainer
5. **Merge**: PR merged into main branch

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Maximum line length: 88 characters
- Use meaningful variable and function names
- Add docstrings to all public functions and classes

### Code Organization

```python
# Import order:
# 1. Standard library imports
# 2. Third-party imports
# 3. Local application imports

import os
import sys
from datetime import datetime

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

from src.database.models import Video
from src.utils.helpers import format_number
```

### Type Hints

Use type hints for all function parameters and return values:

```python
from typing import List, Dict, Optional

def process_videos(videos: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    """Process video data and return DataFrame.
    
    Args:
        videos: List of video dictionaries
        
    Returns:
        Processed DataFrame or None if empty
    """
    if not videos:
        return None
    return pd.DataFrame(videos)
```

### Error Handling

```python
import logging

logger = logging.getLogger(__name__)

def fetch_data() -> Optional[Dict[str, Any]]:
    """Fetch data with proper error handling."""
    try:
        # Your code here
        return data
    except APIError as e:
        logger.error(f"API error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise
```

## Testing

### Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── test_auth.py
│   ├── test_database.py
│   └── ...
├── integration/          # Integration tests
│   ├── test_workflows.py
│   └── ...
└── fixtures/            # Test data and fixtures
    ├── sample_data.json
    └── ...
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

from src.auth.youtube_auth import YouTubeAuth

class TestYouTubeAuth:
    """Test cases for YouTube authentication."""
    
    def test_initialization(self):
        """Test auth initialization."""
        auth = YouTubeAuth()
        assert auth is not None
        assert auth.credentials is None
    
    @patch('src.auth.youtube_auth.build')
    def test_create_service(self, mock_build):
        """Test service creation."""
        auth = YouTubeAuth()
        auth.credentials = Mock()
        
        service = auth.create_service()
        
        assert service is not None
        mock_build.assert_called_once()
```

### Test Coverage

- Aim for >80% test coverage
- Test both success and failure scenarios
- Include edge cases and boundary conditions
- Mock external dependencies (APIs, databases)

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include examples for complex functions

```python
def generate_insights(data: pd.DataFrame, prompt_template: str) -> List[Dict[str, Any]]:
    """Generate AI insights from video data.
    
    Args:
        data: DataFrame containing video metrics
        prompt_template: Template for AI prompt generation
        
    Returns:
        List of insight dictionaries with keys:
        - content: Insight text
        - priority: Priority level (high/medium/low)
        - category: Insight category
        
    Raises:
        ValueError: If data is empty or invalid
        APIError: If AI service is unavailable
        
    Example:
        >>> data = pd.DataFrame({'views': [100, 200], 'likes': [10, 20]})
        >>> insights = generate_insights(data, "Analyze performance: {data}")
        >>> len(insights) > 0
        True
    """
```

### README Updates

When adding new features:

- Update feature list
- Add configuration options
- Include usage examples
- Update troubleshooting section

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Changelog

Update `CHANGELOG.md` with:

- New features
- Bug fixes
- Breaking changes
- Deprecations

## Getting Help

### Resources

- **Documentation**: Check existing docs and README
- **Issues**: Search existing issues for similar problems
- **Discussions**: Use GitHub Discussions for questions
- **Code**: Review existing code for patterns and examples

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and feedback

### Mentorship

New contributors are welcome! We're happy to help you:

- Understand the codebase
- Choose appropriate first issues
- Review your contributions
- Learn best practices

Look for issues labeled `good first issue` or `help wanted`.

## Recognition

Contributors are recognized in:

- GitHub contributors list
- Release notes
- Project documentation

Thank you for contributing to the YouTube Analytics Dashboard!