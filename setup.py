from setuptools import setup, find_packages

setup(
    name="arcane-arsenal",
    version="0.1.0",
    description="A roleplaying state manager built on Entity Component System architecture",
    author="Samuel",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "flask>=3.0.0",
        "jsonschema>=4.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "mypy>=1.7.0",
            "pylint>=3.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "arcane=src.cli.commands:main",
        ]
    },
)
