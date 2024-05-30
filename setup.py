from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="candycom",
    version="0.1.5",
    author="Michael Lance, Charles Palmer, Thomas Baker",
    author_email="michaelbraydenlance@gmail.com",
    description="Asyncio based communication protocol for candy machine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MikeL270/candycom",
    project_urls={
        "Bug Tracker": "https://github.com/MikeL270/candycom/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "."},
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "adafruit-blinka",
        "adafruit-circuitpython-ble",
        "pyserial",
    ],
)
