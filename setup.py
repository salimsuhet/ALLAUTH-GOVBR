from setuptools import find_packages, setup

setup(
    name="allauth-govbr",
    version="1.0.0",
    description="Plugin django-allauth para Login Gov.br e Acesso Cidadão ES (GeoNode 4.x)",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="CLAUDE.AI",
    url="https://github.com/seu-org/allauth-govbr",
    license="MIT",
    packages=find_packages(exclude=["tests*", "docs*"]),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        # Compatível com GeoNode 4.x
        "django-allauth>=0.51.0,<0.57.0",
        "requests>=2.28",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-django",
        ]
    },
    classifiers=[
        "Framework :: Django",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet :: WWW/HTTP :: Session",
    ],
)
