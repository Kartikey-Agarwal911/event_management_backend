# Contributing to NeoFi Event Management System

Thank you for your interest in contributing to the NeoFi Event Management System! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/event_management_backend.git
   cd event_management_backend
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate   # Windows
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. Initialize the database:
   ```bash
   python -m app.database
   ```

## Development Workflow

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run tests:
   ```bash
   pytest --cov=app tests/
   ```

4. Commit your changes:
   ```bash
   git commit -m "Description of changes"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a Pull Request

## Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for functions and classes
- Keep functions small and focused
- Write tests for new features

## Testing

- Write unit tests for new features
- Ensure all tests pass
- Maintain or improve test coverage

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update the README.md if needed
5. The PR will be merged once approved

## Questions?

Feel free to open an issue for any questions or concerns. 