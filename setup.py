from setuptools import setup, find_packages

setup(
    name="distributed-sync-system",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),  
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "aiohttp>=3.8.1",
        "python-dotenv>=0.19.0",
        "redis>=4.3.4",
        "aioredis>=2.0.1",
        "prometheus-client>=0.14.1",
        "cryptography>=37.0.0",
        "pytest>=7.1.2",
        "pytest-asyncio>=0.18.3",
        "locust>=2.8.6",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "dsync=src.main:main",
        ],
    },
)
