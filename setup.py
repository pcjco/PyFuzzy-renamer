import pathlib
from setuptools import setup

README = (pathlib.Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="PyFuzzy-renamer",
    version="0.1.0",
    description="Uses a list of input strings and will rename each one with the most similar string from another list of strings",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/pcjco/PyFuzzy-renamer",
    author="pcjco",
    author_email="pcjco@hotmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    packages=["pyfuzzyrenamer"],
    include_package_data=False,
    python_requires=">=3.6",
    install_requires=[
        "wxPython>=4.1.0",
        "python-Levenshtein>=0.12.0",
        "fuzzywuzzy>=0.17.0",
    ],
    entry_points={"gui_scripts": ["pyfuzzyrenamer = pyfuzzyrenamer.__main__:main"]},
)
