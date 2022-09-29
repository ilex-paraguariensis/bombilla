from setuptools import setup, find_packages

setup(
    name="bomba",
    description="A cowsay clone for python in one file.",
    author="Giulio Zani, Ali Rahimi",
    author_email="yerba.mate.dl@proton.me",
    url="https://github.com/ilex-paraguariensis/bombilla",
    python_requires=">=3.9",
    version="1.1.112",
    packages=find_packages("packages", exclude=["tests", "examples"]),
    include_package_data=True,
    package_dir={"": "packages/"},
    license="Apache License 2.0",
    license_files=("LICENSE.md",),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    scripts=["./src/bomba"],
)
