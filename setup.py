from setuptools import setup, find_packages

setup(
    name="allauth-govbr",
    version="0.2.0",
    description="Plugin django-allauth para Login Gov.br e Acesso Cidadão ES — GeoNode 5.x / allauth 0.63.x",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="SECTI-ES",
    url="https://github.com/salimsuhet/ALLAUTH-GOVBR",
    license="MIT",
    packages=find_packages(exclude=["tests*", "docs*"]),
    python_requires=">=3.10",
    install_requires=[
        "django>=4.2",
        "django-allauth>=0.63.0,<0.64.0",
        "requests>=2.28",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-django",
            "pytest-cov",
        ]
    },
    classifiers=[
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
