from setuptools import setup, find_packages

setup(
    name="jwt_core_lib",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-jose[cryptography]",
        "pydantic"
    ],
)
