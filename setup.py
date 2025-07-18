from setuptools import setup, find_packages

setup(
    name="ag",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "click",
        "requests",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "ag = ag.cli:cli",
        ],
    },
)
