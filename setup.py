import sys
import setuptools

with open("requirements.txt", "r", encoding="utf-8") as r:
    requires = [i.strip() for i in r]

if sys.version_info >= (3, 8):
    for require in requires:
        if "cached-property" in require:
            requires.remove(require)
            break

setuptools.setup(
    name="tg_bot",
    version="0.0.2.1",
    author="daveusa31",
    packages=setuptools.find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=requires,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Natural Language :: Russian",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    project_urls={
        "Source": "https://github.com/daveusa31/tg-bot"
    },
)
